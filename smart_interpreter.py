# smart_interpreter.py — K-Transition OS v5.0
# KILLER FEATURE #2: AI-powered Cultural Interpreter
# Not just translation — CULTURAL INTELLIGENCE
# Understands formality levels, what NOT to say, hidden meanings
# User sends Korean/English text → gets full cultural breakdown
# Like having a Korean friend who explains EVERYTHING

import asyncio
import logging

logger = logging.getLogger(__name__)

INTERPRETER_SYSTEM = """You are the Cultural Interpreter for K-Transition OS — an AI that explains the culture behind Korean words.
You are NOT a general survival bot, you are strictly a language and culture interpreter.

USER'S KOREAN LEVEL: {level}
USER'S CONTEXT: Student at {university} in {city}

WHEN THE USER SENDS KOREAN TEXT:
Provide a clear English explanation, pronunciation, formality level, and cultural context.

WHEN THE USER SENDS ENGLISH TEXT:
Provide the Korean translation, pronunciation, formality level breakdown (casual/polite/formal), and cultural warnings.

RULES:
1. ALWAYS respond in the SAME language the user used to ask the question. If they ask in English, explain in English.
2. NEVER use Markdown tables (`|` or `---`). The platform does not support tables. Use bullet points or indented lists instead.
3. NEVER append emergency numbers (112, 119) or massive general survival guides. Stick strictly to interpreting the phrase or situation requested.
4. Keep the response concise, conversational, and under 200 words.
"""

# Quick phrase categories for /interpret menu
PHRASE_CATEGORIES = {
    "survive": {
        "title": "🆘 Survival Phrases",
        "phrases": [
            ("Help!", "도와주세요!", "do-wa-ju-se-yo"),
            ("How much?", "얼마예요?", "eol-ma-ye-yo"),
            ("Where is...?", "...어디예요?", "...eo-di-ye-yo"),
            ("I don't understand", "이해 못 해요", "i-hae mot hae-yo"),
            ("Please speak slowly", "천천히 말해주세요", "cheon-cheon-hi mal-hae-ju-se-yo"),
            ("One more time please", "다시 한번 말해주세요", "da-si han-beon mal-hae-ju-se-yo"),
        ]
    },
    "food": {
        "title": "🍽️ Food Ordering",
        "phrases": [
            ("This one please", "이거 주세요", "i-geo ju-se-yo"),
            ("Is this spicy?", "이거 매워요?", "i-geo mae-wo-yo"),
            ("No pork please", "돼지고기 빼주세요", "dwae-ji-go-gi bbae-ju-se-yo"),
            ("Is this halal?", "할랄 음식이에요?", "hal-lal eum-si-gi-e-yo"),
            ("Delicious!", "맛있어요!", "ma-si-sseo-yo"),
            ("The bill please", "계산이요", "gye-sa-ni-yo"),
        ]
    },
    "social": {
        "title": "🤝 Social Phrases",
        "phrases": [
            ("Nice to meet you", "만나서 반갑습니다", "man-na-seo ban-gap-seum-ni-da"),
            ("What year were you born?", "몇 년생이에요?", "myeot nyeon-saeng-i-e-yo"),
            ("Let's eat together!", "같이 밥 먹자!", "ga-chi bap meok-ja"),
            ("Thank you so much", "정말 감사합니다", "jeong-mal gam-sa-ham-ni-da"),
            ("I'm from [country]", "[나라]에서 왔어요", "[na-ra]-e-seo wa-sseo-yo"),
            ("Can we be friends?", "우리 친구 하자!", "u-ri chin-gu ha-ja"),
        ]
    },
    "university": {
        "title": "🎓 University Phrases",
        "phrases": [
            ("Professor, I have a question", "교수님, 질문 있습니다", "gyo-su-nim, jil-mun it-seum-ni-da"),
            ("When is the deadline?", "마감일이 언제예요?", "ma-gam-il-i eon-je-ye-yo"),
            ("Can I submit late?", "늦게 제출해도 될까요?", "neut-ge je-chul-hae-do dwel-kka-yo"),
            ("Where is the library?", "도서관이 어디예요?", "do-seo-gwan-i eo-di-ye-yo"),
            ("I'm a exchange student", "교환학생이에요", "gyo-hwan-hak-saeng-i-e-yo"),
            ("Where do I print?", "프린트 어디서 해요?", "peu-rin-teu eo-di-seo hae-yo"),
        ]
    },
    "emergency": {
        "title": "🚨 Emergency Phrases",
        "phrases": [
            ("Call the police!", "경찰 불러주세요!", "gyeong-chal bul-leo-ju-se-yo"),
            ("I need a doctor", "의사 선생님이 필요해요", "ui-sa seon-saeng-nim-i pil-yo-hae-yo"),
            ("I'm lost", "길을 잃었어요", "gi-reul il-eot-seo-yo"),
            ("It hurts here", "여기가 아파요", "yeo-gi-ga a-pa-yo"),
            ("Please call English interpreter", "영어 통역사 불러주세요", "yeong-eo tong-yeok-sa bul-leo-ju-se-yo"),
            ("I'm having an emergency", "긴급 상황이에요", "gin-geup sang-hwang-i-e-yo"),
        ]
    },
    "shopping": {
        "title": "🛍️ Shopping Phrases",
        "phrases": [
            ("Do you have this in size M?", "M 사이즈 있어요?", "em sa-i-jeu it-seo-yo"),
            ("Can I try it on?", "입어봐도 될까요?", "i-beo-bwa-do dwel-kka-yo"),
            ("Too expensive!", "너무 비싸요!", "neo-mu bi-ssa-yo"),
            ("Can you give a discount?", "깎아주세요", "kka-kka-ju-se-yo"),
            ("I'll take this", "이거 살게요", "i-geo sal-ge-yo"),
            ("Where is Daiso?", "다이소 어디예요?", "da-i-so eo-di-ye-yo"),
        ]
    },
}

# Formality decoder — common mistakes
FORMALITY_GUIDE = {
    "반말": "Casual/informal — ONLY use with same-age friends or younger people you're close to",
    "존댓말": "Polite speech — default for strangers, older people, service workers",
    "격식체": "Formal speech — professors, bosses, official situations, emails",
}


async def interpret_text(text, user_info=None, direction="auto"):
    """AI-powered cultural interpretation of text."""
    from ai_brain import call_groq
    
    uni = (user_info or {}).get("university", "a Korean university")
    city = (user_info or {}).get("city", "Korea")
    progress = {}
    try:
        from memory import get_progress
        progress = get_progress((user_info or {}).get("user_id", 0))
    except Exception:
        pass
    level = progress.get("quiz_level", 1)
    level_names = {1: "Total Beginner", 2: "Elementary", 3: "Intermediate", 4: "Upper-Intermediate", 5: "Advanced"}
    
    system = INTERPRETER_SYSTEM.format(
        level=level_names.get(level, "Beginner"),
        university=uni, city=city
    )
    
    if direction == "to_korean":
        user_msg = f"Translate this to Korean with full cultural breakdown: {text}"
    elif direction == "to_english":
        user_msg = f"Translate this Korean to English with full cultural breakdown: {text}"
    else:
        user_msg = f"Interpret this with full cultural context: {text}"
    
    messages = [{"role": "user", "content": user_msg}]
    
    try:
        response = await asyncio.to_thread(call_groq, messages, system)
        if response:
            return response
    except Exception as e:
        logger.error(f"Interpreter failed: {e}")
    
    return (
        "🔄 Interpreter temporarily offline.\n\n"
        "Quick phrases: /interpret menu\n"
        "Try again in a moment!"
    )


def get_phrase_list(category=None):
    """Get formatted phrase list for a category."""
    if category and category in PHRASE_CATEGORIES:
        cat = PHRASE_CATEGORIES[category]
        msg = f"{cat['title']}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for eng, kor, roman in cat["phrases"]:
            msg += f"🇬🇧 {eng}\n🇰🇷 {kor}\n🔤 {roman}\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 /interpret [any phrase] — Get AI cultural breakdown"
        return msg
    
    # Show all categories
    msg = "🔮 Smart Interpreter\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "Not just translation — CULTURAL INTELLIGENCE\n\n"
    msg += "📖 Phrase Books:\n"
    for key, cat in PHRASE_CATEGORIES.items():
        msg += f"  /interpret {key} — {cat['title']}\n"
    msg += "\n🔄 Live Interpreter:\n"
    msg += "  /interpret [Korean text] — Translate + explain\n"
    msg += "  /interpret [English text] — Get Korean version\n"
    msg += "  /interpret how do I say [situation] — Situational phrase\n\n"
    msg += "💡 Example: /interpret 아 진짜요?\n"
    msg += "💡 Example: /interpret I need to tell my professor I'll be late"
    return msg


def get_formality_guide():
    """Return the formality level guide."""
    msg = "📊 Korean Formality Levels\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "Korean has 3 main speech levels:\n\n"
    for level, desc in FORMALITY_GUIDE.items():
        msg += f"🔹 {level}: {desc}\n\n"
    msg += "Example — 'Thank you':\n"
    msg += "  격식체: 감사합니다 (to professor)\n"
    msg += "  존댓말: 고마워요 (to older acquaintance)\n"
    msg += "  반말: 고마워 (to close friend)\n\n"
    msg += "⚠️ Using 반말 to an older person = INSTANT offense\n"
    msg += "💡 When in doubt, use 존댓말!"
    return msg
