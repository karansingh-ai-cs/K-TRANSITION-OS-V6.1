"""
main.py — K-Transition OS v6.0
=================================
Advanced Features Added:
  ✅ Orpheus TTS  — Groq neural TTS (10x better than edge-tts, Korean supported)
  ✅ Photo-to-mission — Llama 4 Scout vision detects goal + context from image
  ✅ Emotion/tension detector — mood, deal%, next-move after each local response
  ✅ Live phrase cheatsheet — top 5 Korean phrases sent every turn
  ✅ Pre-battle briefing — 10-sec cultural tip before session begins
  ✅ Post-deal analyzer — score/100, what worked, what to improve, timeline
  ✅ (Session history is handled entirely in the frontend via localStorage)

Architecture: Client mic → WS → Groq Whisper → LLaMA 3.3 70B → Orpheus TTS → WS → Client
"""

import asyncio
import json
import os
import io
import re
import base64
import logging
import time
from typing import Optional
from dotenv import load_dotenv
# Load from current dir first, then parent dir (when run from bot.py)
import pathlib
_this_dir = pathlib.Path(__file__).resolve().parent
load_dotenv(_this_dir / ".env")
load_dotenv(_this_dir.parent / ".env")  # parent .env for merged deployment

import httpx
import edge_tts
import groq
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

_groq_keys_str       = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEYS        = [k.strip() for k in _groq_keys_str.split(",") if k.strip()]
WHISPER_MODEL        = "whisper-large-v3"
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768"
]
GROQ_LIGHT_MODEL = "llama-3.1-8b-instant"
VISION_MODEL         = os.getenv("VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
KOREAN_TTS_VOICE     = "ko-KR-SunHiNeural"          # edge-tts fallback (FREE and BEST)
ENGLISH_TTS_VOICE    = "en-US-AriaNeural"           # edge-tts fallback (FREE and BEST)

# ── Orpheus TTS (Groq) ─────────────────────────────────────────────────────────
# Groq deprecated PlayAI TTS in Dec 2025 and launched Orpheus (Canopy Labs).
# Set USE_ORPHEUS_TTS=false in .env to fall back to edge-tts.
USE_ORPHEUS_TTS      = os.getenv("USE_ORPHEUS_TTS", "true").lower() == "true"
ORPHEUS_MODEL        = os.getenv("ORPHEUS_MODEL", "orpheus-3b-0.1-ft-q4_k_m")
ORPHEUS_KOREAN_VOICE = os.getenv("ORPHEUS_KOREAN_VOICE", "Seraphina")   # Korean-capable voice
ORPHEUS_ENGLISH_VOICE= os.getenv("ORPHEUS_ENGLISH_VOICE", "Aoede")      # English voice
# ^ Update these voice names from https://console.groq.com/docs/text-speech

import random
def get_groq_key():
    return random.choice(GROQ_API_KEYS) if GROQ_API_KEYS else None

def get_groq_client():
    key = get_groq_key()
    return groq.AsyncGroq(api_key=key) if key else None

# ── System Prompt (v6 — includes emotion/phrases in JSON output) ───────────────

UNIVERSAL_SYSTEM_PROMPT = """You are 한국 AI 도우미 (Korean AI Helper), the voice of K-Transition OS.
You speak Korean DIRECTLY to a Korean person on behalf of an international student who cannot speak Korean.

STUDENT'S MISSION: {mission_goal}
SITUATION TYPE: {context_type}

{tone_modifier}

━━━━━ LANGUAGE PURITY — ABSOLUTE RULE ━━━━━
The "korean_speech" field must contain ONLY Korean Hangul characters and standard punctuation (.,!?~…).
STRICTLY FORBIDDEN in korean_speech: Chinese characters (漢字), Hindi/Devanagari, Thai script, Japanese, Arabic, or ANY non-Korean writing system.
If you need a foreign word, write its phonetic Hangul spelling. Example: "커피" not "coffee" or "咖啡".

━━━━━ HUMAN-IN-THE-LOOP (HITL) RULES ━━━━━
1. NEVER accept a final price, sign up for anything, or make any irreversible commitment without student approval.
2. If the local makes a counter-offer, or says something requiring the student's decision → use action: "CONSULT_USER".
3. If you have already used CONSULT_USER twice with no progress, stop escalating. Say a polite closing in Korean and use action: "SPEAK".
4. If the local firmly refuses — accept gracefully or consult student. Do NOT push the same argument more than once.
5. REACT to what the local actually said.

━━━━━ NUNCHI (눈치) — SITUATIONAL AWARENESS ━━━━━
Read the room. If the local sounds annoyed, rushed, or uninterested:
- Back off immediately with a polite 죄송합니다
- Shift to a softer approach or use CONSULT_USER
Nunchi is more important than winning the negotiation.

━━━━━ STRICT JSON OUTPUT FORMAT ━━━━━
Respond ONLY with this exact JSON. No markdown. No extra fields. No preamble:
{{
  "korean_speech": "Korean Hangul ONLY. Empty string if action is CONSULT_USER.",
  "english_update": "1-2 sentence English summary: what the local said + what student needs to know.",
  "action": "SPEAK",
  "hitl_buttons": null,
  "mood": "friendly",
  "deal_chance": 75,
  "next_move": "One short English tip for the student's next move.",
  "phrases": [
    {{"kr": "얼마예요?", "rom": "eolma-eyo?", "en": "How much is it?"}},
    {{"kr": "깎아 주세요", "rom": "kkakka juseyo", "en": "Please give a discount"}},
    {{"kr": "학생이에요", "rom": "haksaengieyo", "en": "I'm a student"}},
    {{"kr": "현금이에요", "rom": "hyeongeum-ieyo", "en": "I have cash"}},
    {{"kr": "감사합니다", "rom": "gamsahamnida", "en": "Thank you"}}
  ]
}}

FIELD RULES:
- "action" → exactly "SPEAK" or "CONSULT_USER"
- "mood" → exactly one of: "friendly" | "neutral" | "annoyed" | "busy" | "uncertain"
- "deal_chance" → integer 0-100 (realistic estimate of success). Use null if not a deal/bargain context.
- "next_move" → 1 short sentence (English) on what student should do/expect next. Never empty.
- "phrases" → exactly 5 items. Choose the most relevant phrases for THIS specific moment in the conversation.
"""

# ── Pre-battle Briefing Prompt ─────────────────────────────────────────────────

BRIEFING_PROMPT = """You are a Korean cultural coach. A student is about to enter this situation:

GOAL: {goal}
SITUATION TYPE: {context_type}

Give a quick spoken briefing (will be read aloud via TTS) covering:
1. What Korean people normally expect in this exact situation (be specific, not generic)
2. One common mistake foreigners make here
3. One power move or phrase that will immediately help

Keep it short — 3 sentences max, natural spoken English, no bullet points.
Also provide ONE key Korean phrase (the single most important one for this situation).

Respond ONLY with this JSON (no markdown):
{{"briefing_text": "your 3-sentence spoken briefing here", "key_phrase_kr": "Korean phrase", "key_phrase_rom": "romanization", "key_phrase_en": "meaning"}}
"""

# ── Post-Deal Analysis Prompt ──────────────────────────────────────────────────

DEAL_ANALYSIS_PROMPT = """Analyze this Korean conversation session as a negotiation/communication coach.

Review the full conversation and provide:
1. A score from 0-100 (how well the student achieved their goal)
2. A letter grade (A/B/C/D/F)
3. A 2-sentence summary of what happened
4. What went well (1-2 sentences)
5. What could have been better (1-2 sentences)
6. Key moments timeline (3-5 items, each with a short label)

Respond ONLY with this JSON (no markdown):
{{
  "score": 72,
  "grade": "B",
  "summary": "2-sentence summary of the session outcome.",
  "went_well": "What the student did effectively.",
  "improve": "What could have been done better.",
  "timeline": [
    {{"moment": 1, "label": "AI opened with friendly greeting"}},
    {{"moment": 2, "label": "Local gave initial price ₩22,000"}},
    {{"moment": 3, "label": "Student used student card — local softened"}},
    {{"moment": 4, "label": "Deal closed at ₩18,000 (18% off)"}}
  ]
}}
"""

# ── Vocab Prompt ───────────────────────────────────────────────────────────────

VOCAB_PROMPT = """Based on this conversation, extract the 5 most useful Korean words or phrases the student should remember.
Choose words that were actually helpful in this specific interaction.
Respond with EXACTLY this JSON (no markdown, no extra text):
{"vocab": [{"korean": "한국어", "english": "meaning / when to use it"}, ...]}
"""

# ── Tone Modifiers ─────────────────────────────────────────────────────────────

TONE_MODIFIERS = {
    "bargain": """TONE: Polite but persistent negotiator.
Real-life tactics:
- Open with a friendly greeting and a specific lower price
- Use 학생이라서 (I'm a student) and 현금으로 결제할게요 (I'll pay cash)
- If refused: acknowledge their price, ask for ANY small discount (even ₩500)
- If refused twice: use CONSULT_USER — ask student to accept, walk away, or try a bundle deal
- Never sound desperate. Stay warm and smile in your tone.
Final goal: close a deal both sides feel okay about.""",

    "directions": """TONE: Polite, slightly confused tourist. Use humble speech forms.
Real-life tactics:
- Ask clearly for the destination name in Korean
- Confirm each directional step: 왼쪽이요? 오른쪽이요? (Left? Right?)
- If instructions are too fast: 죄송한데, 천천히 말씀해 주실 수 있어요?
- Repeat the route back to confirm understanding
- When you have complete directions → CONSULT_USER asking if student wants to confirm or ask again.""",

    "food_order": """TONE: Friendly, specific, clear about dietary needs.
Real-life tactics:
- State the order clearly first, THEN ask about ingredients
- Key phrases: 돼지고기 들어가나요?, 고기 빼주세요, 멸치 육수 쓰나요?
- If unavailable, use CONSULT_USER for alternative
- Confirm the final order before closing: 주문 확인해 주세요
- When order is confirmed → CONSULT_USER asking if student wants to add anything""",

    "pharmacy": """TONE: Calm, clear, respectful. Medical context.
Real-life tactics:
- Describe symptoms specifically: 어제부터, 여기가 아파요, 열이 38도예요
- Ask about dosage AND frequency: 하루에 몇 번 먹어요? / 밥 먹고 먹어야 해요?
- Ask about side effects: 부작용이 있나요?
- Confirm medicine name: 약 이름이 뭐예요?
- When medicine + instructions received → CONSULT_USER to confirm student is satisfied""",

    "official": """TONE: Formal, patient, thorough. Government/bank context.
Real-life tactics:
- Use formal endings: -겠습니다, -습니다, -주시겠어요?
- Ask one question at a time
- Ask about documents: 어떤 서류가 필요한가요?
- Ask about processing time: 얼마나 걸려요?
- If unclear: 다시 한번 말씀해 주시겠어요?
- When all info gathered → CONSULT_USER confirming with student""",

    "landlord": """TONE: Respectful tenant.
Real-life tactics:
- Be specific about the problem: 화장실 물이 안 나와요, 보일러가 고장났어요
- Ask about repair timeline: 언제 고쳐주실 수 있어요?
- If urgent: 지금 많이 불편해요. 빨리 부탁드릴게요.
- Deposit: 보증금 언제 돌려받을 수 있어요?
- Use CONSULT_USER if they refuse or give unacceptable date""",

    "transport": """TONE: Slightly lost, polite, direct.
Real-life tactics:
- At taxi: 여기로 가주세요 + address clearly
- Ask for meter: 미터기 켜주세요
- On bus/subway: 이 버스 [destination] 가요?
- If lost: 이 역이 [name]역이에요?
- When confirmed → CONSULT_USER asking if student needs anything else""",

    "general": """TONE: Friendly, helpful, natural. Adapt to the actual situation.
Handle whatever the student's mission says. Be practical and warm.
When the core task is done → use CONSULT_USER asking if student needs more help.""",
}

# ── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="K-Transition OS v6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    index_path = _this_dir / "index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        HTML_CONTENT = f.read()
except FileNotFoundError:
    HTML_CONTENT = f"<h1>index.html not found at {index_path}</h1>"

@app.get("/")
async def get_index():
    return HTMLResponse(HTML_CONTENT)

# ── Session State ──────────────────────────────────────────────────────────────

class AssistantSession:
    def __init__(self, websocket: WebSocket, goal: str, context_type: str = "general"):
        self.ws           = websocket
        self.goal         = goal
        self.context_type = context_type
        self.groq_client  = get_groq_client()

        self.memory: list[dict] = []
        self.audio_buffer   = bytearray()

        self.barge_in_event = asyncio.Event()
        self.hitl_event     = asyncio.Event()
        self.hitl_choice: Optional[str] = None

        self.is_speaking    = False
        self.is_processing  = False
        self.is_done        = False
        self.consult_depth  = 0
        self.start_time     = time.time()
        self.turn_count     = 0

    async def send_json(self, data: dict):
        try:
            await self.ws.send_text(json.dumps(data))
        except Exception as e:
            logger.error(f"send_json failed: {e}")

    async def send_audio(self, audio_bytes: bytes):
        try:
            await self.ws.send_bytes(audio_bytes)
        except Exception as e:
            logger.error(f"send_audio failed: {e}")

    def build_system_prompt(self) -> str:
        tone = TONE_MODIFIERS.get(self.context_type, TONE_MODIFIERS["general"])
        return UNIVERSAL_SYSTEM_PROMPT.format(
            mission_goal=self.goal,
            context_type=self.context_type,
            tone_modifier=tone,
        )

# ── Noise Filter ───────────────────────────────────────────────────────────────

def is_valid_transcription(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return False
    valid = re.findall(r'[\w\s\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]', text)
    ratio = len(valid) / max(len(text), 1)
    if ratio < 0.55:
        logger.warning(f"Noise filter rejected: {text!r} (valid_ratio={ratio:.2f})")
        return False
    return True

# ── TTS: Orpheus (Groq) ────────────────────────────────────────────────────────

async def tts_orpheus_bytes(text: str, lang: str = "ko") -> Optional[bytes]:
    """Call Groq's Orpheus TTS API. Returns MP3 bytes or None on failure."""
    api_key = get_groq_key()
    if not api_key or not text.strip():
        return None
    voice = ORPHEUS_KOREAN_VOICE if lang == "ko" else ORPHEUS_ENGLISH_VOICE
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model":  ORPHEUS_MODEL,
                    "input":  text,
                    "voice":  voice,
                    "response_format": "mp3",
                },
            )
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"Orpheus TTS HTTP {resp.status_code}: {resp.text[:200]}")
                return None
    except Exception as e:
        logger.error(f"Orpheus TTS request failed: {e}")
        return None


async def stream_tts_orpheus(session: "AssistantSession", text: str, lang: str = "ko") -> bool:
    """Stream Orpheus TTS. Falls back to edge-tts if Orpheus fails."""
    if not text or not text.strip():
        return True
    session.is_speaking = True
    try:
        audio_bytes = await tts_orpheus_bytes(text, lang)
        if audio_bytes:
            if not session.barge_in_event.is_set():
                await session.send_audio(audio_bytes)
            return not session.barge_in_event.is_set()
        else:
            logger.info("Orpheus TTS failed — falling back to edge-tts")
            # Fall back to edge-tts
            voice = KOREAN_TTS_VOICE if lang == "ko" else ENGLISH_TTS_VOICE
            return await _stream_edge_tts(session, text, voice)
    finally:
        session.is_speaking = False


async def _stream_edge_tts(session: "AssistantSession", text: str, voice: str) -> bool:
    """Low-level edge-tts stream."""
    interrupted = False
    try:
        communicate = edge_tts.Communicate(text, voice, rate="+5%")
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
    except Exception as e:
        logger.error(f"edge-tts failed: {e}")
    return not interrupted


async def stream_tts(session: "AssistantSession", text: str, voice: str) -> bool:
    """Main TTS dispatcher: Orpheus if enabled, else edge-tts."""
    if not text or not text.strip():
        return True
    session.is_speaking = True
    try:
        lang = "ko" if "ko" in voice.lower() or voice == KOREAN_TTS_VOICE else "en"
        if USE_ORPHEUS_TTS:
            return await stream_tts_orpheus(session, text, lang)
        else:
            return await _stream_edge_tts(session, text, voice)
    finally:
        session.is_speaking = False

# ── Image Analysis Endpoint (Llama 4 Scout Vision) ────────────────────────────

@app.post("/analyze-image")
async def analyze_image(request: Request):
    """
    Accepts { "image": "<base64 jpeg/png>" }
    Returns { "goal": "...", "context_type": "..." }
    Uses Llama 4 Scout vision (free on Groq).
    """
    groq_client = get_groq_client()
    if not groq_client:
        return JSONResponse({"error": "No Groq API key configured"}, status_code=500)

    body = await request.json()
    image_b64 = body.get("image", "")
    if not image_b64:
        return JSONResponse({"error": "No image provided"}, status_code=400)

    # Strip data URL prefix if present
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        response = await groq_client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are helping an international student in South Korea. "
                            "Analyze this image (it could be a shop signboard, menu, price tag, "
                            "product label, receipt, or any Korean establishment). "
                            "Detect what the student would most likely want to do here.\n\n"
                            "Respond ONLY with valid JSON, no markdown:\n"
                            '{"goal": "specific actionable goal in English (1-2 sentences, include any prices/items visible)", '
                            '"context_type": "one of: bargain | food_order | pharmacy | directions | transport | official | landlord | general", '
                            '"detected_place": "short English description of what this image shows"}'
                        )
                    }
                ]
            }],
            max_tokens=300,
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        # Strip markdown if model added it anyway
        raw = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)
        return JSONResponse(result)
    except json.JSONDecodeError as e:
        logger.error(f"Vision model JSON parse error: {e} | raw: {raw[:200]}")
        return JSONResponse({"error": "Could not parse vision response"}, status_code=500)
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ── LLM Calls ─────────────────────────────────────────────────────────────────

async def run_llm(session: AssistantSession, user_input: str) -> dict:
    if user_input:
        session.memory.append({"role": "user", "content": user_input})
    system = session.build_system_prompt()

    raw = None
    for model in GROQ_MODELS:
        try:
            response = await session.groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, *session.memory[-12:]],
                max_tokens=700,
                temperature=0.6,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            break
        except Exception as e:
            if "429" in str(e):
                logger.warning(f"Groq rate limit on {model} — trying next model...")
                continue
            logger.error(f"LLM failed on {model}: {e}")
            break

    if raw:
        try:
            parsed = json.loads(raw)
            session.memory.append({"role": "assistant", "content": raw})
            session.turn_count += 1
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"LLM JSON parse failed: {e}")

    logger.error("All LLM models failed or returned invalid JSON.")
    return {
        "korean_speech": "죄송합니다, 잠깐만요.",
        "english_update": "AI had a brief error — retrying.",
        "action": "SPEAK",
        "hitl_buttons": None,
        "mood": "neutral",
        "deal_chance": None,
        "next_move": "Waiting...",
        "phrases": [],
    }


async def generate_briefing(session: AssistantSession) -> dict:
    """Generate pre-battle cultural briefing. Returns dict with briefing_text + key phrase."""
    prompt = BRIEFING_PROMPT.format(goal=session.goal, context_type=session.context_type)
    for model in [GROQ_LIGHT_MODEL] + GROQ_MODELS:
        try:
            response = await session.groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.5,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            return json.loads(raw)
        except Exception as e:
            if "429" in str(e):
                continue
            logger.error(f"Briefing generation failed on {model}: {e}")
            break

    logger.error("All models failed for briefing generation.")
    return {
        "briefing_text": "You're about to speak with a Korean person. Be polite, patient, and use the phrases shown. The AI will speak for you — just record their responses.",
        "key_phrase_kr": "감사합니다",
        "key_phrase_rom": "gamsahamnida",
        "key_phrase_en": "Thank you"
    }


async def generate_post_deal_analysis(session: AssistantSession) -> dict:
    """Analyze the full conversation and return a deal quality score."""
    analysis_request = DEAL_ANALYSIS_PROMPT
    duration_mins = round((time.time() - session.start_time) / 60, 1)

    for model in [GROQ_LIGHT_MODEL] + GROQ_MODELS:
        try:
            response = await session.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"Session duration: {duration_mins} minutes. Goal: {session.goal}. Context: {session.context_type}."},
                    *session.memory[-20:],
                    {"role": "user", "content": analysis_request},
                ],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            result = json.loads(raw)
            result["duration_mins"] = duration_mins
            return result
        except Exception as e:
            if "429" in str(e):
                continue
            logger.error(f"Post-deal analysis failed on {model}: {e}")
            break

    logger.error("All models failed for post-deal analysis.")
    return {
        "score": 70,
        "grade": "B",
        "summary": "Session completed. Analysis unavailable.",
        "went_well": "You used the AI effectively to communicate.",
        "improve": "Try to note key phrases for next time.",
        "timeline": [],
        "duration_mins": duration_mins,
    }

# ── Barge-in / HITL ────────────────────────────────────────────────────────────

async def handle_barge_in(session: AssistantSession):
    logger.info("BARGE-IN — killing TTS")
    session.barge_in_event.set()
    await session.send_json({"action": "kill_audio"})
    await asyncio.sleep(0.1)
    session.barge_in_event.clear()


async def show_hitl_buttons(session: AssistantSession, message: str, buttons: Optional[list] = None) -> str:
    session.hitl_event.clear()
    session.hitl_choice = None

    if not buttons or not isinstance(buttons, list):
        if session.context_type == "bargain":
            buttons = ["Accept the price", "Try one more time", "Walk away"]
        elif session.context_type in ("food_order", "pharmacy"):
            buttons = ["Confirm, proceed", "Ask something else", "Cancel"]
        else:
            buttons = ["Yes, proceed", "Ask differently", "Cancel"]

    await session.send_json({
        "action":  "show_buttons",
        "message": message,
        "buttons": buttons,
    })

    try:
        await asyncio.wait_for(session.hitl_event.wait(), timeout=90.0)
    except asyncio.TimeoutError:
        session.hitl_choice = buttons[-1]

    return session.hitl_choice

# ── Main Turn Pipeline ─────────────────────────────────────────────────────────

async def run_turn(session: AssistantSession, user_input: str):
    if session.is_done:
        return

    if session.is_processing:
        logger.warning(f"run_turn blocked — already processing. Dropped: {user_input[:40]!r}")
        return
    session.is_processing = True

    try:
        if user_input:
            await session.send_json({
                "action": "transcription",
                "text": user_input,
                "speaker": "local"
            })

        await session.send_json({"action": "status", "text": "🤔 Thinking..."})
        llm_result     = await run_llm(session, f"The person said: {user_input}" if user_input else "")
        action         = llm_result.get("action", "SPEAK")
        korean_speech  = llm_result.get("korean_speech", "")
        english_update = llm_result.get("english_update", "")
        hitl_buttons   = llm_result.get("hitl_buttons")

        # ── Send emotion/tension update ────────────────────────
        mood        = llm_result.get("mood", "neutral")
        deal_chance = llm_result.get("deal_chance")
        next_move   = llm_result.get("next_move", "")
        if mood or deal_chance is not None or next_move:
            await session.send_json({
                "action":      "emotion_update",
                "mood":        mood,
                "deal_chance": deal_chance,
                "next_move":   next_move,
            })

        # ── Send live phrase cheatsheet ────────────────────────
        phrases = llm_result.get("phrases", [])
        if phrases:
            await session.send_json({
                "action":  "phrase_update",
                "phrases": phrases,
            })

        if hitl_buttons and not isinstance(hitl_buttons, list):
            hitl_buttons = None

        # Speak Korean
        if korean_speech and not session.barge_in_event.is_set():
            await session.send_json({"action": "status", "text": "🗣️ Speaking Korean..."})
            await session.send_json({"action": "ai_speech", "text": korean_speech})
            completed = await stream_tts(session, korean_speech, KOREAN_TTS_VOICE)
            if not completed:
                session.is_processing = False
                return

        if action == "CONSULT_USER":
            session.consult_depth += 1

            if session.consult_depth > 2:
                logger.warning("CONSULT_USER loop detected — forcing graceful close")
                session.consult_depth = 0
                session.is_processing = False
                await run_turn(session, "The student says to accept the current situation gracefully and wrap up the conversation politely.")
                return

            choice = await show_hitl_buttons(session, english_update, hitl_buttons)
            await stream_tts(session, f"You chose: {choice}. Continuing.", ENGLISH_TTS_VOICE)

            cancel_words = {"walk away", "cancel", "leave", "no thanks"}
            if choice.lower() in cancel_words:
                session.is_done = True
                await session.send_json({"action": "status", "text": "Ending session..."})
                await stream_tts(session, "네, 감사합니다. 안녕히 계세요.", KOREAN_TTS_VOICE)
                await session.send_json({"action": "session_ended", "result": "cancelled"})
                return

            session.consult_depth = 0
            session.is_processing = False
            await run_turn(session, f"Student's decision: {choice}")
            return

        session.consult_depth = 0

        if english_update and not session.barge_in_event.is_set():
            await session.send_json({"action": "english_update", "text": english_update})
            await stream_tts(session, english_update, ENGLISH_TTS_VOICE)

        await session.send_json({"action": "status", "text": "🎙️ Ready — tap mic to record their response"})

    finally:
        session.is_processing = False

# ── WebSocket Endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws/negotiate")
async def negotiate_ws(websocket: WebSocket):
    await websocket.accept()
    session: Optional[AssistantSession] = None

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                audio_chunk = message["bytes"]
                if session is None:
                    continue
                if session.is_speaking and len(audio_chunk) > 500:
                    await handle_barge_in(session)
                    session.audio_buffer.clear()
                    continue
                session.audio_buffer.extend(audio_chunk)

            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                action = data.get("action", "")

                # ── Start session ──────────────────────────────
                if action == "start_negotiation":
                    goal         = data.get("goal", "Help the student communicate.")
                    context_type = data.get("context_type", "general")
                    session      = AssistantSession(websocket, goal, context_type)

                    await session.send_json({"action": "status", "text": "🤔 Preparing your briefing..."})

                    # ── Pre-battle briefing ────────────────────
                    briefing = await generate_briefing(session)
                    await session.send_json({
                        "action":        "briefing",
                        "text":          briefing.get("briefing_text", ""),
                        "key_phrase_kr": briefing.get("key_phrase_kr", ""),
                        "key_phrase_rom":briefing.get("key_phrase_rom", ""),
                        "key_phrase_en": briefing.get("key_phrase_en", ""),
                    })
                    # Speak the briefing in English
                    if briefing.get("briefing_text"):
                        await stream_tts(session, briefing["briefing_text"], ENGLISH_TTS_VOICE)

                    await session.send_json({"action": "status", "text": "🤝 Connected — AI is ready to speak Korean for you."})

                    # ── Opening Korean greeting ────────────────
                    opening = await run_llm(session, "Start with a warm, natural Korean greeting suited to this context and mission.")
                    if opening.get("korean_speech"):
                        await session.send_json({"action": "ai_speech", "text": opening["korean_speech"]})
                        await stream_tts(session, opening["korean_speech"], KOREAN_TTS_VOICE)
                    if opening.get("english_update"):
                        await session.send_json({"action": "english_update", "text": opening["english_update"]})
                    if opening.get("phrases"):
                        await session.send_json({"action": "phrase_update", "phrases": opening["phrases"]})

                    await session.send_json({"action": "status", "text": "🎙️ Ready — tap mic to record their response"})

                # ── Audio finished ─────────────────────────────
                elif action == "audio_end":
                    is_whisper = data.get("is_whisper", False)
                    if session and len(session.audio_buffer) > 1000:
                        audio_data = bytes(session.audio_buffer)
                        session.audio_buffer.clear()

                        await session.send_json({"action": "status", "text": "👂 Transcribing..."})
                        text = await transcribe_audio(session, audio_data)

                        if text and is_valid_transcription(text):
                            if is_whisper:
                                logger.info(f"Whisper received: {text}")
                                session.memory.append({
                                    "role": "system",
                                    "content": f"[STUDENT SECRET INSTRUCTION — incorporate naturally into your next Korean response: {text}]"
                                })
                                await session.send_json({
                                    "action": "english_update",
                                    "text": f"📝 Whisper noted: \"{text}\" — will use it when local speaks next."
                                })
                                await session.send_json({
                                    "action": "status",
                                    "text": "🤫 Whisper saved — tap main mic to record local's response"
                                })
                            else:
                                asyncio.create_task(run_turn(session, text))
                        else:
                            await session.send_json({
                                "action": "status",
                                "text": "❓ Couldn't hear clearly — tap mic and try again"
                            })
                    else:
                        if session:
                            session.audio_buffer.clear()

                # ── SOS Bailout ────────────────────────────────
                elif action == "sos_bailout":
                    if session:
                        await handle_barge_in(session)
                        await session.send_json({"action": "status", "text": "🚨 Emergency exit..."})
                        bail_speech = "아, 죄송합니다! 교수님한테 급한 전화가 왔어요. 다음에 또 올게요. 감사합니다!"
                        await session.send_json({"action": "ai_speech", "text": bail_speech})
                        await stream_tts(session, bail_speech, KOREAN_TTS_VOICE)
                        session.is_done = True
                        await session.send_json({"action": "session_ended", "result": "sos_bailout", "vocab": None})

                # ── User ends session ──────────────────────────
                elif action == "user_end_session":
                    if session:
                        await handle_barge_in(session)
                        await session.send_json({"action": "status", "text": "📝 Analysing your session..."})

                        # Extract vocab
                        session.memory.append({"role": "system", "content": VOCAB_PROMPT})
                        vocab = None
                        for model in [GROQ_LIGHT_MODEL] + GROQ_MODELS:
                            try:
                                resp = await session.groq_client.chat.completions.create(
                                    model=model,
                                    messages=session.memory[-20:],
                                    max_tokens=300,
                                    temperature=0.2,
                                    response_format={"type": "json_object"},
                                )
                                vocab_data = json.loads(resp.choices[0].message.content)
                                vocab = vocab_data.get("vocab")
                                break
                            except Exception as e:
                                if "429" in str(e):
                                    continue
                                logger.error(f"Vocab extraction failed on {model}: {e}")
                                break

                        # Post-deal analysis
                        analysis = await generate_post_deal_analysis(session)

                        session.is_done = True
                        await session.send_json({
                            "action":   "session_ended",
                            "result":   "user_ended",
                            "vocab":    vocab,
                            "analysis": analysis,
                        })

                # ── Barge-in ───────────────────────────────────
                elif action == "barge_in":
                    if session and session.is_speaking:
                        await handle_barge_in(session)

                # ── HITL decision ──────────────────────────────
                elif action == "user_decision":
                    if session:
                        session.hitl_choice = data.get("choice", "Cancel")
                        session.hitl_event.set()

                # ── Reset ──────────────────────────────────────
                elif action == "reset":
                    if session:
                        session.barge_in_event.set()
                        session.is_done = True
                    session = None
                    await websocket.send_text(json.dumps({"action": "reset_ok"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error: {e}")
        try:
            await websocket.send_text(json.dumps({"action": "error", "message": str(e)}))
        except:
            pass


# ── STT ────────────────────────────────────────────────────────────────────────

async def transcribe_audio(session: AssistantSession, audio_bytes: bytes) -> str:
    if not audio_bytes or len(audio_bytes) < 1000:
        return ""
        
    # Attempt 1: Groq Whisper (if client exists)
    if session.groq_client:
        try:
            file_obj = io.BytesIO(audio_bytes)
            transcript = await session.groq_client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=("voice.ogg", file_obj, "audio/ogg"),
                prompt="Korean conversation or English. 안녕하세요. 감사합니다. Hello.",
            )
            return transcript.text.strip()
        except Exception as e:
            logger.warning(f"Whisper STT failed/unavailable: {e}. Falling back to Free Google STT.")
            
    # Attempt 2: Totally Free Google Web Speech API (No API Key)
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        import tempfile
        import os
        
        # Convert OGG/WebM to WAV using pydub
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f_in:
            f_in.write(audio_bytes)
            tmp_ogg = f_in.name
            
        tmp_wav = tmp_ogg + ".wav"
        audio = AudioSegment.from_file(tmp_ogg)
        audio.export(tmp_wav, format="wav")
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_wav) as source:
            audio_data = recognizer.record(source)
            
        # Try Korean first, fallback to English
        try:
            text = recognizer.recognize_google(audio_data, language="ko-KR")
        except sr.UnknownValueError:
            text = recognizer.recognize_google(audio_data, language="en-US")
            
        os.unlink(tmp_ogg)
        os.unlink(tmp_wav)
        return text.strip()
    except ImportError:
        logger.error("SpeechRecognition or pydub not installed. Cannot use free fallback.")
        return ""
    except Exception as e:
        logger.error(f"Free Google STT failed: {e}")
        return ""


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
