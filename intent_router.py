# intent_router.py — K-Transition OS v6.0
# LLM-powered Intent Classification + Entity Extraction
# Single Groq call replaces all keyword matching
# Extracts structured data for zero-command execution

import json
import asyncio
import logging
from ai_brain import call_groq

logger = logging.getLogger(__name__)

ROUTER_SYSTEM = """You are an intent classifier for a Korea international student survival bot.
Classify the user's message and extract entities.

RESPOND ONLY WITH VALID JSON — no markdown, no explanation, no extra text:
{{
  "intent": "<intent>",
  "entities": {{}},
  "korean_query": null,
  "confidence": 0.0
}}

INTENTS (pick ONE):
- "cook" — wants to cook, lists ingredients, food prep. Entities: {{"ingredients": "..."}}
- "map" — find place, directions, nearby. Entities: {{"query": "...", "type": "search|nearby|directions", "origin": "...", "destination": "..."}}
- "buddy" — casual chat, emotional support, homesick, lonely, stressed, wants a friend. Entities: {{"mood": "..."}}
- "interpret" — translate or understand Korean/English text. Entities: {{"text": "...", "direction": "to_korean|to_english|explain"}}
- "simulate" — culture shock scenario. Entities: {{"topic": "..."}}
- "practice" — Korean language roleplay practice. Entities: {{"scenario": "..."}}
- "news" — Korea news or updates. Entities: {{"topic": "..."}}
- "sos" — emergency help. Entities: {{"type": "..."}}
- "visa" — visa, ARC, immigration. Entities: {{}}
- "challenge" — daily survival challenge. Entities: {{}}
- "track" — budget/habit tracker. Entities: {{"tracker": "...", "value": "..."}}
- "apps" — app recommendations. Entities: {{"category": "..."}}
- "hack" — Korea life hacks. Entities: {{"topic": "..."}}
- "schedule" — first week plan, tasks. Entities: {{}}
- "quiz" — Korean quiz. Entities: {{}}
- "word" — Korean word of the day. Entities: {{}}
- "phrase" — survival phrases. Entities: {{"category": "..."}}
- "level" — XP/level status. Entities: {{}}
- "profile" — check profile. Entities: {{}}
- "emergency" — emergency numbers. Entities: {{}}
- "rate" — exchange rates. Entities: {{"amount": "..."}}
- "culture" — cultural tips. Entities: {{"topic": "..."}}
- "scam" — scam check. Entities: {{"situation": "..."}}
- "general_question" — general Korea question. Entities: {{}}
- "greeting" — hello, hi. Entities: {{}}

CRITICAL MAP RULES:
1. ALWAYS set "korean_query" for map intents — translate search to Korean.
   "halal restaurant" → "할랄 식당", "pharmacy" → "약국", "ATM" → "ATM 현금인출기",
   "gym" → "헬스장", "laundry" → "세탁소", "convenience store" → "편의점",
   "hospital" → "병원", "bank" → "은행", "cafe" → "카페", "library" → "도서관",
   "post office" → "우체국", "police station" → "경찰서", "supermarket" → "마트"
2. For directions ("from X to Y", "how to get to") → type="directions", extract origin+destination
3. For "near me/nearby/closest" → type="nearby"

CRITICAL COOK RULES:
1. If user just lists food items with no context → intent="cook"
2. Extract ALL ingredients mentioned

CRITICAL BUDDY RULES:
1. "I miss home", "feeling lonely", "stressed out", "nobody understands" → intent="buddy"
2. Casual friendly messages like "how are you", "what's up" → intent="buddy"

USER CONTEXT: University={university}, City={city}, Diet={diet}"""

# Fast pre-filter — skip LLM for single-word obvious matches
_QUICK = {
    "hi": ("greeting", 0.95), "hello": ("greeting", 0.95), "hey": ("greeting", 0.95),
    "안녕": ("greeting", 0.95), "안녕하세요": ("greeting", 0.95),
    "sos": ("sos", 0.95), "emergency": ("emergency", 0.95),
    "news": ("news", 0.90), "quiz": ("quiz", 0.90), "level": ("level", 0.90),
    "profile": ("profile", 0.90), "visa": ("visa", 0.90),
}


async def route_intent(text: str, user_info: dict = None) -> dict:
    """Classify user message intent + extract entities via LLM.
    Returns: {intent, entities, korean_query, confidence}
    """
    text_lower = text.lower().strip()

    # Quick pre-filter
    if text_lower in _QUICK:
        intent, conf = _QUICK[text_lower]
        return {"intent": intent, "entities": {}, "korean_query": None, "confidence": conf}

    user_info = user_info or {}
    system = ROUTER_SYSTEM.format(
        university=user_info.get("university", "unknown"),
        city=user_info.get("city", "unknown"),
        diet=user_info.get("diet", "none"),
    )

    messages = [{"role": "user", "content": text}]

    try:
        raw = await asyncio.to_thread(call_groq, messages, system)
        if not raw:
            return _fallback(text)

        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(clean)

        if "intent" not in result:
            return _fallback(text)

        result.setdefault("entities", {})
        result.setdefault("korean_query", None)
        result.setdefault("confidence", 0.5)

        logger.info("Intent: %s (%.2f) | Entities: %s", result["intent"], result["confidence"], result["entities"])
        return result

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Intent router parse error: %s", e)
        return _fallback(text)
    except Exception as e:
        logger.error("Intent router failed: %s", e)
        return _fallback(text)


def _fallback(text: str) -> dict:
    """Keyword-based fallback when LLM router fails."""
    t = text.lower()

    if any(w in t for w in ["cook", "recipe", "ingredient", "egg", "ramen", "hungry", "fridge", "what can i make"]):
        return {"intent": "cook", "entities": {"ingredients": text}, "korean_query": None, "confidence": 0.6}
    if any(w in t for w in ["map", "direction", "nearby", "find", "where is", "how to get", "closest", "nearest"]):
        return {"intent": "map", "entities": {"query": text, "type": "search"}, "korean_query": None, "confidence": 0.6}
    if any(w in t for w in ["lonely", "sad", "miss home", "homesick", "depressed", "alone", "stressed", "miss my"]):
        return {"intent": "buddy", "entities": {"mood": "sad"}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["news", "headline", "what's happening", "update"]):
        return {"intent": "news", "entities": {}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["translate", "mean", "korean for", "say in korean", "how do you say", "what does"]):
        return {"intent": "interpret", "entities": {"text": text}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["visa", "arc ", "immigration", "d-2", "d-4", "hikorea"]):
        return {"intent": "visa", "entities": {}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["emergency", "police", "ambulance", "help me", "danger"]):
        return {"intent": "emergency", "entities": {}, "korean_query": None, "confidence": 0.8}
    if any(w in t for w in ["scam", "fraud", "suspicious", "cheat"]):
        return {"intent": "scam", "entities": {"situation": text}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["exchange", "rate", "won to", "usd", "krw"]):
        return {"intent": "rate", "entities": {}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["schedule", "first week", "checklist", "to do"]):
        return {"intent": "schedule", "entities": {}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["word of", "learn korean", "korean word"]):
        return {"intent": "word", "entities": {}, "korean_query": None, "confidence": 0.7}
    if any(w in t for w in ["challenge", "daily challenge"]):
        return {"intent": "challenge", "entities": {}, "korean_query": None, "confidence": 0.7}

    return {"intent": "general_question", "entities": {}, "korean_query": None, "confidence": 0.3}
