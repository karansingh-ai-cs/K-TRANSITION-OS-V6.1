"""
negotiator/main.py — K-Transition OS v3.0
==========================================
Voice assistant backend. Architecture is UNCHANGED (WebSocket/asyncio/barge-in/edge-tts).

Key v3 changes only:
  1. Realistic negotiation: tracks deal_finalized flag.
     Once DEAL_CLOSED/TASK_COMPLETE/REQUEST_FULFILLED is returned, the
     session is sealed — no more LLM calls that could re-open bargaining.
  2. Auto-summary: when session ends, Groq generates a 2-3 sentence summary.
  3. session_ended action sent to frontend with summary.
  4. /transcribe_goal endpoint: POST audio → transcribed goal text.
  5. user_modify action: user can change goal mid-session.
  6. Timeout guard: if session has been idle 5 min → auto-close.
"""

import asyncio
import json
import os
import logging
import tempfile
import time
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import edge_tts
import groq
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
WHISPER_MODEL     = "whisper-large-v3"
LLM_MODEL         = "llama-3.3-70b-versatile"
KOREAN_TTS_VOICE  = "ko-KR-SunHiNeural"
ENGLISH_TTS_VOICE = "en-US-AriaNeural"

# ── System Prompt ─────────────────────────────────────────────────────────────

UNIVERSAL_SYSTEM_PROMPT = """You are 한국 AI 도우미 (Korean AI Helper), the voice assistant of K-Transition OS.
You speak KOREAN directly to the Korean person. You update the student in ENGLISH.
You are acting on behalf of an international student who cannot speak Korean well.

CURRENT MISSION: {mission_goal}
CONTEXT TYPE: {context_type}
SESSION STATUS: {session_status}

{tone_modifier}

━━ DEAL STATE RULES (CRITICAL) ━━
If SESSION STATUS is "FINALIZED": The deal is already done.
- Do NOT ask for more discounts. Do NOT re-negotiate.
- Only handle polite wrap-up: thanking, confirming, saying goodbye.
- After one wrap-up exchange, return action: "SESSION_WRAP_COMPLETE"

If SESSION STATUS is "ACTIVE": Normal flow.
- Follow tone_modifier rules.
- Return DEAL_CLOSED only when price/task is truly agreed/completed — not on first offer.

━━ ABSOLUTE OUTPUT RULE ━━
Always respond with EXACTLY this JSON. No markdown. No extra text:
{{
  "korean_speech": "What to say OUT LOUD in Korean. Natural, human, uses fillers (아, 음, 저기요, 잠깐만요). Never repeat the same sentence.",
  "english_update": "1-2 sentences: what you said, what happened.",
  "action": "SPEAK",
  "hitl_buttons": null
}}

"action" must be one of:
- "SPEAK"               → Continue conversation normally
- "CONSULT_USER"        → Pause for student decision. Set hitl_buttons to 2-3 short strings.
- "DEAL_CLOSED"         → Price/deal successfully agreed (bargain mode only)
- "TASK_COMPLETE"       → Non-bargaining task done (directions, order, pharmacy, official)
- "REQUEST_FULFILLED"   → General request answered
- "SESSION_WRAP_COMPLETE" → Polite wrap-up after finalized session

When action is "CONSULT_USER", hitl_buttons must be a JSON array like:
["Yes, Accept", "Push Lower", "Walk Away"]  ← bargaining
["Sounds good", "Ask differently", "Leave"] ← request
["Confirm", "Clarify more", "Cancel"]       ← official

━━ CONVERSATION RULES ━━
1. React to EXACTLY what the local said — never hallucinate information.
2. Use natural Korean: 혹시, 그러면, 좀, -ㄹ게요, 감사합니다, 죄송한데요.
3. Keep korean_speech under 3 sentences.
4. english_update max 2 sentences.
5. If local refuses/stuck in bargain → CONSULT_USER with relevant buttons.
6. For bargain mode: push 2-3 times naturally before accepting. Don't give up immediately.
7. For non-bargain: move to TASK_COMPLETE/REQUEST_FULFILLED once info is obtained.
"""

TONE_MODIFIERS = {
    "bargain": """TONE: Confident but polite negotiator. Push for a discount but keep it friendly.
Use: 학생이라서요 (I'm a student), 현금으로 드릴게요 (I'll pay cash), 좀 더 깎아주시면 (if you can lower it a bit).
Strategy: Do NOT accept the first price. Make 2-3 attempts before consulting the student.
When seller gives final price and it's reasonable → CONSULT_USER ["Accept this price", "Try one more time", "Walk away"].
When student chooses Accept → respond accepting gracefully → DEAL_CLOSED.
IMPORTANT: Once DEAL_CLOSED has been returned, the session is sealed. Do not ask for more discounts.""",

    "directions": """TONE: Polite, slightly confused tourist. Humble forms (-ㄹ 수 있을까요?, 죄송한데요).
Ask for step-by-step directions. Confirm you understood each step by repeating it back.
When you have full directions → TASK_COMPLETE.""",

    "food_order": """TONE: Friendly and specific. You are ordering food with dietary restrictions.
Ask clearly: 돼지고기 없나요? (no pork?), 고기 빼주세요 (remove meat please), 멸치 육수 쓰나요? (do you use anchovy broth?).
Confirm the order before finishing → TASK_COMPLETE.""",

    "pharmacy": """TONE: Calm, clear, medical.
Describe symptoms: 여기가 아파요, 며칠째, 열이 있어요.
Ask: what medicine (무슨 약) and how to take it (하루에 몇 번).
When you have recommendation → TASK_COMPLETE.""",

    "official": """TONE: Respectful, formal. At bank/immigration/주민센터.
Use: -겠습니다, -습니까, 도움 부탁드립니다.
Ask what documents are needed, the process step by step.
When you have the info → TASK_COMPLETE.""",

    "general": """TONE: Friendly, natural, helpful.
Fulfil the mission as described.
When done → REQUEST_FULFILLED.""",
}

# Terminal actions that seal the session
TERMINAL_ACTIONS = {"DEAL_CLOSED", "TASK_COMPLETE", "REQUEST_FULFILLED"}

# ── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="K-Transition OS Voice Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

try:
    with open("index.html", "r", encoding="utf-8") as f:
        HTML_CONTENT = f.read()
except FileNotFoundError:
    HTML_CONTENT = "<h1>index.html not found — run from the negotiator/ directory</h1>"


@app.get("/")
async def get_index():
    return HTMLResponse(HTML_CONTENT)


@app.get("/health")
async def health():
    return {"status": "ok", "time": time.time()}


# ══════════════════════════════════════════════════════════════
# SECURITY FIX: Telegram initData HMAC validation
# ══════════════════════════════════════════════════════════════
# Without this, ANY request with a known user_id can read
# another user's full conversation history.
# Telegram Mini Apps send initData — a signed string proving
# "this specific user opened this Mini App from Telegram."
# We verify the signature using the bot token as the secret.

import hmac as _hmac
import hashlib as _hashlib
from urllib.parse import unquote as _unquote

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")


def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp initData.
    Returns parsed user dict if valid, None if tampered/invalid.
    Docs: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not init_data or not BOT_TOKEN:
        return None
    try:
        parsed = {}
        for part in _unquote(init_data).split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                parsed[k] = v

        received_hash = parsed.pop("hash", "")
        if not received_hash:
            return None

        # Build data-check string: sorted key=value pairs joined by 

        data_check = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        # HMAC-SHA256: secret = HMAC-SHA256("WebAppData", bot_token)
        secret_key = _hmac.new(
            "WebAppData".encode(),
            BOT_TOKEN.encode(),
            _hashlib.sha256,
        ).digest()

        expected = _hmac.new(
            secret_key,
            data_check.encode(),
            _hashlib.sha256,
        ).hexdigest()

        if not _hmac.compare_digest(expected, received_hash):
            logger.warning("initData validation FAILED — possible tampering")
            return None

        # Parse user field
        user_str = parsed.get("user", "{}")
        import json as _json
        return _json.loads(user_str)

    except Exception as e:
        logger.error("initData validation error: %s", e)
        return None


# ══════════════════════════════════════════════════════════════
# STATE MANAGEMENT: /get_history endpoint
# Mini App JS fetches this on open to restore conversation state.
# Returns last N messages for the authenticated user.
# ══════════════════════════════════════════════════════════════

from fastapi import Header

@app.get("/get_history")
async def get_history(
    x_init_data: str = Header(default="", alias="X-Init-Data"),
    limit: int = 20,
):
    """
    Fetch conversation history for authenticated Mini App user.
    Security: requires valid Telegram initData in X-Init-Data header.
    Frontend sends this header on every request.
    Without it, anyone knowing a user_id could read their history.
    """
    user = validate_telegram_init_data(x_init_data)
    if not user:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            {"error": "Invalid or missing Telegram authentication"},
            status_code=401
        )

    user_id = user.get("id")
    if not user_id:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "No user ID in token"}, status_code=401)

    # Read from SQLite (production: swap for Supabase PostgreSQL)
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "ktransition.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        rows = conn.execute(
            "SELECT role, content, timestamp FROM chat_history "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        conn.close()
        messages = [dict(r) for r in reversed(rows)]
        return {"user_id": user_id, "messages": messages, "count": len(messages)}
    except Exception as e:
        logger.error("get_history DB error: %s", e)
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Database error"}, status_code=500)


@app.post("/queue_notify")
async def queue_notify(request: dict):
    """
    Internal endpoint: FastAPI process queues a message for the bot to send.
    Bot process polls pending_notifications table every 10s and delivers it.
    This decouples FastAPI's uvicorn event loop from PTB's event loop.
    Only callable with internal API key (set INTERNAL_API_KEY in .env).
    """
    api_key = os.getenv("INTERNAL_API_KEY", "")
    if api_key and request.get("api_key") != api_key:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    user_id = request.get("user_id")
    message = request.get("message", "")
    if not user_id or not message:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "user_id and message required"}, status_code=400)

    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "ktransition.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "INSERT INTO pending_notifications (user_id, message, sent, created_at) VALUES (?,?,0,?)",
            (user_id, message[:4000], time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        )
        conn.commit()
        conn.close()
        return {"status": "queued", "user_id": user_id}
    except Exception as e:
        logger.error("queue_notify error: %s", e)
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Queue write failed"}, status_code=500)


# ── Session State ─────────────────────────────────────────────────────────────

class AssistantSession:
    def __init__(self, websocket: WebSocket, goal: str, context_type: str = "general"):
        self.ws           = websocket
        self.goal         = goal
        self.context_type = context_type

        self.groq_client = groq.AsyncGroq(api_key=GROQ_API_KEY)
        self.memory: list[dict] = []

        self.audio_buffer = bytearray()
        self.audio_queue  = asyncio.Queue()

        self.barge_in_event = asyncio.Event()
        self.hitl_event     = asyncio.Event()
        self.hitl_choice: Optional[str] = None

        self.is_speaking    = False
        self.is_processing  = False
        self.is_done        = False

        # v3: deal state tracking — once True, LLM is told session is FINALIZED
        self.deal_finalized = False
        self.last_activity  = time.time()

    async def send_json(self, data: dict):
        try:
            await self.ws.send_text(json.dumps(data))
        except Exception as e:
            logger.error("send_json failed: %s", e)

    async def send_audio(self, audio_bytes: bytes):
        try:
            await self.ws.send_bytes(audio_bytes)
        except Exception as e:
            logger.error("send_audio failed: %s", e)

    def build_system_prompt(self) -> str:
        tone   = TONE_MODIFIERS.get(self.context_type, TONE_MODIFIERS["general"])
        status = "FINALIZED — wrap up only, do NOT re-open bargaining" if self.deal_finalized else "ACTIVE"
        return UNIVERSAL_SYSTEM_PROMPT.format(
            mission_goal=self.goal,
            context_type=self.context_type,
            session_status=status,
            tone_modifier=tone,
        )


# ── Core Pipeline ─────────────────────────────────────────────────────────────

async def transcribe_audio(session: AssistantSession, audio_bytes: bytes) -> str:
    if not audio_bytes or len(audio_bytes) < 1000:
        return ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            transcript = await session.groq_client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=("voice.ogg", f, "audio/ogg"),
                prompt="Korean and English mixed. 안녕하세요.",
            )
        os.unlink(tmp_path)
        text = transcript.text.strip()
        logger.info("Whisper: '%s'", text)
        return text
    except Exception as e:
        logger.error("Whisper STT failed: %s", e)
        return ""


async def run_llm(session: AssistantSession, user_input: str) -> dict:
    """Groq LLaMA. Respects deal_finalized flag via system prompt."""
    session.memory.append({"role": "user", "content": user_input})
    system       = session.build_system_prompt()
    full_response = ""

    try:
        stream = await session.groq_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": system}, *session.memory],
            stream=True,
            max_tokens=500,
            temperature=0.7,
        )
        async for chunk in stream:
            if session.barge_in_event.is_set():
                logger.info("LLM interrupted by barge-in")
                break
            delta = chunk.choices[0].delta.content or ""
            full_response += delta

    except Exception as e:
        logger.error("LLM failed: %s", e)
        return {
            "korean_speech": "죄송합니다, 잠깐만요.",
            "english_update": "AI error, retrying...",
            "action": "SPEAK",
            "hitl_buttons": None,
        }

    try:
        clean  = full_response.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("LLM non-JSON: %s", full_response[:100])
        result = {
            "korean_speech":  full_response[:200] or "잠깐만요.",
            "english_update": "Processing...",
            "action":         "SPEAK",
            "hitl_buttons":   None,
        }

    session.memory.append({"role": "assistant", "content": full_response})
    return result


async def stream_tts(session: AssistantSession, text: str, voice: str) -> bool:
    """Collect all TTS audio then send in one shot for smooth playback."""
    if not text or not text.strip():
        return True
    session.is_speaking = True
    interrupted = False
    try:
        communicate  = edge_tts.Communicate(text, voice, rate="+5%")
        audio_buffer = bytearray()
        async for chunk in communicate.stream():
            if session.barge_in_event.is_set():
                interrupted = True
                break
            if chunk["type"] == "audio":
                audio_buffer.extend(chunk["data"])
            await asyncio.sleep(0)

        if audio_buffer and not interrupted:
            await session.send_audio(bytes(audio_buffer))
            await asyncio.sleep(0.1)

    except Exception as e:
        logger.error("TTS failed: %s", e)
        interrupted = True
    finally:
        session.is_speaking = False
    return not interrupted


async def generate_session_summary(session: AssistantSession) -> str:
    """Generate a 2-3 sentence summary of what was accomplished."""
    if not session.memory:
        return "Session completed."
    try:
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content'][:200]}"
            for m in session.memory[-10:]
        )
        prompt = (
            f"Summarise this Korean conversation session in 2-3 English sentences.\n"
            f"Goal: {session.goal}\nContext: {session.context_type}\n\n"
            f"Conversation:\n{history_text}\n\n"
            f"Write a brief, practical summary of what was achieved. No markdown."
        )
        resp = await session.groq_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Summary generation failed: %s", e)
        return f"Session completed. Goal: {session.goal}"


def show_hitl_buttons(buttons: list[str]) -> dict:
    return {"type": "hitl_buttons", "buttons": buttons}


async def run_conversation_loop(session: AssistantSession):
    """
    Main turn loop.
    CHANGED v3: checks deal_finalized. If true, only allows one wrap-up turn,
    then sends session_ended with summary. Prevents re-opening bargaining.
    """
    while not session.is_done:
        session.last_activity = time.time()

        # Wait for audio or user input
        try:
            audio_bytes = await asyncio.wait_for(session.audio_queue.get(), timeout=300.0)
        except asyncio.TimeoutError:
            logger.info("Session idle timeout")
            session.is_done = True
            break

        if session.is_done:
            break

        # Transcribe
        session.barge_in_event.clear()
        session.is_processing = True
        await session.send_json({"type": "status", "text": "Listening..."})

        user_input = await transcribe_audio(session, audio_bytes)
        if not user_input:
            session.is_processing = False
            continue

        await session.send_json({"type": "user_speech", "text": user_input})
        await session.send_json({"type": "status", "text": "Responding..."})

        # LLM
        result        = await run_llm(session, user_input)
        action        = result.get("action", "SPEAK")
        korean_speech = result.get("korean_speech", "")
        english_update= result.get("english_update", "")
        hitl_buttons  = result.get("hitl_buttons")

        # Send English update to student
        await session.send_json({"type": "assistant_update", "text": english_update, "action": action})

        # --- Realistic deal handling ---
        if action in TERMINAL_ACTIONS and not session.deal_finalized:
            # Seal the deal — one wrap-up turn allowed, then close
            session.deal_finalized = True
            logger.info("Deal/task finalized. Action=%s. Sealing session.", action)

            # Speak the closing line
            await stream_tts(session, korean_speech, KOREAN_TTS_VOICE)

            # Generate summary
            await session.send_json({"type": "status", "text": "Generating summary..."})
            summary = await generate_session_summary(session)

            await session.send_json({
                "type":    "session_ended",
                "action":  action,
                "summary": summary,
            })
            session.is_done = True
            break

        elif action == "SESSION_WRAP_COMPLETE":
            # Wrap-up complete — now fully close
            await stream_tts(session, korean_speech, KOREAN_TTS_VOICE)
            summary = await generate_session_summary(session)
            await session.send_json({
                "type":    "session_ended",
                "action":  action,
                "summary": summary,
            })
            session.is_done = True
            break

        elif action == "CONSULT_USER" and isinstance(hitl_buttons, list):
            # Pause for student decision
            await stream_tts(session, korean_speech, KOREAN_TTS_VOICE)
            await session.send_json(show_hitl_buttons(hitl_buttons))

            session.hitl_event.clear()
            session.hitl_choice = None

            try:
                await asyncio.wait_for(session.hitl_event.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                session.hitl_choice = hitl_buttons[0] if hitl_buttons else "Continue"

            choice = session.hitl_choice or "Continue"
            await session.send_json({"type": "status", "text": f"Student chose: {choice}"})

            # Feed choice back to LLM
            follow_up  = await run_llm(session, f"[Student decision: {choice}]")
            f_action   = follow_up.get("action", "SPEAK")
            f_speech   = follow_up.get("korean_speech", "")
            f_update   = follow_up.get("english_update", "")

            await session.send_json({"type": "assistant_update", "text": f_update, "action": f_action})

            if f_action in TERMINAL_ACTIONS and not session.deal_finalized:
                session.deal_finalized = True
                await stream_tts(session, f_speech, KOREAN_TTS_VOICE)
                summary = await generate_session_summary(session)
                await session.send_json({
                    "type":    "session_ended",
                    "action":  f_action,
                    "summary": summary,
                })
                session.is_done = True
                break
            else:
                await stream_tts(session, f_speech, KOREAN_TTS_VOICE)

        else:
            # Normal SPEAK turn
            await stream_tts(session, korean_speech, KOREAN_TTS_VOICE)

        session.is_processing = False


# ── WebSocket Endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session: Optional[AssistantSession] = None
    conversation_task: Optional[asyncio.Task] = None

    try:
        while True:
            raw = await websocket.receive()

            # Text message (JSON control)
            if "text" in raw:
                try:
                    msg = json.loads(raw["text"])
                except json.JSONDecodeError:
                    continue

                action = msg.get("action", "")

                if action == "start":
                    goal         = msg.get("goal", "Help me in Korea")
                    context_type = msg.get("context_type", "general")
                    session = AssistantSession(websocket, goal, context_type)
                    logger.info("Session started: goal='%s' type='%s'", goal, context_type)

                    # Opening greeting from AI
                    greeting_input = f"[Session start. Goal: {goal}. Greet naturally and begin.]"
                    greeting = await run_llm(session, greeting_input)
                    g_speech = greeting.get("korean_speech", "안녕하세요!")
                    g_update = greeting.get("english_update", "Starting...")
                    await websocket.send_text(json.dumps({"type": "assistant_update", "text": g_update, "action": "SPEAK"}))
                    await stream_tts(session, g_speech, KOREAN_TTS_VOICE)

                    conversation_task = asyncio.create_task(run_conversation_loop(session))

                elif action == "user_speech" and session and not session.deal_finalized:
                    # Text input from user (typed or goal-mic)
                    text = msg.get("text", "").strip()
                    if text:
                        await session.audio_queue.put(b"")   # placeholder
                        # Override: process text directly
                        result = await run_llm(session, text)
                        r_action = result.get("action", "SPEAK")
                        r_speech = result.get("korean_speech", "")
                        r_update = result.get("english_update", "")
                        await websocket.send_text(json.dumps({"type": "assistant_update", "text": r_update, "action": r_action}))
                        await stream_tts(session, r_speech, KOREAN_TTS_VOICE)

                        if r_action in TERMINAL_ACTIONS and not session.deal_finalized:
                            session.deal_finalized = True
                            summary = await generate_session_summary(session)
                            await websocket.send_text(json.dumps({
                                "type": "session_ended",
                                "action": r_action,
                                "summary": summary,
                            }))
                            session.is_done = True

                elif action == "barge_in" and session:
                    session.barge_in_event.set()
                    await asyncio.sleep(0.1)
                    session.barge_in_event.clear()

                elif action == "hitl_choice" and session:
                    session.hitl_choice = msg.get("choice", "")
                    session.hitl_event.set()

                elif action == "user_modify" and session and not session.deal_finalized:
                    # Feature: modify goal mid-session
                    new_goal = msg.get("goal", "").strip()
                    if new_goal:
                        session.goal = new_goal
                        session.memory.append({
                            "role": "user",
                            "content": f"[Goal updated: {new_goal}]"
                        })
                        await websocket.send_text(json.dumps({
                            "type": "status",
                            "text": f"Goal updated: {new_goal}"
                        }))

                elif action == "end" and session:
                    session.is_done = True
                    if conversation_task:
                        conversation_task.cancel()
                        try:
                            await conversation_task
                        except asyncio.CancelledError:
                            pass

            # Binary message = audio chunk from mic
            elif "bytes" in raw and session and not session.deal_finalized:
                chunk = raw["bytes"]
                if chunk:
                    session.audio_buffer.extend(chunk)
                else:
                    # Empty bytes = end of utterance marker
                    if session.audio_buffer:
                        audio_data = bytes(session.audio_buffer)
                        session.audio_buffer = bytearray()
                        await session.audio_queue.put(audio_data)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        if session:
            session.is_done = True
        if conversation_task and not conversation_task.done():
            conversation_task.cancel()
            try:
                await conversation_task
            except asyncio.CancelledError:
                pass


# ── Goal Transcription Endpoint ───────────────────────────────────────────────

@app.post("/transcribe_goal")
async def transcribe_goal(file: UploadFile = File(...)):
    """
    Negotiator Change 4: Transcribe spoken goal from setup screen mic button.
    Frontend sends audio as multipart. Returns {text: "..."}.
    """
    if not GROQ_API_KEY:
        return JSONResponse({"error": "No Groq API key"}, status_code=503)
    try:
        audio_bytes = await file.read()
        client = groq.AsyncGroq(api_key=GROQ_API_KEY)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            transcript = await client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=("voice.ogg", f, "audio/ogg"),
                prompt="Korean or English. The user is describing their goal.",
            )
        os.unlink(tmp_path)
        return JSONResponse({"text": transcript.text.strip()})
    except Exception as e:
        logger.error("Goal transcription failed: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)
