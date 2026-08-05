# culture_sim.py — K-Transition OS v5.0
# Culture Shock Simulator
# Interactive AI-driven choose-your-adventure scenarios
# User faces REAL Korean situations, makes choices, gets scored
# Wrong choices = consequences (like in real life)
# Like a survival RPG but for Korean culture

import asyncio
import random
import logging

logger = logging.getLogger(__name__)

# ── Scenario Bank ────────────────────────────────────────────────────────────
# Each scenario: situation, 3 choices, consequences, cultural lesson

SCENARIOS = [
    {
        "id": "professor_email",
        "title": "📧 Email to Professor",
        "situation": "You need to email your Korean professor to ask for a deadline extension. You've never emailed them before.",
        "choices": [
            {"text": "Hey prof, can I get an extension? Thanks!", "outcome": "BAD", "consequence": "😬 Professor is offended. In Korean academia, casual language to professors is a HUGE disrespect. They might ignore your email entirely.", "score": -20},
            {"text": "교수님, 안녕하세요. [Student ID + Name]입니다. 과제 마감일 연장을 부탁드려도 될까요? 죄송합니다.", "outcome": "PERFECT", "consequence": "👏 Professor appreciates your effort. Using 존댓말 (formal speech) + your student ID + apologetic tone = exactly right in Korean culture.", "score": 30},
            {"text": "Dear Professor, I hope this email finds you well. Could I request an extension?", "outcome": "OK", "consequence": "🙂 Acceptable, but Korean professors prefer Korean-style emails. Adding your student ID and using some Korean would impress more.", "score": 10},
        ],
        "lesson": "💡 Korean email to professors: Always use 교수님, include 학번(student ID) + 이름(name), use formal language, and apologize for the inconvenience (불편을 드려 죄송합니다)."
    },
    {
        "id": "noisy_neighbor",
        "title": "🔊 Noisy Neighbor at 11 PM",
        "situation": "It's 11 PM. Your Korean neighbor is playing loud music. You have an exam tomorrow. What do you do?",
        "choices": [
            {"text": "Bang on their door and tell them to shut up", "outcome": "BAD", "consequence": "😰 Direct confrontation is considered very aggressive in Korea. Your neighbor might call the police ON YOU. 층간소음 complaints should go through proper channels.", "score": -20},
            {"text": "Call the 층간소음 이웃사이센터 (1661-2642) or tell your RA/관리실", "outcome": "PERFECT", "consequence": "✅ Smart move! Korea has an official noise complaint center. Your dorm's 관리실 (management office) can mediate without direct confrontation.", "score": 30},
            {"text": "Put in earplugs and suffer in silence", "outcome": "OK", "consequence": "😐 You survived, but you don't have to! Quiet hours (10PM-7AM) are legally enforced in Korea. You have rights.", "score": 5},
        ],
        "lesson": "💡 층간소음 (floor noise) is SERIOUS in Korea. Call 1661-2642 for official mediation. After 10PM, you have legal backing. Never confront directly — always use 관리실 or official channels."
    },
    {
        "id": "restaurant_bill",
        "title": "💰 Restaurant Bill with Korean Friends",
        "situation": "You went to dinner with 3 Korean friends. The bill arrives. In your country, you'd split the bill. What happens in Korea?",
        "choices": [
            {"text": "Calculate each person's share and ask everyone to pay their part", "outcome": "BAD", "consequence": "😅 Awkward! In Korean 회식 culture, splitting the bill precisely is seen as petty (쩨쩨한). Usually one person pays, or you do 'Dutch pay' (더치페이) only when agreed in advance.", "score": -10},
            {"text": "Offer to pay for everyone (or at least fight to pay)", "outcome": "PERFECT", "consequence": "🎉 THIS is Korean culture! The '계산 전쟁' (bill fight) is a real thing. Offering to pay shows generosity. Even if someone else pays, your offer is deeply respected. Next time, someone else will treat you.", "score": 30},
            {"text": "Wait silently and see what happens", "outcome": "OK", "consequence": "🤷 Not terrible, but you missed a social cue. In Korea, showing willingness to pay (even if you can't afford it) builds social bonds. At minimum, say '제가 낼게요!' (I'll pay!)", "score": 5},
        ],
        "lesson": "💡 Korean '밥 문화' (meal culture): The oldest/most senior person usually pays. Among friends, people 'fight' to pay. If someone treats you, remember to treat them back next time. This is 정 (Korean emotional bonds)."
    },
    {
        "id": "taxi_long_route",
        "title": "🚖 Suspicious Taxi Route",
        "situation": "You're in a taxi going from your university to Seoul Station. The driver seems to be taking a longer route than what Kakao Map shows. What do you do?",
        "choices": [
            {"text": "Stay quiet — maybe they know a better route?", "outcome": "BAD", "consequence": "💸 You just got scammed! Some taxi drivers take longer routes for foreign-looking passengers. Always have Kakao Map open and visible.", "score": -15},
            {"text": "Show your phone with Kakao Map and politely say '카카오맵에서는 이 길이 더 빨라요' (Kakao Map says this route is faster)", "outcome": "PERFECT", "consequence": "👍 Perfect! Showing the map is non-confrontational but makes it clear you're aware. Most drivers will correct course. If they don't, note the taxi number and report to 120.", "score": 30},
            {"text": "Yell 'STOP! You're cheating me!' and refuse to pay", "outcome": "BAD", "consequence": "😤 Dangerous escalation. While the driver may be wrong, refusing to pay is illegal. Better: pay, then report the taxi number + license plate to 120 (Seoul Dasan call center) or the taxi company.", "score": -20},
        ],
        "lesson": "💡 Taxi tip: ALWAYS have Kakao Map open and visible when riding. Scammers target people who look lost. Know your route. If overcharged: pay first, then report the 택시번호 (taxi number on the receipt) to 120."
    },
    {
        "id": "age_question",
        "title": "🎂 Korean Age Question",
        "situation": "You just met a new Korean student at university. Their first question: '몇 년생이에요?' (What year were you born?). Why are they asking this?",
        "choices": [
            {"text": "They're being nosy/rude — ignore it", "outcome": "BAD", "consequence": "😬 You just missed a crucial Korean social ritual! Age determines EVERYTHING: language formality, who pays, who pours drinks, who says hello first.", "score": -15},
            {"text": "Answer honestly — they're figuring out if you're 선배 or 후배 to know how to talk to you", "outcome": "PERFECT", "consequence": "✅ Exactly! In Korea, age = social hierarchy. If you're older → they use 존댓말 (formal) to you. Same age → you're 친구! Younger → you get respect as 선배. This single answer shapes your entire relationship.", "score": 30},
            {"text": "Say 'I don't share personal info' — it's private", "outcome": "BAD", "consequence": "😕 In Western culture, age is private. In Korea, it's ESSENTIAL social info. Refusing feels like you're rejecting the friendship. They literally can't speak to you properly without knowing.", "score": -10},
        ],
        "lesson": "💡 Korean age hierarchy: 선배/후배 (senior/junior) system governs ALL social interactions. Answering '몇 년생?' is not rude — it's them trying to figure out how to treat you with RESPECT."
    },
    {
        "id": "apartment_deposit",
        "title": "🏠 Apartment Deposit Trap",
        "situation": "You found a great apartment. The landlord says: 'Pay ₩5,000,000 deposit now, we'll sign the contract next week.' What do you do?",
        "choices": [
            {"text": "Pay immediately — the apartment is perfect and might be taken!", "outcome": "BAD", "consequence": "🔴 SCAM ALERT! NEVER pay before signing the contract. Once money is transferred without a contract, you have ZERO legal protection. This is the #1 housing scam for foreigners in Korea.", "score": -30},
            {"text": "Say: 'I'll pay when we sign the contract. Can we sign today?'", "outcome": "PERFECT", "consequence": "✅ Smart! Always: 1) Check 등기부등본 at iros.go.kr first 2) Sign contract THEN pay 3) Go to 주민센터 for 확정일자 within 14 days. This protects your deposit legally.", "score": 30},
            {"text": "Ask a Korean friend to call the landlord and negotiate", "outcome": "OK", "consequence": "🙂 Good instinct having Korean help! But the core rule still applies: NEVER pay before contract. Your friend can help verify the 등기부등본 and negotiate terms.", "score": 15},
        ],
        "lesson": "💡 Housing golden rule: 등기부등본 check (iros.go.kr, ₩700) → Sign contract → THEN pay → 주민센터 for 전입신고 + 확정일자 within 14 days. Skip ANY step = risk losing everything."
    },
    {
        "id": "drinking_culture",
        "title": "🍺 Korean Drinking Culture (회식)",
        "situation": "Your Korean lab senior pours you soju. You don't drink alcohol (for religious/personal reasons). What do you do?",
        "choices": [
            {"text": "Accept and pretend to drink, then secretly pour it out", "outcome": "OK", "consequence": "😓 Survivable but stressful. You shouldn't have to hide your beliefs. Korean culture has evolved — most people respect non-drinkers now.", "score": 5},
            {"text": "Politely say '저는 술을 안 마셔요' (I don't drink) and ask for 음료수 (soft drink) instead. Turn your cup upside down.", "outcome": "PERFECT", "consequence": "✅ Perfect response! Most Koreans respect this completely. Turning your cup = clear signal. Many young Koreans are also reducing drinking. You can still participate in 회식 vibes without alcohol!", "score": 30},
            {"text": "Leave the dinner entirely", "outcome": "BAD", "consequence": "😬 Leaving a 회식 early (especially as the youngest) is considered very rude. 회식 is about team bonding, not just drinking. You can absolutely stay and enjoy the food without alcohol.", "score": -15},
        ],
        "lesson": "💡 회식 (team dinner) tip: You DON'T have to drink. '저는 술을 안 마셔요' is completely accepted. If someone insists, smile and say '건강 때문에요' (for health reasons). Nobody will push further."
    },
    {
        "id": "subway_seat",
        "title": "🚇 Subway Seat Dilemma",
        "situation": "The subway is crowded. You see an empty seat in the 'priority section' (노약자석). You're exhausted after a long day. What do you do?",
        "choices": [
            {"text": "Sit down — it's empty and you're tired", "outcome": "BAD", "consequence": "📸 Koreans might photograph you and post it online. 노약자석 (priority seats) are SACRED in Korea — even if empty, young people are heavily judged for sitting there. This is a famous cultural landmine.", "score": -25},
            {"text": "Stand next to it and wait for a regular seat to open", "outcome": "PERFECT", "consequence": "✅ This is the Korean way! Even if the priority seats are empty the entire ride, young people stand. It shows respect for 어르신 (elders). You'll notice Korean students NEVER sit there.", "score": 30},
            {"text": "Sit but immediately stand if an elderly person boards", "outcome": "OK", "consequence": "⚠️ Better than staying seated, but you'll still get judgmental looks while sitting. The safest move is to never sit in 노약자석 at all unless you're pregnant/disabled/elderly.", "score": 0},
        ],
        "lesson": "💡 노약자석 (priority seats) = DO NOT SIT even if empty. This is one of the biggest cultural shocks for foreigners. Regular seats → give up for elderly. Priority seats → never sit if you're young and healthy."
    },
]

SIM_SYSTEM_PROMPT = """You are the Culture Shock Simulator AI for K-Transition OS.
You create INTERACTIVE Korean cultural scenarios that test the user's knowledge.

Generate a scenario in this EXACT format:
🎭 [Scenario Title]

[2-3 sentence situation description — make it vivid and realistic]

What do you do?

A) [Choice A — could be good or bad]
B) [Choice B — could be good or bad]  
C) [Choice C — could be good or bad]

Reply with A, B, or C!

RULES:
1. Scenarios must be REALISTIC situations international students ACTUALLY face in Korea
2. One choice should be the Korean-culturally-correct answer
3. One choice should be a common Western-culture mistake
4. One choice should be somewhere in between
5. Include Korean terms with translations
6. Topic: {topic}
7. Make it engaging — like a game, not a lecture
8. The user's profile: studying at {university} in {city}"""

SIM_JUDGE_PROMPT = """You are judging a Culture Shock Simulator response.
The scenario was: {scenario}
The user chose: {choice}

Respond with:
1. Whether their choice was GOOD (✅), OKAY (🙂), or BAD (❌)
2. What would actually happen in Korea if they did this (be specific and vivid)
3. The CORRECT Korean cultural approach with Korean terms
4. A "Cultural Survival Score" from -30 to +30
5. One memorable tip they'll never forget

Keep it fun, not preachy. Like a friend telling them "bro, here's what would actually happen..."
Be SHORT — max 150 words."""


def get_random_scenario():
    """Get a random pre-built scenario."""
    return random.choice(SCENARIOS)


def format_scenario(scenario):
    """Format a scenario for display."""
    msg = f"🎭 Culture Shock Simulator\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"**{scenario['title']}**\n\n"
    msg += f"{scenario['situation']}\n\n"
    msg += "What do you do?\n\n"
    
    labels = ["A", "B", "C"]
    for i, choice in enumerate(scenario["choices"]):
        msg += f"{labels[i]}) {choice['text']}\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "Reply with A, B, or C!"
    return msg


def evaluate_choice(scenario, choice_letter):
    """Evaluate the user's choice and return result."""
    idx = {"a": 0, "b": 1, "c": 2}.get(choice_letter.lower(), -1)
    if idx < 0 or idx >= len(scenario["choices"]):
        return None

    chosen = scenario["choices"][idx]
    outcome = chosen["outcome"]
    
    icons = {"PERFECT": "✅", "OK": "🙂", "BAD": "❌"}
    labels = {"PERFECT": "PERFECT!", "OK": "Not bad...", "BAD": "Oof!"}
    
    msg = f"{icons.get(outcome, '🤔')} {labels.get(outcome, '...')}\n\n"
    msg += f"{chosen['consequence']}\n\n"
    msg += f"📊 Score: {'+' if chosen['score'] > 0 else ''}{chosen['score']} points\n\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{scenario['lesson']}\n\n"
    msg += "🎮 /simulate — Try another scenario!\n"
    msg += "🧠 /simulate topic — Choose a topic"
    
    return msg, chosen["score"]


async def generate_ai_scenario(topic="random", user_info=None):
    """Generate a dynamic AI scenario based on topic."""
    from ai_brain import call_groq
    
    uni = (user_info or {}).get("university", "a Korean university")
    city = (user_info or {}).get("city", "Korea")
    
    system = SIM_SYSTEM_PROMPT.format(
        topic=topic, university=uni, city=city
    )
    messages = [{"role": "user", "content": f"Generate a culture shock scenario about: {topic}"}]
    
    try:
        response = await asyncio.to_thread(call_groq, messages, system)
        if response:
            return response
    except Exception as e:
        logger.error(f"Culture sim AI failed: {e}")
    
    # Fallback to pre-built
    scenario = get_random_scenario()
    return format_scenario(scenario)


def get_scenario_topics():
    """Return available simulation topics."""
    return (
        "🎭 Culture Shock Simulator — Topics\n\n"
        "Choose a topic or get a random scenario:\n\n"
        "🍽️ /simulate food — Dining etiquette\n"
        "🏠 /simulate housing — Apartment survival\n"
        "🎓 /simulate university — Academic culture\n"
        "🚇 /simulate transport — Getting around\n"
        "💼 /simulate workplace — Office/lab culture\n"
        "🍺 /simulate social — Social situations\n"
        "💰 /simulate money — Financial situations\n"
        "🏥 /simulate emergency — Emergency responses\n"
        "🎲 /simulate — Random scenario\n\n"
        "Each scenario tests your Korea survival IQ!\n"
        "Your choices have CONSEQUENCES 👀"
    )


async def evaluate_ai_choice(scenario_text, choice_letter, user_info=None):
    """Evaluate user's choice for AI-generated scenario using LLM."""
    from ai_brain import call_groq
    import re
    import asyncio

    system = SIM_JUDGE_PROMPT.format(
        scenario=scenario_text,
        choice=choice_letter.upper()
    )
    messages = [{"role": "user", "content": f"The user chose: {choice_letter.upper()}. Evaluate this choice."}]

    try:
        response = await asyncio.to_thread(call_groq, messages, system)
        if response:
            score_match = re.search(r"score[:\s]*([+-]?\d+)", response.lower())
            score = 10  # default fallback score
            if score_match:
                try:
                    score = int(score_match.group(1))
                except ValueError:
                    pass

            response += "\n\n🎮 /simulate — Try another scenario!\n"
            response += "🧠 /simulate topic — Choose a topic"

            return response, score
    except Exception as e:
        logger.error(f"Culture sim AI judge failed: {e}")

    return None
