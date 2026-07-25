# guided_tour.py — K-Transition OS v6.0
# Senior's 1-Minute Interactive Guided Tour (선배의 1분 가이드)
# An elegant, frictionless onboarding carousel designed to walk users through core features.

TOUR_STEPS = {
    1: {
        "title": "🌱 Step 1: Your Day 1 in Korea (선배의 첫날 조언)",
        "text": (
            "Hey! Welcome to Korea! 🇰🇷 As your senior (선배), my first advice is about Day 1 survival.\n\n"
            "Three things are absolutely critical on your first day:\n"
            "1. **T-Money Card:** Buy at any convenience store for ₩4,000 for all transit.\n"
            "2. **SIM Card:** Get a prepaid SIM using your passport at the airport or any convenience store.\n"
            "3. **ARC (외국인등록증):** Book your appointment immediately at HiKorea.go.kr!\n\n"
            "We have a built-in checklist to track all of this. Click below to try it!"
        ),
        "next_step": 2,
        "action_text": "📅 See Day 1 Checklist",
        "action_data": "tour_act_checklist"
    },
    2: {
        "title": "🍽️ Step 2: Food & Maps (밥과 길 찾기)",
        "text": (
            "Getting lost or eating hidden pork are the most common student struggles!\n\n"
            "• **DormChef:** Have a microwave and some CU ingredients? Tell our chef what you have and get instant, safe microwave recipes!\n"
            "• **Tri-Engine Maps:** Need a pharmacy (약국) or ATM? We translate locations to Korean search strings and generate Kakao/Naver map links that actually work in Korea!\n\n"
            "Let's try cooking some convenience store food right now!"
        ),
        "next_step": 3,
        "prev_step": 1,
        "action_text": "🍳 Try Dorm Chef",
        "action_data": "tour_act_chef"
    },
    3: {
        "title": "🧑 Step 3: Speak like a Local & Chat (친구 민수)",
        "text": (
            "Don't study Korean like a textbook — practice in real life!\n\n"
            "• **Minsu (AI Buddy):** Chat with your Korean friend Minsu. He texts like a real student (uses ㅋㅋ, typos, slang) and adapts to your emotions!\n"
            "• **Language Practice:** Roleplay ordering food or talking to your professor with instant grammar coaching!\n\n"
            "Click below to start a friendly chat with Minsu instantly!"
        ),
        "prev_step": 2,
        "action_text": "💬 Chat with Minsu",
        "action_data": "tour_act_buddy"
    }
}


def get_tour_step(step_id: int) -> dict | None:
    return TOUR_STEPS.get(step_id)


def format_tour_message(step_id: int) -> str:
    step = get_tour_step(step_id)
    if not step:
        return ""
    msg = f"✨ **선배의 1분 가이드 (Guided Tour)** ✨\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"**{step['title']}**\n\n"
    msg += f"{step['text']}\n\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "Tap an action to test it, or proceed to the next step:"
    return msg
