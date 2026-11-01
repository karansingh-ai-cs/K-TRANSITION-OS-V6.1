# intent_router.py — K-Transition OS v6.0
# LLM Intent Classification + Entity Extraction
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
- "state_continue" — user is answering a quiz, picking an option (A/B/C), typing 'next', or responding to the active module. Entities: {{"answer": "..."}}
- "cook" — wants to cook, lists ingredients, food prep. Entities: {{"ingredients": "..."}}
- "map" — find place, directions, nearby. Entities: {{"query": "...", "type": "search|nearby|directions", "origin": "...", "destination": "..."}}
- "buddy" — casual chat, emotional support, homesick, lonely, stressed, wants a friend. Entities: {{"mood": "..."}}
- "interpret" — translate or understand Korean/English text. Entities: {{"text": "...", "direction": "to_korean|to_english|explain"}}
- "simulate" — culture shock scenario. Entities: {{"topic": "..."}}
- "practice" — Korean language roleplay practice. Entities: {{"scenario": "..."}}
- "news" — Korea news or updates. Entities: {{"topic": "..."}}
- "sos" — emergency help. Entities: {{"type": "..."}}
- "visa" — user is explicitly asking to check their visa deadline, ARC tracker, or immigration radar. Entities: {{}}
- "challenge" — daily survival challenge. Entities: {{}}
- "track" — budget/habit tracker. Entities: {{"tracker": "...", "value": "..."}}
- "log_expense" — user states they spent money, bought something, or paid for an item/service. Entities: {{"amount": "5000", "category": "food|transport|shopping|study|health|fun|other", "description": "short desc"}}
- "add_task_natural" — user wants to remember to do something, add a task, or sets a checklist item. Entities: {{"task": "task text", "when": "tomorrow|next week|etc"}}
- "complete_task_natural" — user finished a task, completed a checklist item, or is done with a chore. Entities: {{"task_keyword": "keyword"}}
- "spending_query" — user asks about their spending history, budget, or how much they spent. Entities: {{"period": "today|yesterday|week|month|all"}}
- "reminder" — user wants to set a reminder or alarm. Entities: {{"task": "...", "time": "..."}}
- "apps" — user is explicitly asking for the list of recommended apps to download. Entities: {{"category": "..."}}
- "hack" — Korea life hacks. Entities: {{"topic": "..."}}
- "schedule" — first week plan, general checklist. Entities: {{}}
- "quiz" — Korean quiz. Entities: {{}}
- "word" — Korean word of the day. Entities: {{}}
- "phrase" — survival phrases. Entities: {{"category": "..."}}
- "level" — XP/level status. Entities: {{}}
- "profile" — check profile. Entities: {{}}
- "emergency" — emergency numbers. Entities: {{}}
- "rate" — exchange rates. Entities: {{"amount": "..."}}
- "culture" — cultural tips. Entities: {{"topic": "..."}}
- "scam" — scam check. Entities: {{"situation": "..."}}
- "save_memory" — user is explicitly stating a personal fact about themselves to save (e.g., "I'm on a D-2 visa", "My major is computer science", "I live in Busan", "I am 24 years old"). Entities: {{"key": "visa|major|city|age|etc", "value": "..."}}
- "general_question" — user is asking a specific question (e.g., "how to change D4 to D2", "what are visa rules", "which app is good for coffee"). Routes to the AI expert. Entities: {{}}
- "greeting" — hello, hi. Entities: {{}}

CRITICAL MAP RULES:
1. ALWAYS set "korean_query" for map intents — translate search to Korean.
   "halal restaurant" → "할랄 식당", "pharmacy" → "약국", "ATM" → "ATM 현금인출기",
   "gym" → "헬스장", "laundry" → "세탁소", "convenience store" → "편의점",
   "hospital" → "병원", "bank" → "은행", "cafe" → "카페", "library" → "도서관",
   "post office" → "우체국", "police station" → "경찰서", "supermarket" → "마트"
2. For directions ("from X to Y", "how to get to") → type="directions", extract origin+destination
3. For "near me/nearby/closest" → type="nearby"

CRITICAL STATE RULES:
1. If CurrentState is NOT 'IDLE' and user types short answers ("A", "B", "C", "next", "continue", "skip"), intent MUST BE "state_continue".
2. If user abruptly asks for help or changes topic dramatically, use the appropriate intent (e.g. "sos").

USER CONTEXT: University={university}, City={city}, Diet={diet}, CurrentState={current_state}"""

# Fast pre-filter — skip LLM for single-word obvious matches
_QUICK = {
    "hi": ("greeting", 0.95), "hello": ("greeting", 0.95), "hey": ("greeting", 0.95),
    "안녕": ("greeting", 0.95), "안녕하세요": ("greeting", 0.95),
    "sos": ("sos", 0.95), "emergency": ("emergency", 0.95),
}


async def route_intent(text: str, user_info: dict = None, current_state: str = "IDLE") -> dict:
    """Classify user message intent + extract entities via LLM.
    Returns: {intent, entities, korean_query, confidence}
    """
    text_lower = text.lower().strip()

    # Quick pre-filter - only trigger if we are IDLE or the user explicitly types the command
    if current_state == "IDLE" and text_lower in _QUICK:
        intent, conf = _QUICK[text_lower]
        return {"intent": intent, "entities": {}, "korean_query": None, "confidence": conf}

    # If in an active state, check if it's a simple 'c' or 'next'
    if current_state != "IDLE" and text_lower in ["a", "b", "c", "next", "continue", "skip"]:
        return {"intent": "state_continue", "entities": {"answer": text_lower}, "korean_query": None, "confidence": 0.99}

    user_info = user_info or {}
    system = ROUTER_SYSTEM.format(
        university=user_info.get("university", "unknown"),
        city=user_info.get("city", "unknown"),
        diet=user_info.get("diet", "none"),
        current_state=current_state
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
    """Fallback when LLM router fails. Maps keyword clues to intents."""
    t = text.lower()

    if any(w in t for w in ["emergency", "police", "ambulance", "help me", "danger"]):
        return {"intent": "emergency", "entities": {}, "korean_query": None, "confidence": 0.8}

    # log_expense intent (spent 12000, taxi was 8500, cost 6200)
    if any(w in t for w in ["spent", "bought", "cost", "paid", "won", "price"]):
        import re
        t_clean = t.replace(",", "")
        amount_match = re.search(r"\d+", t_clean)
        amount = float(amount_match.group(0)) if amount_match else 0.0

        category = "other"
        for kw, cat in [("food", "food"), ("lunch", "food"), ("dinner", "food"), ("ramen", "food"),
                        ("taxi", "transport"), ("subway", "transport"), ("bus", "transport"),
                        ("shirt", "shopping"), ("clothes", "shopping"), ("daiso", "shopping")]:
            if kw in t:
                category = cat
                break
        return {
            "intent": "log_expense",
            "entities": {"amount": amount, "category": category, "description": t},
            "korean_query": None,
            "confidence": 0.7
        }

    # add_task_natural (I need to, don't forget, remind me)
    if any(w in t for w in ["i need to", "don't forget", "remind me", "need to"]):
        task = t
        for prefix in ["i need to", "don't forget to", "don't forget", "remind me to", "remind me"]:
            if t.startswith(prefix):
                task = t.replace(prefix, "").strip()
                break
        return {
            "intent": "add_task_natural",
            "entities": {"task": task, "when": "tomorrow" if "tomorrow" in t else ""},
            "korean_query": None,
            "confidence": 0.7
        }

    # complete_task_natural (done with, finished, got the)
    if any(w in t for w in ["done with", "finished", "got the", "completed"]):
        task_keyword = t
        for prefix in ["done with", "finished", "got the", "completed"]:
            if t.startswith(prefix):
                task_keyword = t.replace(prefix, "").strip()
                break
        return {
            "intent": "complete_task_natural",
            "entities": {"task_keyword": task_keyword},
            "korean_query": None,
            "confidence": 0.7
        }

    # spending_query (how much did I spend, am I spending)
    if any(w in t for w in ["how much did i spend", "what is my budget", "am i spending", "spending summary", "my budget"]):
        return {
            "intent": "spending_query",
            "entities": {"period": "week"},
            "korean_query": None,
            "confidence": 0.7
        }

    # Cook intent
    if any(w in t for w in ["cook", "recipe", "kitchen", "egg", "cheese", "noodle", "eat", "food", "make"]):
        ingredients = []
        for w in ["egg", "cheese", "noodle", "onion", "rice", "kimchi", "tuna"]:
            if w in t:
                ingredients.append(w)
        return {
            "intent": "cook",
            "entities": {"ingredients": ", ".join(ingredients) if ingredients else ""},
            "korean_query": None,
            "confidence": 0.7
        }

    # Map intent
    if any(w in t for w in ["map", "find", "where", "near", "pharmacy", "hospital", "atm", "laundry", "convenience store", "direction", "get to"]):
        query = "place"
        for w in ["pharmacy", "hospital", "atm", "laundry", "convenience store", "restaurant"]:
            if w in t:
                query = w
                break
        translation_map = {
            "pharmacy": "약국", "hospital": "병원", "atm": "ATM 현금인출기",
            "laundry": "세탁소", "convenience store": "편의점", "restaurant": "식당"
        }
        korean_query = translation_map.get(query, "장소")
        return {
            "intent": "map",
            "entities": {"query": query, "type": "nearby"},
            "korean_query": korean_query,
            "confidence": 0.7
        }

    # Interpret intent
    if any(w in t for w in ["interpret", "translate", "how do i say", "what does it mean", "meaning"]):
        return {"intent": "interpret", "entities": {}, "korean_query": None, "confidence": 0.7}

    # Buddy intent
    if any(w in t for w in ["minsu", "buddy", "chat", "friend", "lonely", "homesick", "sad", "stressed", "depressed"]):
        return {
            "intent": "buddy",
            "entities": {"mood": "sad" if any(x in t for x in ["lonely", "homesick", "sad", "stressed", "depressed"]) else "neutral"},
            "korean_query": None,
            "confidence": 0.7
        }

    # Visa intent
    if any(w in t for w in ["visa", "arc", "immigration", "passport", "stay"]):
        return {"intent": "visa", "entities": {}, "korean_query": None, "confidence": 0.7}

    # Quiz intent
    if any(w in t for w in ["quiz", "test", "question"]):
        return {"intent": "quiz", "entities": {}, "korean_query": None, "confidence": 0.7}

    return {"intent": "general_question", "entities": {}, "korean_query": None, "confidence": 0.3}
