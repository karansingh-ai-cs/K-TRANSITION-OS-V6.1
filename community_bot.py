# community_bot.py — K-Transition OS v4.0
# ═══════════════════════════════════════════════════════════
# COMMUNITY PLATFORM — Group Management System
# ═══════════════════════════════════════════════════════════
#
# Architecture:
#   One Telegram supergroup with Forum mode (Topics enabled)
#   Bot manages topics, anonymous posting, welcome, moderation
#
# Topics in the group:
#   📢 Announcements      — bot-only, important updates
#   💬 General Chat       — anything goes
#   🏠 Housing Help       — rent, contracts, scams
#   🍜 Food & Halal       — food safety, halal spots
#   🪪 Visa & ARC         — bureaucracy support
#   💙 Support (Anonymous)— mental health, anonymous option
#   🇰🇷 Language Exchange  — Korean practice, correction
#   🎓 Future Students    — aspiring GKS scholars Q&A (SEED AUDIENCE)
#   📦 Marketplace        — buy/sell/free stuff among students
#   🏆 Weekly Challenge   — gamified engagement
#   🎓 [University]       — per-university threads (created dynamically)
#
# Anonymous posting:
#   User sends /anon [topic] [message] to bot in DM
#   Bot posts as "🎭 Anonymous Student #N" in the correct topic
#   Bot privately stores mapping (for moderation only)
#
# Seed audience strategy:
#   Future students (aspiring GKS scholars) are the FIRST users.
#   They ask questions → bot answers from knowledge base.
#   Present students join → answer real questions.
#   Flywheel: more Q&A → more value → more students.
#
# Weekly challenge system:
#   Every Monday bot posts a challenge in #weekly-challenge
#   Students report completion → earn points → leaderboard

import json
import logging
import asyncio
import random
from datetime import datetime, UTC, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# TOPIC DEFINITIONS
# ══════════════════════════════════════════════════════════════

TOPICS = {
    "announcements":    {"name": "📢 Announcements",       "description": "Important updates from the bot and admins"},
    "general":          {"name": "💬 General Chat",         "description": "Anything about life in Korea"},
    "housing":          {"name": "🏠 Housing Help",         "description": "Rent, contracts, landlords, scams"},
    "food":             {"name": "🍜 Food & Halal",          "description": "Food safety, halal spots, cooking"},
    "visa":             {"name": "🪪 Visa & ARC",            "description": "Visa types, ARC process, immigration"},
    "support":          {"name": "💙 Support",               "description": "Mental health, anonymous OK, no judgment"},
    "language":         {"name": "🇰🇷 Language Exchange",    "description": "Korean practice, correction, vocab"},
    "future_students":  {"name": "🎓 Future Students Q&A",  "description": "Aspiring GKS scholars — ask anything"},
    "marketplace":      {"name": "📦 Marketplace",           "description": "Buy/sell/free items among students"},
    "challenge":        {"name": "🏆 Weekly Challenge",      "description": "Weekly missions — earn points"},
}

# Map keywords → topic
TOPIC_ROUTER = {
    "housing":    ["house", "rent", "deposit", "landlord", "보증금", "계약", "lease", "apartment", "room", "gosiwon"],
    "food":       ["food", "eat", "halal", "haram", "pork", "restaurant", "hungry", "allergy", "vegan", "vegetarian"],
    "visa":       ["visa", "arc", "immigration", "d-2", "d-4", "hikorea", "overstay", "extension", "출입국"],
    "support":    ["lonely", "depressed", "anxious", "homesick", "struggling", "mental", "sad", "힘들", "외롭"],
    "language":   ["korean", "word", "phrase", "translation", "topik", "pronunciation", "한국어", "배우"],
    "future_students": ["applying", "gks", "scholarship", "before coming", "requirements", "how to apply"],
}

# ══════════════════════════════════════════════════════════════
# WEEKLY CHALLENGES
# ══════════════════════════════════════════════════════════════

WEEKLY_CHALLENGES = [
    {
        "id": "wc_01",
        "title": "🇰🇷 Korean Only at One Meal",
        "description": "Order food OR buy something at a store using ONLY Korean. No English backup.",
        "report_phrase": "I ordered in Korean! Here's what happened:",
        "points": 30,
        "category": "language",
    },
    {
        "id": "wc_02",
        "title": "🆘 Emergency-Ready Check",
        "description": "Save 112, 119, and 1345 in your phone AND learn to say '도와주세요' correctly.",
        "report_phrase": "Saved the numbers + practiced the phrase!",
        "points": 15,
        "category": "safety",
    },
    {
        "id": "wc_03",
        "title": "🏙️ Neighborhood Discovery",
        "description": "Find and visit one place you've never been to within 1km of where you live.",
        "report_phrase": "Found something new near me:",
        "points": 20,
        "category": "explore",
    },
    {
        "id": "wc_04",
        "title": "💬 Korean Conversation",
        "description": "Have a real conversation with a Korean person (not teacher) — 5+ exchanges.",
        "report_phrase": "I had a real conversation in Korean! It went:",
        "points": 40,
        "category": "social",
    },
    {
        "id": "wc_05",
        "title": "🍜 Try One New Korean Food",
        "description": "Eat something you've never tried before. Bonus if you can name it in Korean.",
        "report_phrase": "I tried 먹었어요! Here's what I thought:",
        "points": 15,
        "category": "culture",
    },
    {
        "id": "wc_06",
        "title": "📚 Teach a Future Student",
        "description": "In the #future-students topic, answer ONE question from someone who hasn't arrived yet.",
        "report_phrase": "I helped a future student with:",
        "points": 35,
        "category": "community",
    },
    {
        "id": "wc_07",
        "title": "💰 Budget Snapshot",
        "description": "Calculate roughly what you spent this week. Share the breakdown (no exact amounts needed).",
        "report_phrase": "My weekly spending breakdown:",
        "points": 20,
        "category": "financial",
    },
    {
        "id": "wc_08",
        "title": "🏛️ Bureaucracy Win",
        "description": "Complete any official task: ARC appointment, bank, 주민센터, NHIS inquiry.",
        "report_phrase": "I conquered Korean bureaucracy! I did:",
        "points": 45,
        "category": "admin",
    },
    {
        "id": "wc_09",
        "title": "🧘 Wellbeing Check",
        "description": "Spend 10 minutes doing something purely for your mental wellbeing. No phone.",
        "report_phrase": "I took care of myself by:",
        "points": 20,
        "category": "mental",
    },
    {
        "id": "wc_10",
        "title": "🤝 Korean Friend Challenge",
        "description": "Exchange contact details with a Korean student you've never spoken to before.",
        "report_phrase": "I met a new Korean friend! Context:",
        "points": 50,
        "category": "social",
    },
]


def get_this_weeks_challenge() -> dict:
    """Deterministic: same challenge all week, rotates weekly."""
    week_number = datetime.now(UTC).isocalendar()[1]
    return WEEKLY_CHALLENGES[week_number % len(WEEKLY_CHALLENGES)]


def format_weekly_challenge(challenge: dict, leaderboard: list = None) -> str:
    week_str = datetime.now(UTC).strftime("Week of %B %d, %Y")
    msg  = f"🏆 Weekly Challenge — {week_str}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{challenge['title']}\n\n"
    msg += f"📋 {challenge['description']}\n\n"
    msg += f"📝 To complete: use /challenge done in the group\n"
    msg += f"   Then share: \"{challenge['report_phrase']}\"\n\n"
    msg += f"⭐ Reward: {challenge['points']} community points\n\n"

    if leaderboard:
        msg += "━━ This Week's Leaders ━━\n"
        for i, entry in enumerate(leaderboard[:5], 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
            msg += f"{medal} {entry['name']} — {entry['points']} pts\n"

    return msg


# ══════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════

from db import get_conn as _get_conn


def setup_community_tables():
    with _get_conn() as conn:
        # Group registrations (which groups the bot manages)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS community_groups (
                group_id     INTEGER PRIMARY KEY,
                group_name   TEXT,
                university   TEXT DEFAULT '',
                topic_ids    TEXT DEFAULT '{}',
                created_at   TEXT
            )
        """)
        # Anonymous post mapping (bot knows sender, group doesn't)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS anon_posts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                group_id     INTEGER,
                topic_id     INTEGER DEFAULT 0,
                message_id   INTEGER,
                anon_number  INTEGER,
                timestamp    TEXT
            )
        """)
        # Community points
        conn.execute("""
            CREATE TABLE IF NOT EXISTS community_points (
                user_id      INTEGER PRIMARY KEY,
                display_name TEXT DEFAULT 'Student',
                points       INTEGER DEFAULT 0,
                challenges_done TEXT DEFAULT '[]',
                joined_at    TEXT
            )
        """)
        # University threads (dynamic)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uni_threads (
                university   TEXT PRIMARY KEY,
                group_id     INTEGER,
                topic_id     INTEGER,
                created_at   TEXT
            )
        """)
        conn.commit()


def get_or_create_community_profile(user_id: int, display_name: str = "Student") -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM community_points WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO community_points (user_id, display_name, points, joined_at) VALUES (?, ?, 0, ?)",
                (user_id, display_name, datetime.now(UTC).isoformat())
            )
            conn.commit()
            return {"user_id": user_id, "display_name": display_name, "points": 0, "challenges_done": []}
        p = dict(row)
        p["challenges_done"] = json.loads(p.get("challenges_done", "[]"))
        return p


def add_community_points(user_id: int, points: int, reason: str = ""):
    with _get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO community_points (user_id, points, joined_at) VALUES (?, 0, ?)",
                     (user_id, datetime.now(UTC).isoformat()))
        conn.execute("UPDATE community_points SET points = points + ? WHERE user_id = ?", (points, user_id))
        conn.commit()
    logger.info("User %d +%d pts (%s)", user_id, points, reason)


def complete_challenge(user_id: int, challenge_id: str) -> tuple[bool, int]:
    """Returns (already_done, points_awarded)."""
    profile = get_or_create_community_profile(user_id)
    done    = profile.get("challenges_done", [])
    if challenge_id in done:
        return True, 0

    challenge = next((c for c in WEEKLY_CHALLENGES if c["id"] == challenge_id), None)
    if not challenge:
        return False, 0

    pts = challenge["points"]
    done.append(challenge_id)
    with _get_conn() as conn:
        conn.execute(
            "UPDATE community_points SET points = points + ?, challenges_done = ? WHERE user_id = ?",
            (pts, json.dumps(done), user_id)
        )
        conn.commit()
    return False, pts


def get_leaderboard(limit: int = 10) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, display_name, points FROM community_points ORDER BY points DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def next_anon_number(group_id: int) -> int:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(anon_number) as mx FROM anon_posts WHERE group_id = ?", (group_id,)
        ).fetchone()
    return (row["mx"] or 0) + 1


def log_anon_post(user_id: int, group_id: int, topic_id: int, message_id: int, anon_number: int):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO anon_posts (user_id, group_id, topic_id, message_id, anon_number, timestamp) VALUES (?,?,?,?,?,?)",
            (user_id, group_id, topic_id, message_id, anon_number, datetime.now(UTC).isoformat())
        )
        conn.commit()


def route_message_to_topic(text: str) -> str:
    """Suggest which topic a message belongs to."""
    text_lower = text.lower()
    for topic, keywords in TOPIC_ROUTER.items():
        if any(kw in text_lower for kw in keywords):
            return topic
    return "general"


# ══════════════════════════════════════════════════════════════
# WELCOME & ONBOARDING MESSAGES
# ══════════════════════════════════════════════════════════════

def get_welcome_message(first_name: str, is_future_student: bool = False) -> str:
    if is_future_student:
        return (
            f"Welcome {first_name}! 🎓\n\n"
            "This community is for both current students in Korea AND future students planning to come.\n\n"
            "Since you're still planning:\n"
            "→ Ask ANYTHING in #future-students-qa — current students answer\n"
            "→ Browse #housing-help and #visa-arc for real experiences\n"
            "→ The bot (@this_bot) answers instantly 24/7\n\n"
            "What are you most nervous about regarding Korea? Ask away! 🙌"
        )
    return (
        f"환영합니다 {first_name}! 🇰🇷\n\n"
        "You're now part of the K-Transition community — "
        "international students in Korea helping each other.\n\n"
        "Quick start:\n"
        "📌 Introduce yourself in #general\n"
        "🏠 Housing question? → #housing-help\n"
        "💙 Having a hard time? → #support (anonymous OK)\n"
        "🏆 This week's challenge → #weekly-challenge\n\n"
        "The personal bot (@this_bot) works in DMs for private questions.\n"
        "Anonymous posts: /anon [your message] in any topic.\n\n"
        "Glad you're here. What city are you in? 🌆"
    )


def get_group_rules() -> str:
    return """📋 Community Rules

1. 🤝 Respect always — everyone is adjusting at their own pace
2. 🔴 No scam/spam/promo without permission
3. 💙 Support topic is judgment-free — no toxic positivity
4. 🎭 Anonymous posts: use /anon — moderators can see sender if needed for safety
5. 🌍 All nationalities, all backgrounds — this community is diverse by design
6. 🤫 What's shared in #support stays in #support
7. 📢 Only admins post in #announcements
8. ❓ Before asking — search the topic history, it may already be answered

Breaking these = removed from group. Simple."""


def get_topic_intro(topic_key: str) -> str:
    intros = {
        "housing": (
            "🏠 Housing Help\n\n"
            "This is the single most financially dangerous aspect of being an international student in Korea.\n\n"
            "Ask about: rent prices, contract clauses, deposit protection, scams, 고시원 vs 원룸 vs dormitory.\n\n"
            "🔴 GOLDEN RULE: NEVER pay deposit before signed contract. Ever.\n"
            "Always check 등기부등본 at iros.go.kr (700 won).\n"
            "After signing: 주민센터 within 14 days for 확정일자 (600 won) = deposit protection."
        ),
        "support": (
            "💙 Support Space\n\n"
            "This topic is different. No advice unless asked. No 'just be positive'.\n"
            "Just honest space for the hard stuff.\n\n"
            "Feeling lonely, overwhelmed, homesick, anxious about money, academic pressure, "
            "identity confusion — all valid here.\n\n"
            "Anonymous option: type /anon support [your message]\n"
            "Nobody sees your name. Only the admins can see sender in safety situations.\n\n"
            "If you're in crisis right now:\n"
            "📞 109 (Korea Crisis Line, 24/7, free)\n"
            "📞 1345 (Multilingual foreigner support)"
        ),
        "future_students": (
            "🎓 Future Students Q&A\n\n"
            "You haven't arrived yet — that's exactly why you belong here.\n\n"
            "Ask current students ANYTHING:\n"
            "• What do I actually need to prepare before flying?\n"
            "• How much money should I bring?\n"
            "• What was the biggest surprise about Korean university life?\n"
            "• Is [university] good for my field?\n"
            "• GKS scholarship application tips?\n\n"
            "Current students: answer one question this week = earn challenge points!\n"
            "Your experience saves the next person months of confusion."
        ),
        "language": (
            "🇰🇷 Language Exchange\n\n"
            "Post Korean you're not sure about — someone will correct it.\n"
            "Share a word or phrase you learned this week.\n"
            "Ask pronunciation questions.\n\n"
            "Korean students on this channel: your corrections + explanations = community points!\n\n"
            "Weekly: bot posts the Word of the Day here every morning.\n"
            "Use /quiz in DM with the bot for adaptive AI-powered quiz."
        ),
        "marketplace": (
            "📦 Marketplace\n\n"
            "International students come and go. Great things get left behind.\n\n"
            "Post: items for sale, items to give away FREE, items you're looking for.\n\n"
            "Format:\n"
            "[SELL] Item — price — condition — location\n"
            "[FREE] Item — available until [date] — location\n"
            "[WANT] What you're looking for\n\n"
            "No commercial selling. Students only."
        ),
    }
    return intros.get(topic_key, TOPICS.get(topic_key, {}).get("description", ""))


# ══════════════════════════════════════════════════════════════
# SEEDED CONTENT FOR FUTURE STUDENTS TOPIC
# Real Q&A to make the group valuable from day 1
# ══════════════════════════════════════════════════════════════

SEED_QA = [
    {
        "q": "How much money should I bring to Korea for the first month?",
        "a": (
            "Realistic first-month budget breakdown:\n"
            "• SIM card: 30,000-50,000 won\n"
            "• T-Money + charges: 25,000 won\n"
            "• ARC fee: 30,000 won\n"
            "• Household setup (Daiso etc.): 100,000-150,000 won\n"
            "• Food first month: 200,000-350,000 won\n"
            "• Transport: 50,000-80,000 won\n"
            "Total: ~500,000-700,000 won (~$380-530 USD) EXCLUDING rent\n\n"
            "Bring at least 1,000,000 won as cash/accessible funds for first 2 weeks "
            "before your bank account is set up."
        )
    },
    {
        "q": "Is it hard to find halal food in Korea?",
        "a": (
            "Depends on your city. Seoul (especially Itaewon area) = easiest.\n"
            "Daejeon, Daegu, smaller cities = harder but manageable.\n\n"
            "What works: HalalKorea.com, search '할랄' on Naver Maps, "
            "Muslim Student Association at most universities, cooking at home (halal meat "
            "available at Islamic Foundation of Korea shops).\n\n"
            "What catches people off guard: Korean food that looks safe often has "
            "hidden pork stock (설렁탕, 된장찌개) or alcohol marinades. "
            "Always ask: 돼지고기 없나요? (no pork?)"
        )
    },
    {
        "q": "What's the most important thing to do in the first week?",
        "a": (
            "In order:\n"
            "1. SIM card (airport — passport only)\n"
            "2. T-Money card (any CU/GS25/7-Eleven)\n"
            "3. Download: Naver Maps, Papago, KakaoTalk\n"
            "4. Book ARC appointment at HiKorea.go.kr (slots fill up 2-4 weeks out!)\n"
            "5. Find your international student office on campus\n\n"
            "The #1 mistake: waiting on ARC. Everything else (bank account, "
            "proper phone plan, housing contracts) requires ARC. Book Day 2."
        )
    },
    {
        "q": "How is Korean university life different from back home?",
        "a": (
            "Things that surprise almost everyone:\n"
            "• Professors = significant authority. Don't interrupt, argue publicly.\n"
            "• Group projects: oldest student usually leads. Respect seniority.\n"
            "• Study culture is intense — library at 11pm is normal.\n"
            "• Social life: 동아리 (clubs) are how Korean students make friends. Join one.\n"
            "• Food: campus cafeteria is cheap and good. 3,500-5,000 won/meal.\n"
            "• Alcohol culture: 회식 (group dinner+drinks) is social cement. "
            "Saying no repeatedly = social isolation. Say yes once, leave early.\n\n"
            "Biggest hidden rule: staying after class to ask the professor a question "
            "= shows respect and interest = affects your grade more than you expect."
        )
    },
    {
        "q": "Will I be lonely in Korea as an international student?",
        "a": (
            "Honest answer: possibly, especially Month 2-3. Almost everyone goes through it.\n\n"
            "Why: Korean students have established friend groups from day one. "
            "International students are often grouped together, which is comfortable "
            "but can create a bubble.\n\n"
            "What actually helps:\n"
            "• Language exchange (언어교환) — most organic way to meet Korean students\n"
            "• 동아리 (clubs) — join one that matches your interest, not 'international' clubs\n"
            "• University counseling center — free, don't wait until it's bad\n"
            "• This community — people who exactly understand what you're going through\n\n"
            "It gets significantly better after Month 3-4 for most people. "
            "The students who reach out early have much easier transitions."
        )
    },
]


def format_seed_post(qa: dict) -> str:
    return f"❓ Common Question:\n\n{qa['q']}\n\n━━━━━━\n\n💬 From a current student:\n\n{qa['a']}"
