# korean_teacher.py — K-Transition OS v3.0
# Dynamic Korean lessons powered by AI quiz generation.
# Static vocab pool is kept as FALLBACK only — live quizzes come from Groq.
# Categories rotate per session to cover all practical areas.

import json
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Load static lesson data (fallback) ────────────────────────────────────────

def _load_lessons() -> dict:
    from config import DATA_DIR
    try:
        with open(DATA_DIR / "korean_lessons.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Could not load korean_lessons.json: %s", e)
        return {}

LESSONS = _load_lessons()


# ── Word of the Day (still deterministic from static pool) ────────────────────

def get_word_of_the_day(day_number: int = None) -> dict | None:
    vocab = LESSONS.get("daily_vocab", [])
    if not vocab:
        return None
    if day_number is None:
        import datetime
        day_number = datetime.date.today().toordinal()
    return vocab[day_number % len(vocab)]


def format_word_of_day(word: dict | None) -> str:
    if not word:
        return "No word available today!"
    msg  = "📚 Word of the Day\n"
    msg += "─────────────────\n"
    msg += f"🇰🇷  {word.get('korean','')}\n"
    msg += f"🔤  {word.get('romanized','')}\n"
    msg += f"💬  {word.get('meaning','')}\n"
    if word.get("example"):
        msg += f"\nExample:\n  {word['example']}\n"
    if word.get("tip"):
        msg += f"\nTip: {word['tip']}"
    return msg


# ── Survival Phrases ──────────────────────────────────────────────────────────

def get_survival_phrases(topic: str = None) -> list:
    phrases = LESSONS.get("survival_phrases", [])
    if topic:
        phrases = [p for p in phrases if p.get("topic", "").lower() == topic.lower()]
    return phrases


def format_phrases_list(phrases: list, title: str = "Survival Phrases") -> str:
    if not phrases:
        return "No phrases found for this topic!"
    msg = f"🗣️  {title}\n{'─'*26}\n\n"
    for i, p in enumerate(phrases[:8], 1):
        msg += f"{i}.  {p.get('korean','')}\n"
        msg += f"    {p.get('romanized','')}\n"
        msg += f"    {p.get('meaning','')}"
        if p.get("situation"):
            msg += f"\n    Use when: {p['situation']}"
        msg += "\n\n"
    return msg.strip()


def get_topic_list() -> list[str]:
    phrases = LESSONS.get("survival_phrases", [])
    return sorted(set(p.get("topic", "general") for p in phrases))


# ── Dynamic AI Quiz ───────────────────────────────────────────────────────────
# Rotating categories ensure variety across sessions.

QUIZ_CATEGORIES = [
    "daily life in Korea",
    "food and restaurants",
    "public transport and navigation",
    "shopping and money",
    "health and pharmacy",
    "housing and apartments",
    "university and campus life",
    "emergency and safety",
    "social etiquette and politeness",
    "government offices and paperwork",
]

_category_index: dict[int, int] = {}   # user_id → current category index


def _next_category(user_id: int) -> str:
    idx = _category_index.get(user_id, random.randint(0, len(QUIZ_CATEGORIES)-1))
    cat = QUIZ_CATEGORIES[idx % len(QUIZ_CATEGORIES)]
    _category_index[user_id] = idx + 1
    return cat


def format_ai_quiz_message(question: dict) -> str:
    """Format the quiz display text (without buttons — those are added in bot.py)."""
    korean = question["korean"]
    return (
        f"🎯 Korean Quiz — Level {question.get('level', 1)}\n\n"
        f"What does  {korean}  ({question['romanized']})  mean?\n\n"
        "Tap the correct answer:"
    )


def format_quiz_result(question: dict, selected_idx: int, correct_idx: int) -> str:
    """Rich feedback after the user answers."""
    is_correct = (selected_idx == correct_idx)
    korean = question["korean"]
    correct = question["correct_meaning"]
    example = question.get("example_sentence", "")
    trans   = question.get("example_translation", "")
    tip     = question.get("tip", "")

    if is_correct:
        msg = f"✅ Correct!\n\n"
        msg += f"🇰🇷  {korean}  =  {correct}\n"
    else:
        all_opts = [question["correct_meaning"]] + question["wrong_answers"]
        # re-shuffle to match original display order via stored data
        chosen = all_opts[selected_idx] if selected_idx < len(all_opts) else "?"
        msg = f"❌ Not quite!\n\n"
        msg += f"🇰🇷  {korean}  =  {correct}\n"
        msg += f"You chose: {chosen}\n"

    if example:
        msg += f"\nExample: {example}"
        if trans:
            msg += f"\n→ {trans}"
    if tip:
        msg += f"\n\n💡 {tip}"

    msg += "\n\n/quiz for another question"
    return msg


# ── Build full quiz options list (correct + 3 wrong, shuffled) ────────────────

def build_quiz_options(question: dict) -> tuple[list[str], int]:
    """Return (shuffled_options, correct_index_in_shuffled_list)."""
    options = [question["correct_meaning"]] + question["wrong_answers"][:3]
    random.shuffle(options)
    correct_idx = options.index(question["correct_meaning"])
    return options, correct_idx


# ── Fallback static quiz (if Groq is unavailable) ────────────────────────────

def get_static_quiz_question() -> dict | None:
    """Pull from the JSON vocab pool as emergency fallback."""
    vocab = LESSONS.get("daily_vocab", [])
    quiz  = LESSONS.get("quiz_pool", vocab)
    if len(quiz) < 4:
        return None
    answer = random.choice(quiz)
    wrong  = random.sample(
        [w["meaning"] for w in quiz if w.get("korean") != answer.get("korean")],
        min(3, len(quiz)-1)
    )
    return {
        "korean":          answer.get("korean", ""),
        "romanized":       answer.get("romanized", ""),
        "correct_meaning": answer.get("meaning", ""),
        "wrong_answers":   wrong,
        "example_sentence": answer.get("example", ""),
        "example_translation": "",
        "tip":             answer.get("tip", ""),
        "level":           1,
        "source":          "static",
    }


# ── Alphabet / Numbers / Pronunciation (static lessons) ───────────────────────

def get_alphabet_lesson() -> str:
    return """🔤 Korean Alphabet (한글) Crash Course

You can learn to READ Korean in 1-2 hours. Here's why:

━━ VOWELS (모음) ━━
아=ah  이=ee  우=oo  에=eh  오=oh  위=wi  외=we

━━ BASIC CONSONANTS (자음) ━━
ㄱ=g/k  ㄴ=n  ㄷ=d/t  ㄹ=r/l  ㅁ=m
ㅂ=b/p  ㅅ=s  ㅇ=silent/ng  ㅈ=j  ㅎ=h

━━ HOW SYLLABLE BLOCKS WORK ━━
Each block = consonant + vowel (+ optional final consonant)
한 = ㅎ(h) + ㅏ(a) + ㄴ(n) = "han"
국 = ㄱ(g) + ㅜ(u) + ㄱ(k) = "guk"
→ 한국 = Hanguk = Korea 🇰🇷

━━ TRY IT NOW ━━
Read: 안녕 = ㅇ+ㅏ+ㄴ / ㄴ+ㅕ+ㅇ = "an-nyeong" = Hello! ✅

💡 Apps: Drops or Duolingo for interactive practice.
You'll be reading Korean signs within 2 days!"""


def get_numbers_lesson() -> str:
    return """🔢 Korean Numbers

Korea uses TWO systems:

━━ SINO-KOREAN (money, dates, phone, floors) ━━
1=일 2=이 3=삼 4=사 5=오 6=육 7=칠 8=팔 9=구 10=십
100=백  1,000=천  10,000=만 ← count in units of 10,000!

Money: 30,000원 = 삼만원 (sam-man-won)

━━ NATIVE KOREAN (objects, age, hours) ━━
1=하나 2=둘 3=셋 4=넷 5=다섯 6=여섯 7=일곱 8=여덟 9=아홉 10=열

Age: "I'm 22" = 스물두 살이에요

━━ MOST USEFUL NOW ━━
얼마예요? = How much?
천원=1,000  오천=5,000  만원=10,000  이만=20,000

💡 Practice: say the price in Korean before you pay at a convenience store!"""


def get_pronunciation_tips() -> str:
    return """🎵 Korean Pronunciation Tips

━━ TRICKY SOUNDS ━━
ㄹ = halfway between R and L. Tap your tongue quickly.
ㅓ (eo) = "uh" not "eo". Seoul = "Suh-ul" not "Seh-oul"
Tense consonants ㄲ ㄸ ㅃ ㅆ ㅉ = say with throat tension

━━ RHYTHM ━━
Korean is FLAT — no rising tone for questions.
Speak in steady rhythm, equal stress on each syllable.

━━ COMMON MISTAKES ━━
❌ 감사합니다 → "gam-SA-ham-ni-DA"
✅ 감사합니다 → flat, each syllable equal

❌ 안녕하세요 → "an-NYONG-hassy-o"
✅ 안녕하세요 → "an-nyeong-ha-se-yo"

━━ FASTEST IMPROVEMENT ━━
1. YouTube: "Talk To Me In Korean" (TTMIK)
2. Watch K-dramas with subtitles
3. Language exchange apps: HelloTalk, Tandem
4. Ask your uni about 언어교환 (language exchange) programs"""


def search_vocab_and_phrases(query: str) -> str:
    """Search both vocabulary and survival phrases for a query word."""
    query = query.lower().strip()
    results = []

    # Search daily_vocab
    vocab = LESSONS.get("daily_vocab", [])
    for word in vocab:
        if (query in word.get("korean", "").lower() or
            query in word.get("meaning", "").lower() or
            query in word.get("romanized", "").lower()):
            results.append({
                "type": "Vocabulary",
                "korean": word.get("korean", ""),
                "romanized": word.get("romanized", ""),
                "meaning": word.get("meaning", ""),
                "example": word.get("example", ""),
                "tip": word.get("tip", "")
            })

    # Search survival_phrases
    phrases = LESSONS.get("survival_phrases", [])
    for p in phrases:
        if (query in p.get("korean", "").lower() or
            query in p.get("meaning", "").lower() or
            query in p.get("romanized", "").lower()):
            results.append({
                "type": f"Phrase (Topic: {p.get('topic', 'General').title()})",
                "korean": p.get("korean", ""),
                "romanized": p.get("romanized", ""),
                "meaning": p.get("meaning", ""),
                "example": p.get("situation", "")
            })

    if not results:
        return f"🔍 No Korean words or phrases found matching: '{query}'\nTry search terms like 'hospital', 'food', '약국', 'hello'."

    msg = f"🔍 Search Results for '{query}':\n\n"
    for r in results[:5]:  # limit to top 5 results for neatness
        msg += f"📌 {r['type']}\n"
        msg += f"🇰🇷  {r['korean']}\n"
        msg += f"🔤  {r['romanized']}\n"
        msg += f"💬  {r['meaning']}\n"
        if r.get("example"):
            msg += f"💡  {r['example']}\n"
        if r.get("tip"):
            msg += f"📝  {r['tip']}\n"
        msg += "─────────────────\n\n"

    if len(results) > 5:
        msg += f"And {len(results) - 5} more results. Try a more specific search!"
    return msg.strip()
