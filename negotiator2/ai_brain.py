# ai_brain.py — K-Transition OS v3.0
# AI providers: Groq (primary, fast, free) → Gemini (fallback, free, handles images).
# Also handles voice note transcription via Groq Whisper.

import requests
import json
import base64
import io
import os
import logging
import asyncio
from config import get_groq_key, GEMINI_API_KEY, GROQ_MODELS, GROQ_LIGHT_MODEL, GEMINI_MODEL, WHISPER_MODEL

logger = logging.getLogger(__name__)

# ── Korea Expert System Prompt ─────────────────────────────────────────────────
# This is the "secret sauce" — makes AI act like someone who actually lived in Korea.

KOREA_SYSTEM_PROMPT = """You are 한국 선배 (Korean Senior) — a specialised AI companion built ONLY for
international students arriving in South Korea. You are NOT a general AI. You only talk about Korea.

Personality: warm, honest, like a senior student who already went through everything you're going through.
Give SPECIFIC practical info — not vague generic advice that anyone could Google.

━━ FIRST WEEK ━━
SIM: Airport booths (SK Telecom/KT/LG U+) or any CU/GS25/7-Eleven. Passport only. ~30-50k/month.
T-Money: 4,000 won at CU/GS25/7-Eleven. Charge at subway machines. 1,250–1,550 won/ride.
ARC (외국인등록증): Mandatory if staying 90+ days. Book at HiKorea.go.kr. Bring passport +
  enrollment cert + 2 photos + 30,000 won. Takes 2-4 weeks. ARC needed for: bank, phone, rent, NHIS.

━━ HOUSING ━━
전세=large deposit, no rent (HIGH RISK). 월세=deposit+monthly rent (SAFER). 고시원=3-7sqm, 300-500k/mo.
SCAM PREVENTION: Check 등기부등본 at iros.go.kr (700 won). NEVER pay before signed contract.
After signing: 주민센터 within 14 days for 전입신고(free) + 확정일자(600 won) = deposit protection.

━━ FOOD ━━
Pork is everywhere: 설렁탕/감자탕/뼈해장국 = pork BONE broth (entire broth, not just meat).
된장/김치찌개 = anchovy stock (not vegetarian). Mirin/청주 = alcohol in marinades.
Ask: 이 음식에 돼지고기 있어요? / 할랄 음식 있어요? / 채식 메뉴 있나요?
Labels: 유통기한=best-before, 소비기한=use-by (hard limit), 제조일=manufacture date (YYYY.MM.DD).

━━ BANKING ━━
Kakao Bank: easiest, fully mobile, needs Korean number + passport. No branch visit.
Shinhan: best English staff. KB Kookmin: most ATMs. Open with ARC+passport or passport+enrollment cert.
International transfer: Wise app > bank wire.

━━ HEALTHCARE ━━
NHIS auto-enrolls after 6 months, ~30-40k/month. With NHIS: 20-30% of hospital cost.
University clinic = cheapest. Pharmacy (약국) = no prescription for OTC. 응급실 = ER.

━━ VISA & WORK ━━
D-2: 25 hrs/week during semester, unlimited vacation. D-4: need 시간제취업허가 from HiKorea.
Min wage 2025: ~9,860 won/hour. Extension: apply 1 month before expiry.

━━ DAILY LIFE ━━
Garbage: 종량제 봉투 (official bags at convenience stores, 1-20L). Fine=100,000 won.
Noise quiet hours: 10PM-7AM. 층간소음 = floor noise — Koreans take it very seriously.
Convenience stores (CU/GS25/7-Eleven): pay bills, charge T-Money, ATM, print, eat 24/7.

━━ EMERGENCIES ━━
112=Police (say "English please"), 119=Fire+Ambulance, 1345=Foreigner helpline (24/7 multilingual),
1393=Crisis/suicide line, 182=Cybercrime.

━━ HOW TO RESPOND ━━
1. Be SPECIFIC: "Kakao Bank" not "some bank". "1,250 won" not "a small amount".
2. Use Korean naturally: 주민센터 [community center], with romanisation if helpful.
3. Flag risks with 🔴 DANGER: or ⚠️ CAUTION:
4. Keep responses SHORT for simple questions, detailed for complex ones.
5. NEVER discuss topics outside Korea student life.
6. For food: always check hidden pork/alcohol/fish stock.
7. For housing: always mention 등기부등본 and 전입신고.
8. If crisis (suicide/self-harm): IMMEDIATELY give 1393 and 1345.
"""


# ── Groq API with Tool Calling ────────────────────────────────────────────────

def search_korea_web(query: str) -> str:
    """Search DuckDuckGo with strict Korea localization and return full context snippets."""
    try:
        from duckduckgo_search import DDGS
        # Force localization to Korea
        localized_query = f"{query} in South Korea OR 대한민국"
        logger.info(f"Searching web: {localized_query}")
        
        results = DDGS().text(localized_query, region='kr-kr', safesearch='off', max_results=10)
        if not results:
            return "No search results found. Recommend checking with official sources like 1345 hotline."
            
        snippets = []
        for r in results:
            snippets.append(f"Source: {r.get('title', 'Unknown')}\nInfo: {r.get('body', '')}\nURL: {r.get('href', '')}\n")
            
        full_text = "\n".join(snippets)
        return full_text[:4000] # Limit context size
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Search failed: {e}. Recommend checking with official sources."


def call_groq(messages: list, system_prompt: str = None) -> str | None:
    api_key = get_groq_key()
    if not api_key:
        return None
        
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)
    
    tools = [{
        "type": "function",
        "function": {
            "name": "search_korea_web",
            "description": "Search the internet for real-time information, laws, fees, or news about South Korea. USE THIS FOR ANY DATA YOU ARE NOT 100% SURE ABOUT.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g. 'ARC renewal fee 2025')"
                    }
                },
                "required": ["query"]
            }
        }
    }]
    
    for model in GROQ_MODELS:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": api_messages, "tools": tools, "tool_choice": "auto", "max_tokens": 1500, "temperature": 0.5},
                timeout=30,
            )
            r.raise_for_status()
            response_msg = r.json()["choices"][0]["message"]
            
            # Tool call loop
            if response_msg.get("tool_calls"):
                api_messages.append(response_msg)
                for tool_call in response_msg["tool_calls"]:
                    if tool_call["function"]["name"] == "search_korea_web":
                        args = json.loads(tool_call["function"]["arguments"])
                        search_result = search_korea_web(args["query"])
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": "search_korea_web",
                            "content": search_result
                        })
                
                # Second call with search results
                r2 = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": api_messages, "max_tokens": 1500, "temperature": 0.7},
                    timeout=30,
                )
                r2.raise_for_status()
                return r2.json()["choices"][0]["message"]["content"]
                
            return response_msg.get("content")
            
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Groq rate limit on {model} — trying next model...")
                continue # Try the next model in the list
            else:
                logger.error("Groq HTTP error: %s", e)
                break # Non rate limit error, don't retry models
        except Exception as e:
            logger.error("Groq error: %s", e)
            break
            
    logger.warning("All Groq models exhausted or failed — switching to Gemini fallback")
    return None


# ── Gemini API ────────────────────────────────────────────────────────────────

def _resize_image(image_bytes: bytes, max_px: int = 800) -> bytes:
    """Fix BUG 6: resize image before sending to Gemini to avoid quota burn."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        if max(img.size) > max_px:
            img.thumbnail((max_px, max_px))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception:
        return image_bytes     # PIL not installed — send as-is


def call_gemini(messages: list, system_prompt: str = None, image_bytes: bytes = None) -> str | None:
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

    # ── FIX: Build full multi-turn history for Gemini so it remembers the conversation ──
    # Gemini API uses "user"/"model" roles (not "assistant")
    # We include up to the last 10 messages to keep token usage reasonable
    gemini_contents = []

    # System prompt injected as first user turn + model ack (Gemini doesn't have a system role)
    if system_prompt:
        gemini_contents.append({"role": "user",  "parts": [{"text": f"[System instructions]\n{system_prompt}"}]})
        gemini_contents.append({"role": "model", "parts": [{"text": "Understood. I'll follow these instructions."}]})

    # Add conversation history (last 10 messages max to save tokens)
    for m in messages[-10:]:
        role    = m.get("role", "user")
        content = m.get("content", "")
        if not content:
            continue
        # Gemini uses "model" instead of "assistant"
        gemini_role = "model" if role == "assistant" else "user"
        gemini_contents.append({"role": gemini_role, "parts": [{"text": content}]})

    # If image, attach to the last user turn
    if image_bytes and gemini_contents:
        resized = _resize_image(image_bytes)
        last_turn = gemini_contents[-1]
        if last_turn["role"] == "user":
            last_turn["parts"].insert(0, {
                "inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(resized).decode()}
            })
        else:
            # No trailing user turn → add one with image only
            gemini_contents.append({
                "role": "user",
                "parts": [{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(resized).decode()}}]
            })

    # Gemini requires conversation to end on a user turn
    if not gemini_contents or gemini_contents[-1]["role"] != "user":
        logger.warning("Gemini: last turn is not 'user' — appending placeholder")
        gemini_contents.append({"role": "user", "parts": [{"text": "Please continue."}]})

    payload = {
        "contents": gemini_contents,
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 800},  # Lower temp = less hallucination
    }
    try:
        r = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload, timeout=30)
        r.raise_for_status()
        cands = r.json().get("candidates", [])
        if cands:
            return cands[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Gemini rate limit hit")
        else:
            logger.error("Gemini HTTP error: %s", e)
    except Exception as e:
        logger.error("Gemini error: %s", e)
    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def ask_ai(user_message: str, conversation_history: list = None,
           extra_context: str = "", image_bytes: bytes = None) -> tuple[str | None, str | None]:
    """Groq first, Gemini fallback. Returns (response, provider)."""
    if conversation_history is None:
        conversation_history = []
    messages = list(conversation_history)
    full_msg = user_message if not extra_context else f"{user_message}\n\n[System note: {extra_context}]"
    messages.append({"role": "user", "content": full_msg})

    if not image_bytes:
        resp = call_groq(messages, KOREA_SYSTEM_PROMPT)
        if resp:
            return resp, "groq"

    resp = call_gemini(messages, KOREA_SYSTEM_PROMPT, image_bytes)
    if resp:
        return resp, "gemini"

    logger.error("Both AI providers failed")
    return None, None


async def ask_ai_async(user_message: str, conversation_history: list = None,
                       extra_context: str = "", image_bytes: bytes = None):
    return await asyncio.to_thread(ask_ai, user_message, conversation_history, extra_context, image_bytes)


# ── Image analysis ────────────────────────────────────────────────────────────

def analyze_image(image_bytes: bytes, user_question: str = "") -> str | None:
    prompt = (
        f'The user sent this image and asked: "{user_question}"\n\n'
        if user_question else ""
    )
    prompt += (
        "Analyse this image for an international student in South Korea. Cover:\n"
        "1. What is this? (food label, contract, sign, menu...)\n"
        "2. Any risks? (pork, alcohol, allergens, scam signs)\n"
        "3. Korean text: translate the important parts\n"
        "4. Practical tip based on what you see\n"
        "Be specific. Use Korea expert knowledge."
    )
    return call_gemini([{"role": "user", "content": prompt}], KOREA_SYSTEM_PROMPT, image_bytes)


async def analyze_image_async(image_bytes: bytes, user_question: str = "") -> str | None:
    return await asyncio.to_thread(analyze_image, image_bytes, user_question)


# ── Voice note transcription (Groq Whisper) ───────────────────────────────────

# ── Voice transcription queue ────────────────────────────────────────────────
# Whisper rate limits are separate from (and lower than) text inference limits.
# Without a queue, concurrent voice notes cause 429 errors with no fallback.
# This semaphore limits concurrent Whisper calls to 3, queuing the rest.
_whisper_semaphore = asyncio.Semaphore(3)
_whisper_last_call: float = 0.0
_WHISPER_MIN_INTERVAL = 2.0  # seconds between calls to avoid burst rate limits


def transcribe_audio(audio_bytes: bytes, lang_hint: str = "ko") -> str | None:
    """
    Transcribe audio via Groq Whisper → HuggingFace Whisper fallback.
    FIX: HuggingFace free Inference API as secondary (no internet issues unlike local).
    """
    api_key = get_groq_key()
    if not api_key:
        return None
    if not audio_bytes or len(audio_bytes) < 500:
        return None
    import tempfile, os, time as _time
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        def _call_whisper(retry: bool = False) -> str | None:
            with open(tmp_path, "rb") as f:
                r = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": ("voice.ogg", f, "audio/ogg")},
                    data={"model": WHISPER_MODEL, "language": lang_hint,
                          "prompt": "Korean and English conversation. 안녕하세요."},
                    timeout=30,
                )
            if r.status_code == 429 and not retry:
                logger.warning("Whisper 429 — backing off 10s then retrying once")
                _time.sleep(10)
                return _call_whisper(retry=True)
            r.raise_for_status()
            return r.json().get("text", "").strip()

        result = _call_whisper()
        os.unlink(tmp_path)
        return result

    except requests.HTTPError as e:
        logger.error("Groq Whisper failed after retry: %s — trying HuggingFace fallback", e)
        # ── FIX: HuggingFace free Inference API as fallback ──────────────────
        # Free tier, no billing needed, works from any server including Render/HF Spaces
        return _transcribe_via_hf(audio_bytes)
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        return _transcribe_via_hf(audio_bytes)


def _transcribe_via_hf(audio_bytes: bytes) -> str | None:
    """
    HuggingFace Inference API (free tier) — Whisper-large-v3.
    Set HF_API_TOKEN in .env for higher rate limits (still free).
    No local compute needed — works fine on Render and HF Spaces.
    """
    hf_token = os.environ.get("HF_API_TOKEN", "")  # Optional: add to .env for higher limits
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/openai/whisper-large-v3",
            headers={**headers, "Content-Type": "audio/ogg"},
            data=audio_bytes,
            timeout=40,
        )
        if r.status_code == 503:
            logger.warning("HF Whisper model loading (cold start) — retry in 10s. User may see a brief delay.")
            import time as _t; _t.sleep(10)
            r = requests.post(
                "https://api-inference.huggingface.co/models/openai/whisper-large-v3",
                headers={**headers, "Content-Type": "audio/ogg"},
                data=audio_bytes,
                timeout=40,
            )
        r.raise_for_status()
        result = r.json()
        if isinstance(result, dict):
            return result.get("text", "").strip()
        return ""
    except Exception as e:
        logger.error("HuggingFace Whisper fallback failed: %s", e)
        return None


async def transcribe_audio_async(audio_bytes: bytes) -> str | None:
    async with _whisper_semaphore:
        return await asyncio.to_thread(transcribe_audio, audio_bytes)


# ── Dynamic quiz generation ───────────────────────────────────────────────────

LEVEL_LABELS = {1: "beginner", 2: "elementary", 3: "intermediate", 4: "upper-intermediate", 5: "advanced"}

def generate_quiz_question(level: int = 1, category: str = "daily life") -> dict | None:
    """Ask Groq to generate a fresh quiz question. Returns structured dict or None."""
    api_key = get_groq_key()
    if not api_key:
        return None

    level_name = LEVEL_LABELS.get(level, "beginner")
    prompt = f"""Generate ONE Korean vocabulary quiz question for a {level_name} student.
Category hint: {category}

Respond ONLY with this JSON (no markdown, no extra text):
{{
  "korean": "Korean word or phrase",
  "romanized": "pronunciation in English letters",
  "correct_meaning": "correct English meaning",
  "wrong_answers": ["wrong1", "wrong2", "wrong3"],
  "example_sentence": "short Korean example sentence",
  "example_translation": "English translation of example",
  "tip": "one practical tip about when/how to use this word in Korea"
}}

Rules:
- Level {level}: {"basic survival words (hello, thank you, how much)" if level==1 else "daily life vocabulary" if level==2 else "situational phrases" if level==3 else "nuanced expressions" if level==4 else "advanced idioms and grammar"}
- wrong_answers must be plausible but clearly different meanings
- example_sentence should reflect a real situation in Korea"""

    try:
        messages = [{"role": "user", "content": prompt}]
        raw = None
        for model in GROQ_MODELS:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "max_tokens": 500, "temperature": 0.3},
                    timeout=20,
                )
                r.raise_for_status()
                raw = r.json()["choices"][0]["message"]["content"]
                break
            except requests.HTTPError as e:
                if e.response.status_code == 429:
                    continue
                break
                
        if not raw:
            return None
        clean = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        # Validate required fields
        required = ["korean", "romanized", "correct_meaning", "wrong_answers", "example_sentence"]
        if not all(k in data for k in required):
            return None
        if len(data.get("wrong_answers", [])) < 3:
            return None
        return data
    except Exception as e:
        logger.warning("Quiz generation failed: %s", e)
        return None


async def generate_quiz_question_async(level: int = 1, category: str = "daily life") -> dict | None:
    return await asyncio.to_thread(generate_quiz_question, level, category)
