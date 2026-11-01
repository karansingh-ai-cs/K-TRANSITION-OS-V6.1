# ai_brain.py — K-Transition OS v6.0
# Smart Multi-Model Router
# Task → Best Model → Fallback Chain → Error
#
# Routing logic:
#   BUDDY/CASUAL  → Gemma 4 27B (Gemini) [Unlimited TPM, 1500 RPD]
#   COMPLEX/LEGAL → GPT-OSS-120B (Groq)  [30 RPM, 1K RPD]
#   QUIZ          → GPT-OSS-20B (Groq)   [30 RPM, 1K RPD]
#   IMAGE         → Gemini 2.5 Flash    [5 RPM, 20 RPD — vision only]
#   VOICE         → Whisper Turbo       [20 RPM, 2K RPD]
#   NEWS/SUMMARY  → GPT-OSS-20B (Groq)   [1K RPD]

import requests
import json
import base64
import io
import logging
import asyncio
from config import (
    get_groq_key, get_gemini_key, get_sambanova_key, lock_groq_key, lock_gemini_key,
    # Gemini text models (all tiers)
    GEMINI_BUDDY_MODEL, GEMINI_BUDDY_BACKUP, GEMINI_FLASH_LITE,
    GEMINI_VISION_MODEL, GEMINI_MODEL, GEMINI_35_FLASH, GEMINI_3_FLASH,
    # Gemini special-purpose
    GEMINI_TTS_MODEL, GEMINI_TTS_BACKUP,
    GEMINI_LIVE_MODEL, GEMINI_LIVE_BACKUP,
    GEMINI_EMBED_MODEL, GEMINI_EMBED_BACKUP,
    IMAGEN_MODEL, IMAGEN_HQ_MODEL,
    # Groq text models
    GROQ_LIGHT_MODEL, GROQ_FAST_MODEL, GROQ_HEAVY_MODEL,
    GROQ_ARABIC_MODEL, GROQ_SCOUT_MODEL,
    GROQ_GPT120B, GROQ_GPT20B, GROQ_COMPOUND_MODEL, GROQ_COMPOUND_MINI,
    GROQ_GUARD_MODEL, GROQ_MODELS, WHISPER_MODEL,
    # Sambanova models
    SAMBANOVA_COMPLEX_MODEL, SAMBANOVA_BUDDY_MODEL,
)



logger = logging.getLogger(__name__)

# ── Korea Expert System Prompt ─────────────────────────────────────────────────
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
Labels: 유통기한=best-before, 소비기한=use-by (hard limit), 제조일=manufacture date.

━━ BANKING ━━
Kakao Bank: easiest, fully mobile, needs Korean number + passport. No branch visit.
Shinhan: best English staff. KB Kookmin: most ATMs. Open with ARC+passport.
International transfer: Wise app > bank wire.

━━ HEALTHCARE ━━
NHIS auto-enrolls after 6 months, ~30-40k/month. With NHIS: 20-30% of hospital cost.
University clinic = cheapest. Pharmacy (약국) = no prescription for OTC. 응급실 = ER.

━━ VISA & WORK ━━
D-2: 25 hrs/week during semester, unlimited vacation. D-4: need 시간제취업허가 from HiKorea.
Min wage 2025: ~9,860 won/hour. Extension: apply 1 month before expiry.

━━ DAILY LIFE ━━
Garbage: 종량제 봉투 (official bags at convenience stores, 1-20L). Fine=100,000 won.
Noise quiet hours: 10PM-7AM. Convenience stores (CU/GS25/7-Eleven): pay bills, ATM, print, eat 24/7.

━━ EMERGENCIES ━━
112=Police, 119=Fire+Ambulance, 1345=Foreigner helpline (24/7 multilingual),
1393=Crisis/suicide line, 182=Cybercrime.

━━ HOW TO RESPOND ━━
1. Be SPECIFIC: "Kakao Bank" not "some bank". "1,250 won" not "a small amount".
2. Use Korean naturally: 주민센터 [community center], with romanisation.
3. Flag risks with 🔴 DANGER: or ⚠️ CAUTION:
4. Keep responses SHORT for simple questions, detailed for complex ones.
5. NEVER discuss topics outside Korea student life.
6. ANTI-HALLUCINATION (CRITICAL): If the user asks about their personal info (Visa, University, Major, Arrival Date, etc.) and you do not know it, DO NOT GUESS. Explicitly ask them to provide it (e.g., "I don't know your visa type yet! What visa are you on?").
7. If crisis (suicide/self-harm): IMMEDIATELY give 1393 and 1345.
"""

# ── Task Type Constants ────────────────────────────────────────────────────────
TASK_BUDDY   = "buddy"    # casual chat, emotional support
TASK_COMPLEX = "complex"  # visa, legal, ARC, contracts
TASK_QUIZ    = "quiz"     # Korean quiz generation
TASK_IMAGE   = "image"    # food label, sign, contract scan
TASK_SUMMARY = "summary"  # news/web summarization
TASK_VOICE   = "voice"    # audio transcription (handled separately)

# Complex topic keywords — route to heavy model
COMPLEX_KEYWORDS = [
    "visa", "arc", "immigration", "contract", "legal", "extension",
    "hikorea", "overstay", "lawsuit", "scam", "deposit", "등기부등본",
    "전입신고", "확정일자", "외국인등록증", "체류기간", "출입국"
]


def _detect_task(user_message: str) -> str:
    """Detect what kind of task this message requires."""
    msg = user_message.lower()
    if any(kw in msg for kw in COMPLEX_KEYWORDS):
        return TASK_COMPLEX
    return TASK_BUDDY

# ── Safety Filter (LLaMA Prompt Guard) ───────────────────────────────────────
# Uses llama-prompt-guard-2-86m: 30 RPM, 14,400 RPD — checks ALL messages
# Returns True if message is SAFE, False if it looks like a jailbreak/harmful

def check_message_safety(user_message: str) -> bool:
    """Quick safety check using LLaMA Prompt Guard (tiny, fast model).
    Returns True = safe to process. False = potential jailbreak/abuse.
    On any error, defaults to True (fail-open to avoid blocking legit users).
    """
    api_key = get_groq_key()
    if not api_key:
        return True  # No key = skip check
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_GUARD_MODEL,
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": 10,
                "temperature": 0,
            },
            timeout=5,
        )
        if r.status_code == 200:
            label = r.json()["choices"][0]["message"].get("content", "").lower()
            # Prompt Guard returns "safe" or "unsafe"
            if "unsafe" in label or "jailbreak" in label or "injection" in label:
                logger.warning("Safety filter blocked message: %s...", user_message[:50])
                return False
    except Exception as e:
        logger.debug("Safety check skipped: %s", e)
    return True


def search_korea_web(query: str) -> str:
    """Search the web for Korea-related info using DuckDuckGo SDK."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(f"site:kr {query}", max_results=3))
        if not results:
            return "No recent search results found."
        snippets = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            snippets.append(f"{title}: {body}")
        return "\n".join(snippets)[:3500]
    except ImportError:
        logger.warning("duckduckgo-search not installed — search disabled")
        return "Web search unavailable (duckduckgo-search not installed)."
    except Exception as e:
        logger.error("Search failed: %s", e)
        return f"Search failed: {e}"


# ── Gemini API (unified caller) ────────────────────────────────────────────────
def _call_gemini_model(model: str, messages: list, system_prompt: str = None,
                       image_bytes: bytes = None) -> str | None:
    """Call any Gemini model by name. Returns text or None."""
    gemini_key = get_gemini_key()
    if not gemini_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    # Context history pruning (max 8 messages) to save tokens but retain memory!
    pruned_messages = messages[-8:] if len(messages) > 8 else messages
    # Gemini requires contents to start with 'user' turn
    while pruned_messages and pruned_messages[0].get("role") == "assistant":
        pruned_messages = pruned_messages[1:]

    contents = []
    for m in pruned_messages:
        # Gemini uses "model" instead of "assistant"
        role = "model" if m.get("role") == "assistant" else "user"
        contents.append({
            "role": role,
            "parts": [{"text": str(m.get("content", ""))}]
        })

    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Hello"}]})

    if image_bytes:
        resized = _resize_image(image_bytes)
        img_part = {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(resized).decode()}}
        if contents[-1]["role"] == "user":
            contents[-1]["parts"].insert(0, img_part)
        else:
            contents.append({"role": "user", "parts": [img_part, {"text": "Analyze this image."}]})

    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
    }

    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    try:
        headers = {
            "Content-Type": "application/json"
        }
        r = requests.post(url, params={"key": gemini_key}, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        cands = r.json().get("candidates", [])
        if cands:
            cand = cands[0]
            content = cand.get("content") or {}
            parts = content.get("parts") or [{}]
            if parts and isinstance(parts, list):
                return parts[0].get("text", "")
    except requests.HTTPError as e:
        code = e.response.status_code
        if code == 429:
            logger.warning("Gemini 429 on model %s", model)
            # 429 indicates rate limit exceeded; we simply return None to let caller handle fallback
        else:
            logger.error("Gemini HTTP error on %s: %s", model, e)
    except Exception as e:
        logger.error("Gemini error on %s: %s", model, e)
    return None



def _resize_image(image_bytes: bytes, max_px: int = 800) -> bytes:
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        if max(img.size) > max_px:
            img.thumbnail((max_px, max_px))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception:
        return image_bytes


# ── Sambanova API (unified caller) ─────────────────────────────────────────────
def _call_sambanova_model(model: str, messages: list, system_prompt: str = None,
                          max_tokens: int = 600, temperature: float = 0.7) -> str | None:
    """Call any Sambanova model by name. Returns text or None."""
    api_key = get_sambanova_key()
    if not api_key:
        return None

    # Context history pruning
    pruned_messages = messages[-4:] if len(messages) > 4 else messages

    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(pruned_messages)

    body = {"model": model, "messages": api_messages,
            "max_tokens": max_tokens, "temperature": temperature}

    try:
        r = requests.post(
            "https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body, timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"].get("content")
    except Exception as e:
        logger.error("Sambanova error on %s: %s", model, e)
    return None

# ── Groq API (unified caller) ──────────────────────────────────────────────────
def _call_groq_model(model: str, messages: list, system_prompt: str = None,
                     max_tokens: int = 600, temperature: float = 0.7,
                     tools: list = None) -> str | None:
    """Call any Groq model by name. Returns text or None."""
    api_key = get_groq_key()
    if not api_key:
        return None

    # Context history pruning (max 4 messages) to save tokens!
    pruned_messages = messages[-4:] if len(messages) > 4 else messages

    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(pruned_messages)

    body = {"model": model, "messages": api_messages,
            "max_tokens": max_tokens, "temperature": temperature}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body, timeout=30,
        )
        r.raise_for_status()
        resp_msg = r.json()["choices"][0]["message"]

        # Handle tool calls (web search)
        if tools and resp_msg.get("tool_calls"):
            api_messages.append(resp_msg)
            for tc in resp_msg["tool_calls"]:
                if tc["function"]["name"] == "search_korea_web":
                    args = json.loads(tc["function"]["arguments"])
                    result = search_korea_web(args["query"])
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": "search_korea_web",
                        "content": result
                    })
            # Second call with search results
            body2 = {"model": model, "messages": api_messages,
                     "max_tokens": max_tokens, "temperature": temperature}
            r2 = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body2, timeout=30,
            )
            r2.raise_for_status()
            return r2.json()["choices"][0]["message"].get("content")

        return resp_msg.get("content")

    except requests.HTTPError as e:
        code = e.response.status_code
        if code == 429:
            retry_after = e.response.headers.get("retry-after", "N/A")
            remaining_req = e.response.headers.get("x-ratelimit-remaining-requests", "N/A")
            remaining_tok = e.response.headers.get("x-ratelimit-remaining-tokens", "N/A")
            logger.warning(
                "Groq 429 rate limit hit on model %s | retry-after=%ss, remaining_req=%s, remaining_tok=%s",
                model, retry_after, remaining_req, remaining_tok
            )
            lock_groq_key(api_key)
        else:
            logger.error("Groq HTTP error on %s: %s | %s", model, e, e.response.text[:200])
    except Exception as e:
        logger.error("Groq error on %s: %s", model, e)
    return None



# ── SMART TASK ROUTER ──────────────────────────────────────────────────────────
# The heart of the system. Routes each task to its optimal model.

SEARCH_TOOL = [{
    "type": "function",
    "function": {
        "name": "search_korea_web",
        "description": "Search the web for real-time info about South Korea. Use for any data you are not 100% sure about.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"]
        }
    }
}]


def _route_buddy(messages: list) -> tuple[str | None, str | None]:
    """BUDDY route: Sambanova LLaMA 3.3 → Gemma 4 27B → Gemma 4 31B → Flash Lite → 3.5 Flash → 3 Flash → Groq Fallback."""
    # Primary: Sambanova
    resp = _call_sambanova_model(SAMBANOVA_BUDDY_MODEL, messages, KOREA_SYSTEM_PROMPT)
    if resp:
        return resp, f"sambanova/{SAMBANOVA_BUDDY_MODEL}"

    # Tier A: Unlimited TPM models first
    resp = _call_gemini_model(GEMINI_BUDDY_MODEL, messages, KOREA_SYSTEM_PROMPT)
    if resp:
        return resp, f"gemini/{GEMINI_BUDDY_MODEL}"

    resp = _call_gemini_model(GEMINI_BUDDY_BACKUP, messages, KOREA_SYSTEM_PROMPT)
    if resp:
        return resp, f"gemini/{GEMINI_BUDDY_BACKUP}"

    # Tier B: 500 RPD
    resp = _call_gemini_model(GEMINI_FLASH_LITE, messages, KOREA_SYSTEM_PROMPT)
    if resp:
        return resp, f"gemini/{GEMINI_FLASH_LITE}"

    # Tier C/D: Extra fallbacks (20 RPD each — last resort)
    for model in [GEMINI_35_FLASH, GEMINI_3_FLASH, GEMINI_MODEL]:
        resp = _call_gemini_model(model, messages, KOREA_SYSTEM_PROMPT)
        if resp:
            return resp, f"gemini/{model}"

    # Cross-provider fallback: try Groq active models if Gemini is unavailable
    for model in [GROQ_LIGHT_MODEL, GROQ_FAST_MODEL, GROQ_SCOUT_MODEL]:
        resp = _call_groq_model(model, messages, KOREA_SYSTEM_PROMPT)
        if resp:
            return resp, f"groq/{model}"

    return None, None


def _route_complex(messages: list) -> tuple[str | None, str | None]:
    """COMPLEX route: Sambanova LLaMA 3.3 → GPT-OSS 120B → Qwen 3.6 27B → Groq Compound → GPT-OSS 20B → Gemma fallback."""
    # Primary: Sambanova LLaMA 3.3
    resp = _call_sambanova_model(SAMBANOVA_COMPLEX_MODEL, messages, KOREA_SYSTEM_PROMPT, max_tokens=900)
    if resp:
        return resp, f"sambanova/{SAMBANOVA_COMPLEX_MODEL}"

    # Secondary: GPT-OSS 120B (GROQ_FAST_MODEL)
    resp = _call_groq_model(GROQ_FAST_MODEL, messages, KOREA_SYSTEM_PROMPT,
                            max_tokens=900, tools=SEARCH_TOOL)
    if resp:
        return resp, f"groq/{GROQ_FAST_MODEL}"

    # Secondary: Qwen 3.6 27B (GROQ_SCOUT_MODEL)
    resp = _call_groq_model(GROQ_SCOUT_MODEL, messages, KOREA_SYSTEM_PROMPT,
                            max_tokens=900, tools=SEARCH_TOOL)
    if resp:
        return resp, f"groq/{GROQ_SCOUT_MODEL}"

    # High TPM Burst: Groq Compound (GROQ_COMPOUND_MODEL)
    resp = _call_groq_model(GROQ_COMPOUND_MODEL, messages, KOREA_SYSTEM_PROMPT,
                            max_tokens=900)
    if resp:
        return resp, f"groq/{GROQ_COMPOUND_MODEL}"

    # Fallback: GPT-OSS 20B (GROQ_LIGHT_MODEL)
    resp = _call_groq_model(GROQ_LIGHT_MODEL, messages, KOREA_SYSTEM_PROMPT,
                            max_tokens=900)
    if resp:
        return resp, f"groq/{GROQ_LIGHT_MODEL}"

    # All Groq failed — fall back to Gemma (Gemini)
    return _route_buddy(messages)


def ask_ai(user_message: str, conversation_history: list = None,
           extra_context: str = "", image_bytes: bytes = None,
           language: str = "en") -> tuple[str | None, str | None]:
    """
    Main entry point. Runs safety check, detects task type, routes to best model.
    Returns (response_text, provider_name).
    """
    if conversation_history is None:
        conversation_history = []

    # Safety check — blocks jailbreaks before wasting API quota
    if not check_message_safety(user_message):
        return (
            "⚠️ This message was flagged by our safety system. "
            "Please ask Korea-related student questions only!",
            "safety_filter"
        )

    messages = list(conversation_history)
    full_msg = user_message if not extra_context else f"{user_message}\n\n[Context: {extra_context}]"
    messages.append({"role": "user", "content": full_msg})

    # Images always go to vision model
    if image_bytes:
        resp = _call_gemini_model(GEMINI_VISION_MODEL, messages, KOREA_SYSTEM_PROMPT, image_bytes)
        if resp:
            return resp, f"gemini/{GEMINI_VISION_MODEL}"
        resp = _call_gemini_model(GEMINI_MODEL, messages, KOREA_SYSTEM_PROMPT, image_bytes)
        return resp, f"gemini/{GEMINI_MODEL}"

    # Arabic language users → allam-2-7b (7K RPD, built for Arabic)
    if language == "ar":
        resp = _call_groq_model(GROQ_ARABIC_MODEL, messages, KOREA_SYSTEM_PROMPT)
        if resp:
            return resp, f"groq/{GROQ_ARABIC_MODEL}"

    # Route by task type
    task = _detect_task(user_message)
    if task == TASK_COMPLEX:
        return _route_complex(messages)
    else:
        return _route_buddy(messages)


async def ask_ai_async(user_message: str, conversation_history: list = None,
                       extra_context: str = "", image_bytes: bytes = None,
                       language: str = "en"):
    return await asyncio.to_thread(
        ask_ai, user_message, conversation_history, extra_context, image_bytes, language
    )


# ── Quiz Generation ────────────────────────────────────────────────────────────
# Uses LLaMA 3.1 8B — 14,400 RPD — perfect for high-frequency quiz generation

LEVEL_LABELS = {1: "beginner", 2: "elementary", 3: "intermediate",
                4: "upper-intermediate", 5: "advanced"}


def generate_quiz_question(level: int = 1, category: str = "daily life") -> dict | None:
    """Generate Korean quiz question. Uses LLaMA 3.1 8B (14.4K RPD)."""
    level_name = LEVEL_LABELS.get(level, "beginner")
    prompt = f"""Generate ONE Korean vocabulary quiz question for a {level_name} student.
Category: {category}

Respond ONLY with this JSON (no markdown):
{{
  "korean": "Korean word or phrase",
  "romanized": "pronunciation",
  "correct_meaning": "correct English meaning",
  "wrong_answers": ["wrong1", "wrong2", "wrong3"],
  "example_sentence": "short Korean example",
  "example_translation": "English translation",
  "tip": "one practical tip for using this in Korea"
}}"""

    messages = [{"role": "user", "content": prompt}]

    # Primary: LLaMA 3.1 8B — 14.4K RPD — best for frequent quiz generation
    raw = _call_groq_model(GROQ_LIGHT_MODEL, messages, max_tokens=600, temperature=0.3)

    # Fallback: Gemma 4 (1500 RPD)
    if not raw:
        raw = _call_gemini_model(GEMINI_BUDDY_MODEL, messages)

    if not raw:
        return None

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        required = ["korean", "romanized", "correct_meaning", "wrong_answers", "example_sentence"]
        if not all(k in data for k in required):
            return None
        if len(data.get("wrong_answers", [])) < 3:
            return None
        return data
    except Exception as e:
        logger.warning("Quiz JSON parse failed: %s", e)
        return None


async def generate_quiz_question_async(level: int = 1, category: str = "daily life") -> dict | None:
    return await asyncio.to_thread(generate_quiz_question, level, category)


# ── News Summarization ─────────────────────────────────────────────────────────
# Uses LLaMA 3.1 8B — 14.4K RPD

def summarize_for_students(text: str, topic: str = "Korea news") -> str | None:
    """Summarize news/content for international students. Uses LLaMA 3.1 8B."""
    prompt = f"""Summarize this {topic} for an international student in Korea.
Be brief (3-4 bullet points). Highlight any practical impact on student life.

Content:
{text[:2000]}"""

    messages = [{"role": "user", "content": prompt}]
    resp = _call_groq_model(GROQ_LIGHT_MODEL, messages, max_tokens=400, temperature=0.5)
    if not resp:
        resp = _call_gemini_model(GEMINI_BUDDY_MODEL, messages)
    return resp


# ── Image Analysis ─────────────────────────────────────────────────────────────
# Uses Gemini 2.5 Flash — vision only, 20 RPD

def analyze_image(image_bytes: bytes, user_question: str = "") -> str | None:
    """Analyze food label, contract, sign, menu for students. Gemini 2.5 Flash vision."""
    prompt = (f'User asked: "{user_question}"\n\n' if user_question else "")
    prompt += (
        "Analyse this image for an international student in South Korea:\n"
        "1. What is this? (food label, contract, sign, menu...)\n"
        "2. Any risks? (pork, alcohol, allergens, scam signs)\n"
        "3. Korean text: translate important parts\n"
        "4. Practical tip\nBe specific."
    )
    return _call_gemini_model(
        GEMINI_VISION_MODEL,
        [{"role": "user", "content": prompt}],
        KOREA_SYSTEM_PROMPT,
        image_bytes
    )


async def analyze_image_async(image_bytes: bytes, user_question: str = "") -> str | None:
    return await asyncio.to_thread(analyze_image, image_bytes, user_question)


# ── Voice Transcription (Groq Whisper) ────────────────────────────────────────
_whisper_semaphore = asyncio.Semaphore(3)  # max 3 concurrent voice calls


def transcribe_audio(audio_bytes: bytes, lang_hint: str = "ko") -> str | None:
    """Transcribe voice note via Groq Whisper Turbo. 20 RPM, 2K RPD."""
    api_key = get_groq_key()
    if not api_key or not audio_bytes or len(audio_bytes) < 500:
        return None

    import tempfile, os, time as _time
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        def _call(retry: bool = False) -> str | None:
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
                logger.warning("Whisper 429 — backing off 10s")
                _time.sleep(10)
                return _call(retry=True)
            r.raise_for_status()
            return r.json().get("text", "").strip()

        result = _call()
        os.unlink(tmp_path)
        return result
    except Exception as e:
        logger.error("Whisper error: %s", e)
        return None


async def transcribe_audio_async(audio_bytes: bytes) -> str | None:
    async with _whisper_semaphore:
        return await asyncio.to_thread(transcribe_audio, audio_bytes)


# ── Legacy alias (backward compat with bot.py calls) ──────────────────────────
def call_gemini(messages: list, system_prompt: str = None, image_bytes: bytes = None) -> str | None:
    """Backward compatible wrapper — routes to best available Gemini model."""
    if image_bytes:
        return _call_gemini_model(GEMINI_VISION_MODEL, messages, system_prompt, image_bytes)

    # Interceptor: If it's the Korean Brain or Buddy, force the unlimited model
    if system_prompt and ("Minsu" in system_prompt or "Korean Brain" in system_prompt):
        resp = _call_gemini_model(GEMINI_BUDDY_MODEL, messages, system_prompt)
        if resp: return resp
        return _call_gemini_model(GEMINI_BUDDY_BACKUP, messages, system_prompt)

    resp = _call_gemini_model(GEMINI_BUDDY_MODEL, messages, system_prompt)
    if not resp:
        resp = _call_gemini_model(GEMINI_MODEL, messages, system_prompt)
    return resp


def call_groq(messages: list, system_prompt: str = None) -> str | None:
    """Backward compatible wrapper — acts as a Smart Interceptor for legacy code with full fallbacks."""
    # SMART INTERCEPTOR 1: Offload Buddy to Light Model (gpt-oss-20b)
    if system_prompt and ("Minsu" in system_prompt or "KakaoTalk" in system_prompt):
        logger.info("SMART INTERCEPT: Routing Minsu to Groq Light Model (gpt-oss-20b)")
        resp = _call_groq_model(GROQ_LIGHT_MODEL, messages, system_prompt)
        if resp:
            return resp

    # SMART INTERCEPTOR 2: Intent Classification to Light Model
    if system_prompt and "intent classifier" in system_prompt.lower():
        logger.info("SMART INTERCEPT: Routing Intent to Light Model (gpt-oss-20b)")
        resp = _call_groq_model(GROQ_LIGHT_MODEL, messages, system_prompt)
        if resp:
            return resp

    # SMART INTERCEPTOR 3: DormChef to Light Model
    if system_prompt and "Dorm-Chef" in system_prompt:
        logger.info("SMART INTERCEPT: Routing Chef to Light Model (gpt-oss-20b)")
        resp = _call_groq_model(GROQ_LIGHT_MODEL, messages, system_prompt)
        if resp:
            return resp

    # Standard Fallback Chain for Complex tasks or interceptor fallbacks
    for model in [GROQ_FAST_MODEL, GROQ_SCOUT_MODEL, GROQ_COMPOUND_MODEL, GROQ_LIGHT_MODEL]:
        resp = _call_groq_model(model, messages, system_prompt, tools=SEARCH_TOOL)
        if resp:
            return resp

    # Ultimate cross-provider fallback to Gemini if all Groq models fail
    return call_gemini(messages, system_prompt)
