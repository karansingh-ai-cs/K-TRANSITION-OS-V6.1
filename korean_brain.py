# korean_brain.py — K-Transition OS v5.0
# AI-powered Korean scenario practice — like Duolingo but for REAL situations
# User practices ordering food, going to pharmacy, talking to professor, etc.
# AI adapts difficulty to user's Korean level

import asyncio
import logging

logger = logging.getLogger(__name__)

SCENARIOS = {
    "food":      {"emoji": "🍜", "title": "Order Food at a Restaurant",   "context": "You're at a Korean restaurant. The 아주머니 (lady) is waiting for your order."},
    "cafe":      {"emoji": "☕", "title": "Order at a Korean Café",        "context": "You're at a Korean café. The barista is ready to take your order."},
    "pharmacy":  {"emoji": "💊", "title": "Visit the Pharmacy",            "context": "You're at a 약국 (pharmacy). You need to describe your symptoms to the pharmacist."},
    "professor": {"emoji": "👨‍🏫", "title": "Talk to Your Professor",       "context": "You need to ask your Korean professor about an assignment deadline. You should use formal Korean (존댓말)."},
    "taxi":      {"emoji": "🚖", "title": "Take a Taxi",                   "context": "You're in a taxi. Tell the driver where you want to go and ask about the fare."},
    "market":    {"emoji": "🏪", "title": "Shop at a Market",              "context": "You're at a Korean traditional market (시장). You want to buy some fruits and ask the price."},
    "bank":      {"emoji": "🏦", "title": "At the Bank",                   "context": "You're at Shinhan Bank trying to open an account. The staff is asking you questions."},
    "hospital":  {"emoji": "🏥", "title": "At the Hospital",               "context": "You're at a hospital reception desk. You need to register and describe your problem."},
    "landlord":  {"emoji": "🏠", "title": "Talk to Your Landlord",         "context": "Your landlord is calling about rent. You also need to report a broken heater (보일러)."},
    "friend":    {"emoji": "🤝", "title": "Chat with a Korean Friend",     "context": "You're meeting a Korean friend at a café. They want to practice English but you want to practice Korean!"},
    "shop":      {"emoji": "🛍️", "title": "Shopping for Clothes",          "context": "You're at a Korean clothing store. You want to try something on and ask about sizes/prices."},
    "post":      {"emoji": "📮", "title": "Send a Package at Post Office", "context": "You're at 우체국 (post office) trying to send a package to your home country."},
}

BRAIN_SYSTEM_PROMPT = """You are a Korean conversation practice partner for K-Transition OS.
You are roleplaying as: {role_description}

STUDENT'S KOREAN LEVEL: {level_name}
(Level 1=total beginner, Level 5=advanced)

RULES:
1. You speak KOREAN as the character. After each Korean line, add [Translation] in English.
2. Keep your Korean responses SHORT (1-2 sentences max).
3. For Level 1-2: Use very simple Korean, lots of hints in [brackets].
4. For Level 3-4: More natural Korean, fewer hints.
5. For Level 5: Natural Korean, no hints.
6. After the student responds, give FEEDBACK:
   - ✅ What they said correctly
   - 🔧 How to improve (correct grammar/vocabulary)
   - 💡 A useful phrase they could use next
7. Keep the conversation going naturally — don't end after one exchange.
8. Be encouraging! Even small attempts deserve praise.
9. Use natural Korean with fillers: 네, 아, 음, 저기요
10. The student may respond in English, broken Korean, or mix — handle all gracefully.

SCENARIO: {scenario_context}

Start by speaking Korean as your character. Set the scene naturally."""

LEVEL_NAMES = {1: "Total Beginner", 2: "Elementary", 3: "Intermediate", 4: "Upper-Intermediate", 5: "Advanced"}


async def start_practice(scenario_key, korean_level=1):
    """Start a Korean practice session. Returns AI's opening line."""
    from ai_brain import call_groq

    scenario = SCENARIOS.get(scenario_key, SCENARIOS["food"])
    level_name = LEVEL_NAMES.get(korean_level, "Beginner")

    system = BRAIN_SYSTEM_PROMPT.format(
        role_description=scenario["context"],
        level_name=level_name,
        scenario_context=scenario["context"]
    )

    messages = [
        {"role": "user", "content": f"[Start the scenario. I'm a Level {korean_level} Korean learner. Speak Korean as the character and set the scene.]"}
    ]

    try:
        response = await asyncio.to_thread(call_groq, messages, system)
        if response:
            return response
    except Exception as e:
        logger.error(f"Korean Brain start failed: {e}")

    return (
        f"{scenario['emoji']} {scenario['title']}\n\n"
        "안녕하세요! [Hello!]\n\n"
        "AI is temporarily unavailable. Practice these phrases:\n"
        "• 이거 주세요 — This one please\n"
        "• 얼마예요? — How much?\n"
        "• 감사합니다 — Thank you\n\n"
        "Try again in a moment!"
    )


async def continue_practice(user_response, scenario_key, conversation_history, korean_level=1):
    """Continue an ongoing practice conversation."""
    from ai_brain import call_groq

    scenario = SCENARIOS.get(scenario_key, SCENARIOS["food"])
    level_name = LEVEL_NAMES.get(korean_level, "Beginner")

    system = BRAIN_SYSTEM_PROMPT.format(
        role_description=scenario["context"],
        level_name=level_name,
        scenario_context=scenario["context"]
    )

    messages = list(conversation_history)
    messages.append({"role": "user", "content": user_response})

    try:
        response = await asyncio.to_thread(call_groq, messages, system)
        if response:
            return response
    except Exception as e:
        logger.error(f"Korean Brain continue failed: {e}")

    return "죄송합니다! AI had a hiccup. Say something again or type /practice to restart!"


def get_scenario_list():
    """Return formatted list of available scenarios."""
    msg = "🧠 Korean Brain — Practice Scenarios\n\n"
    msg += "Choose a situation to practice:\n\n"
    for key, scenario in SCENARIOS.items():
        msg += f"{scenario['emoji']} /practice {key}\n   {scenario['title']}\n\n"
    msg += "💡 The AI adapts to your Korean level!\n"
    msg += "Your level is based on your /quiz progress.\n\n"
    msg += "During practice, just reply in Korean (or English!) and the AI will coach you."
    return msg
