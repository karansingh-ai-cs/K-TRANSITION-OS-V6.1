# ai_brain.py — K-Transition OS v3.0
# AI providers: Groq (primary, fast, free) → Gemini (fallback, free, handles images).
# Also handles voice note transcription via Groq Whisper.

import requests
import json
import base64
import io
import logging
import asyncio
from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL, WHISPER_MODEL

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


# ── Groq API ──────────────────────────────────────────────────────────────────

def call_groq(messages: list, system_prompt: str = None) -> str | None:
    if not GROQ_API_KEY:
        return None
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": api_messages, "max_tokens": 1000, "temperature": 0.7},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Groq rate limit — switching to Gemini")
        else:
            logger.error("Groq HTTP error: %s", e)
    except Exception as e:
        logger.error("Groq error: %s", e)
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

    prefix = (system_prompt + "\n\n---\n\n") if system_prompt else ""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    parts = [{"text": prefix + last_user}]
    if image_bytes:
        resized = _resize_image(image_bytes)
        parts = [
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(resized).decode()}},
            {"text": prefix + last_user},
        ]

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
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
    Transcribe Telegram voice note bytes using Groq Whisper.
    FIX: exponential backoff on 429. Retry once after 10s before giving up.
    Whisper rate limits hit before text inference limits at scale.
    """
    if not GROQ_API_KEY:
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
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
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
        logger.error("Whisper HTTP error after retry: %s", e)
        return None
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        return None


async def transcribe_audio_async(audio_bytes: bytes) -> str | None:
    async with _whisper_semaphore:
        return await asyncio.to_thread(transcribe_audio, audio_bytes)


# ── Dynamic quiz generation ───────────────────────────────────────────────────

LEVEL_LABELS = {1: "beginner", 2: "elementary", 3: "intermediate", 4: "upper-intermediate", 5: "advanced"}

def generate_quiz_question(level: int = 1, category: str = "daily life") -> dict | None:
    """Ask Groq to generate a fresh quiz question. Returns structured dict or None."""
    if not GROQ_API_KEY:
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
        raw = call_groq(messages)   # no system prompt — we want pure JSON
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
