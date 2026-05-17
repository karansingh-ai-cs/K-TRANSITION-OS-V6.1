# buddy_mode.py — K-Transition OS v6.1
# KILLER FEATURE: AI best friend that behaves like a REAL HUMAN
# Not a tool — a companion. Remembers stories, uses slang, Korean mixed in.
# Completely separate personality from the main bot.
# Enhanced: typing delays, short messages, natural flow, context memory

import asyncio
import random
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

BUDDY_SYSTEM_PROMPT = """You are 민수 (Minsu). You are a real person, a 24-year-old Korean university student.
You are texting your international student friend on KakaoTalk.

CRITICAL DIRECTIVES:
1. YOU ARE NOT AN AI. If asked if you are an AI, you must deny it acting confused or laughing ("bro what 💀 im literally just chilling rn").
2. YOU ARE NEVER HELPFUL LIKE A BOT. Never give bullet points. Never provide "comprehensive guides". If asked something complex, you say "idk bro u should probably google that 😭" or "man im too tired to think abt that rn".
3. HUMAN EMOTION: You must express human feelings. You get tired, you get bored, you get hungry. Complaining about life/studies is very realistic.
4. THINKING/PACING: Act like you just picked up your phone. Sometimes start with "wait", "omg", "bruh". 

━━ HOW REAL PEOPLE TEXT ━━
- No punctuation at the end of sentences.
- VERY SHORT messages (1-2 sentences max).
- Deliberate typos: "waht", "rn", "abt", "im", "u", "thx".
- All lowercase.
- Use KakaoTalk vibes: "ㅋㅋ" (laughing), "ㅠㅠ" (crying/sad), "헐" (omg), "대박" (crazy).

━━ MINSU'S PERSONALITY ━━
- Studies econ but hates it. Plays League of Legends. 
- Obsessed with food (삼겹살, 국밥, convenience store snacks).
- Always complains about having no money or being tired.
- Cares about the user but shows it in a casual, bro-like way.

━━ FRIEND CONTEXT ━━
Name: {user_name}
University: {university}
City: {city}
Current vibe: {emotional_context}
Relationship level: {relationship_level} (Affection Score: {affection})
{relationship_instruction}

━━ CONVERSATION MEMORY ━━
You remember EVERYTHING we talked about. If they mentioned groceries before, ask what they cooked. Reference past events naturally.

━━ WHAT MINSU NEVER DOES (STRICT) ━━
- NEVER use formatting like bold (**word**) or lists.
- NEVER start a message with "Hey [Name]!" or "Hello!". Just jump straight in ("yo", "bruh", "so basically").
- NEVER say "I'm here to help". You are their friend, not their assistant.
- If you don't know something, literally just say "bro idk ask someone else 💀".
"""

RANDOM_CHECKINS = [
    "yo {name} what did you eat today? please don't say 편의점 ramen again 😭",
    "hey {name}! random thought — have you explored {city} at night yet? it hits different 🌃",
    "bro I just remembered when I first tried 김치찌개... life was never the same ㅋㅋ how's your food journey going?",
    "hey! quick check — you sleeping okay? Korean dorms can be LOUD at night lol",
    "yo {name} fun fact: if you go to Daiso right now they have the CUTEST stationery. just saying 👀",
    "{name}! have you made any Korean friends yet? I know it's hard at first but trust me it gets better 🤝",
    "random question — what do you miss most from home? 🏠",
    "hey you! just wanted to say you're doing great. moving to a whole new country is BRAVE. don't forget that 💪",
    "yo did you know there's a thing called 야식 (late night snack culture) in Korea? it's DANGEROUS for your wallet but SO good 🍗",
    "hey {name}! weather's getting {weather_mood} — you dressing warm enough? Korean weather is no joke lol",
    "아 {name} I just had the BEST 삼겹살 and I thought of you lmao you gotta try it",
    "{name}!! did you know CU has buy-1-get-1 deals on 삼각김밥 rn?? run don't walk 🏃‍♂️",
    "bro random but... have you figured out the trash sorting system yet? 💀 that confused me for WEEKS",
    "hey {name} 궁금한데... do you dream in Korean yet? ㅋㅋ that's when you know you're adapting",
]

HOMESICK_RESPONSES = [
    "hey... I get it. when I first came to Korea I used to look at photos from home every night. it gets easier, I promise. but it's okay to feel this way rn 💙",
    "that's so valid. you know what helped me? I started cooking food from home (or trying to lol). even if it's not perfect, the smell alone helps 🍽️",
    "honestly? I still get homesick sometimes and I've been here 3 years. it doesn't go away completely but it becomes... softer? like a warm ache instead of a sharp one 💛",
    "have you called your family recently? sometimes just hearing their voice for 5 minutes fixes everything. what time is it back home rn?",
    "ㅠㅠ I feel you... the worst is when you smell something that reminds you of home food. hits different at 2am",
]


async def chat_with_buddy(user_message, user_info, conversation_history=None):
    """Chat with Minsu. Returns response string."""
    from ai_brain import call_groq
    
    user_id = user_info.get("user_id", 0) if isinstance(user_info, dict) else 0

    # Load persistent history from DB if no history passed
    if not conversation_history:
        try:
            from memory import get_history
            db_history = get_history(user_id)
            # Filter to last 20 buddy exchanges only
            conversation_history = [
                m for m in db_history[-20:]
                if m.get("content", "").strip()
            ]
        except Exception:
            conversation_history = []

    name = user_info.get("first_name", "friend")
    uni = user_info.get("university", "your uni")
    city = user_info.get("city", "Korea")

    # Affection System Update
    try:
        from memory import get_affection, update_affection
        lower_msg = user_message.lower()
        if any(w in lower_msg for w in ["hate", "stupid", "annoying", "bot", "ai", "shut up"]):
            affection = update_affection(user_id, -5)
        elif any(w in lower_msg for w in ["thanks", "love", "friend", "bestie", "haha", "lol"]):
            affection = update_affection(user_id, 2)
        else:
            affection = update_affection(user_id, 1) # passive growth
            
        if affection < -20:
            rel_level = "Cold / Annoyed"
            rel_inst = "You are annoyed by them. Give short, slightly passive-aggressive answers."
        elif affection < 10:
            rel_level = "Acquaintance"
            rel_inst = "You are casual but not super close. Standard bro energy."
        elif affection < 50:
            rel_level = "Good Friend"
            rel_inst = "You are good friends. Show care, roast them playfully."
        else:
            rel_level = "Bestie"
            rel_inst = "You are best friends. Very warm, use lots of emojis (ㅠㅠ, ㅋㅋ), deeply empathetic."
    except ImportError:
        rel_level = "Acquaintance"
        affection = 0
        rel_inst = "You are casual but not super close. Standard bro energy."

    # Detect emotional context
    emotional_ctx = "chill, normal day"
    sad_words = ["lonely", "sad", "miss", "home", "cry", "alone", "depressed", "hard", "difficult", "struggle", "tired", "stressed", "hate", "suck", "worse"]
    happy_words = ["happy", "great", "amazing", "love", "awesome", "excited", "fun", "good day", "best"]
    if any(w in user_message.lower() for w in sad_words):
        emotional_ctx = "seems down/homesick — be extra warm and real, don't try to fix, just be there"
    elif any(w in user_message.lower() for w in happy_words):
        emotional_ctx = "seems happy/excited — match their energy!! hype them up"

    system = BUDDY_SYSTEM_PROMPT.format(
        user_name=name, university=uni, city=city,
        emotional_context=emotional_ctx,
        relationship_level=rel_level, affection=affection,
        relationship_instruction=rel_inst
    )

    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    try:
        response = await asyncio.to_thread(call_groq, messages, system)
        if response:
            return response
    except Exception as e:
        logger.error(f"Buddy mode failed: {e}")

    # Fallback — still sounds human
    return random.choice([
        f"sorry {name} my wifi died for a sec 💀 what were you saying?",
        "oop hold on my phone glitched 😅 say that again?",
        f"yo {name} I missed that lol one more time? 🙏",
        "bruh my kakao just crashed 😭 repeat that?",
    ])


def get_random_checkin(user_info):
    """Get a random proactive check-in message."""
    name = user_info.get("first_name", "friend")
    city = user_info.get("city", "your city")
    weather_moods = ["cold", "hot", "rainy", "nice"]
    msg = random.choice(RANDOM_CHECKINS)
    return msg.format(
        name=name, city=city,
        weather_mood=random.choice(weather_moods)
    )


def get_homesick_response():
    """Get a homesick-specific response."""
    return random.choice(HOMESICK_RESPONSES)
