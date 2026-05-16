# bridge_builder.py — K-Transition OS v4.0
# ═══════════════════════════════════════════════════════════
# BRIDGE BUILDER — Integration Milestone Tracker
# CAREER COMPASS  — Korean workplace/career navigation
# GRADUATION PORTFOLIO — 4-year competency record
# ═══════════════════════════════════════════════════════════
#
# "Invisible Integration" problem:
# Student physically in Korea, grades fine, but zero Korean friends.
# Parallel existence, not actual integration.
# GKS mission = building Korea-world bridges. This measures that.
#
# Korean CV, interview roleplay, workplace scenarios — nobody teaches this.
# Every Western student learns it the hard way. This module changes that.

import json
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# INTEGRATION MILESTONES
# Each milestone = a genuine Korea connection moment
# ══════════════════════════════════════════════════════════════

INTEGRATION_MILESTONES = [
    {
        "id": "korean_greeting",
        "title": "First Korean Greeting",
        "description": "Greeted a Korean person in Korean (not in English)",
        "points": 10,
        "prompt": "Next time you enter a shop or pass a staff member, say 안녕하세요 first.",
        "level": 1,
    },
    {
        "id": "korean_order",
        "title": "Ordered Food in Korean",
        "description": "Placed a food/drink order completely in Korean",
        "points": 15,
        "prompt": "At your next café or restaurant visit, say: 이거 주세요 (point at menu). That's a complete order.",
        "level": 1,
    },
    {
        "id": "korean_conversation",
        "title": "Real Korean Conversation",
        "description": "Had a real back-and-forth conversation with a Korean person (5+ exchanges)",
        "points": 30,
        "prompt": "Ask a Korean classmate: 오늘 수업 어떠셨어요? (How was today's class?) and keep it going.",
        "level": 2,
    },
    {
        "id": "korean_classmate_contact",
        "title": "Korean Classmate KakaoTalk",
        "description": "Exchanged KakaoTalk contact with a Korean student",
        "points": 25,
        "prompt": "At the end of a class, say: 카카오톡 ID가 뭐예요? (What's your KakaoTalk ID?)",
        "level": 2,
    },
    {
        "id": "korean_professor_chat",
        "title": "Talked to a Professor Personally",
        "description": "Had a personal conversation with a Korean professor after class",
        "points": 35,
        "prompt": "Stay 2 minutes after a class. Ask: 교수님, 오늘 [topic] 질문이 있는데요... (Professor, I have a question about today's topic...)",
        "level": 2,
    },
    {
        "id": "korean_friend",
        "title": "Korean Friend",
        "description": "Have a Korean person you'd genuinely call a friend (not just acquaintance)",
        "points": 50,
        "prompt": "Language exchange is the most organic way. Search '[your uni] 언어교환' this week.",
        "level": 3,
    },
    {
        "id": "korean_home_visit",
        "title": "Visited a Korean Student's Home",
        "description": "Were invited to and visited a Korean person's home or family gathering",
        "points": 60,
        "prompt": "This comes after building a real friendship. Focus on milestone 6 (Korean Friend) first.",
        "level": 4,
    },
    {
        "id": "korean_only_day",
        "title": "Korean-Only Day",
        "description": "Spent an entire day communicating only in Korean",
        "points": 70,
        "prompt": "Set a date. Tell a Korean friend. Make it a challenge together.",
        "level": 4,
    },
    {
        "id": "helped_korean",
        "title": "Helped a Korean Person",
        "description": "Helped a Korean person with something meaningful (advice, translation, skill)",
        "points": 40,
        "prompt": "This is the relationship flip — from student to contributor. You'll know when it happens.",
        "level": 3,
    },
    {
        "id": "korean_club",
        "title": "Joined a Korean Club",
        "description": "Joined a 동아리 (club) where most members are Korean",
        "points": 45,
        "prompt": "Check your university's 동아리 board. Look for something you genuinely like — not 'international students welcome', just a regular club.",
        "level": 3,
    },
]


# ══════════════════════════════════════════════════════════════
# CAREER COMPASS
# Korean workplace culture nobody teaches
# ══════════════════════════════════════════════════════════════

CAREER_CONTENT = {
    "cv_guide": """📄 Korean CV Guide — Different from Everything You Know

━━ KEY DIFFERENCES FROM WESTERN CV ━━

1. PHOTO (required in Korea)
   • Professional headshot, plain background, business attire
   • Size: passport photo style
   • No smile is fine — neutral/slight smile standard

2. PERSONAL INFO Koreans include:
   • Date of birth (나이/생년월일)
   • Gender
   • Address
   • Military service (남자만 — males only)
   • Do NOT include religion, marital status

3. EDUCATION: list in REVERSE order (most recent first)
   • Include GPA if above 3.5/4.5 or 3.0/4.0
   • List scholarships (GKS = VERY impressive on Korean CV)

4. SELF-INTRODUCTION (자기소개서) = the most important part
   • Usually 600-1000 Korean characters
   • Format: Growth story → Strengths → Why this company → Future goals
   • More personal/narrative than Western cover letters
   • Mention specific experiences in Korea, not generic

5. SKILLS SECTION
   • TOPIK level (if any — even beginner level shows effort)
   • OPIc English level (AI-assessed English test Koreans use)
   • Computer skills: MOS certifications common

━━ GOLDEN RULE ━━
Korean hiring managers want to know: "Will this person fit our team culture?"
More than skills. More than grades. 팀워크 (teamwork) and 성실함 (diligence) are the magic words.

Type /career interview for Korean interview prep.""",

    "interview_guide": """🎯 Korean Interview Preparation

━━ WHAT THEY ALWAYS ASK ━━

1. 자기소개 해보세요 (Introduce yourself)
   • 1-2 minutes. Growth → strength → why here.
   • End with: 잘 부탁드립니다 (I look forward to working together)

2. 지원 동기가 뭔가요? (Why do you want this job/position?)
   • Be specific to THIS company, not the industry
   • Research the company beforehand — mention one specific thing

3. 장단점이 뭔가요? (What are your strengths and weaknesses?)
   • Weakness: pick a real one but show how you're improving it
   • Never say: "I work too hard" — they know this trick

4. 어떤 어려움이 있었고 어떻게 극복했나요? (Difficult experience and how you overcame it)
   • Korea loves resilience stories
   • Studying in Korea as a foreigner = powerful story material

━━ CULTURAL RULES ━━
• Bow slightly when entering (15 degrees, not 90)
• Sit only when invited to
• Two hands when giving/receiving anything
• "I don't know but I will find out" > making up an answer
• Speak about team accomplishments, not just personal ones

━━ AS AN INTERNATIONAL STUDENT ━━
Your advantage: cross-cultural experience + language skills + unique perspective
Frame it: "I understand both Korean culture and international perspective — that's rare."

Type /career roleplay to practice with AI.""",

    "workplace_scenarios": """🏢 Korean Workplace — What Nobody Teaches You

━━ HIERARCHY (직급 체계) ━━
인턴 → 사원 → 주임 → 대리 → 과장 → 차장 → 부장 → 임원
Seniority determines speaking order in meetings, seating at meals, everything.

━━ REAL SCENARIOS ━━

Scenario 1: 회식 (Company Dinner)
Boss says "Let's go for dinner" at 6pm. This is NOT optional.
• Pour drinks for others first, especially seniors
• Never pour your own drink — someone will notice and refill it
• Leave when the most senior person leaves
• Refusing = career damage. Going 30-60 min = respectful exit.

Scenario 2: Sunbae asks for help outside work hours
Just say yes. This is relationship investment, not exploitation.
In 6 months when you need help, you know who to call.

Scenario 3: Your idea got used but you weren't credited
Don't confront directly. Build relationship with sunbae first.
Then: "선배님, 제가 기여한 부분을 어떻게 발전시키면 좋을까요?" (How can I build on my contribution?)

Scenario 4: You made a mistake
Own it immediately and directly to your direct manager.
Koreans respect swift ownership more than perfect performance.

━━ COMMUNICATION ━━
• Email starts with formal greeting ALWAYS
• Instant messaging = casual is fine among same-rank peers
• Never message a senior at night unless they initiate
• "Yes" in a meeting often means "I hear you" not "I agree" — confirm with action""",
}


def setup_bridge_tables():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_milestones (
                user_id   INTEGER,
                milestone_id TEXT,
                completed_at TEXT,
                PRIMARY KEY (user_id, milestone_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER,
                category  TEXT,
                event     TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()


from db import get_conn as _get_conn


def get_completed_milestones(user_id: int) -> list[str]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT milestone_id FROM integration_milestones WHERE user_id = ?", (user_id,)
        ).fetchall()
    return [r["milestone_id"] for r in rows]


def complete_milestone(user_id: int, milestone_id: str) -> dict | None:
    """Mark a milestone complete. Returns the milestone data or None if not found."""
    milestone = next((m for m in INTEGRATION_MILESTONES if m["id"] == milestone_id), None)
    if not milestone:
        return None
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO integration_milestones (user_id, milestone_id, completed_at) VALUES (?, ?, ?)",
            (user_id, milestone_id, datetime.now(UTC).isoformat())
        )
        conn.commit()
    # Log to portfolio
    log_portfolio_event(user_id, "integration", f"Completed: {milestone['title']}")
    return milestone


def get_integration_score(user_id: int) -> dict:
    """Return integration score, level, and next suggested milestone."""
    completed   = get_completed_milestones(user_id)
    total_pts   = sum(m["points"] for m in INTEGRATION_MILESTONES if m["id"] in completed)
    max_pts     = sum(m["points"] for m in INTEGRATION_MILESTONES)
    percentage  = int(total_pts / max_pts * 100) if max_pts else 0

    # Find next uncompleted milestone at lowest level
    next_ms = None
    for level in [1, 2, 3, 4]:
        for m in INTEGRATION_MILESTONES:
            if m["level"] == level and m["id"] not in completed:
                next_ms = m
                break
        if next_ms:
            break

    return {
        "completed":    completed,
        "total_points": total_pts,
        "max_points":   max_pts,
        "percentage":   percentage,
        "next":         next_ms,
        "count":        len(completed),
    }


def format_integration_status(user_id: int) -> str:
    data = get_integration_score(user_id)
    pct  = data["percentage"]
    completed = data["completed"]

    if pct >= 80:
        badge = "🌟 Deep Integrator"
    elif pct >= 60:
        badge = "🌳 Well Connected"
    elif pct >= 40:
        badge = "🌿 Building Roots"
    elif pct >= 20:
        badge = "🌱 Just Starting"
    else:
        badge = "🪴 Plant the Seed"

    msg  = f"🌉 Integration Score: {pct}% — {badge}\n"
    msg += f"Milestones completed: {data['count']}/{len(INTEGRATION_MILESTONES)}\n\n"

    # Show completed
    if completed:
        msg += "✅ Achieved:\n"
        for m in INTEGRATION_MILESTONES:
            if m["id"] in completed:
                msg += f"  • {m['title']} (+{m['points']}pts)\n"
        msg += "\n"

    # Show next
    nxt = data["next"]
    if nxt:
        msg += f"🎯 Next milestone:\n"
        msg += f"  {nxt['title']}\n"
        msg += f"  {nxt['description']}\n\n"
        msg += f"💡 How: {nxt['prompt']}"
    else:
        msg += "🏆 You've completed all integration milestones!"

    msg += "\n\n/bridge done [milestone] to mark one complete"
    return msg


def format_milestone_list() -> str:
    msg = "🌉 Integration Milestones\n\n"
    for level in [1, 2, 3, 4]:
        level_names = {1: "Beginner", 2: "Connected", 3: "Integrated", 4: "Fluent"}
        msg += f"Level {level} — {level_names[level]}:\n"
        for m in INTEGRATION_MILESTONES:
            if m["level"] == level:
                msg += f"  /bridge done {m['id']}\n"
                msg += f"  {m['title']} ({m['points']} pts)\n"
        msg += "\n"
    return msg.strip()


# ══════════════════════════════════════════════════════════════
# GRADUATION PORTFOLIO
# ══════════════════════════════════════════════════════════════

def log_portfolio_event(user_id: int, category: str, event: str):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolio_events (user_id, category, event, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, category, event[:300], datetime.now(UTC).isoformat())
        )
        conn.commit()


def generate_portfolio(user_id: int, user_info: dict) -> str:
    """Generate the graduation competency document."""
    from memory import get_progress, get_situations
    from predictor import days_since_arrival

    progress   = get_progress(user_id)
    situations = get_situations(user_id, 100)
    integration = get_integration_score(user_id)

    # Count situations by risk
    high_risk   = sum(1 for s in situations if s.get("risk") == "HIGH")
    scams_avoided = sum(1 for s in situations if "scam" in s.get("summary","").lower() or "SCAM" in s.get("rule_id",""))

    days = None
    if user_info.get("arrival_date"):
        days = days_since_arrival(user_info["arrival_date"])

    name   = user_info.get("first_name", "Student")
    uni    = user_info.get("university", "Unknown University")
    city   = user_info.get("city", "Korea")

    with _get_conn() as conn:
        events = conn.execute(
            "SELECT category, event, timestamp FROM portfolio_events WHERE user_id = ? ORDER BY timestamp",
            (user_id,)
        ).fetchall()

    duration_str = f"{days} days" if days else "Unknown duration"

    msg  = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"  KOREA COMPETENCY RECORD\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"Student:    {name}\n"
    msg += f"University: {uni}\n"
    msg += f"City:       {city}\n"
    msg += f"Duration:   {duration_str}\n\n"

    msg += f"━━ LANGUAGE PROGRESSION ━━\n"
    msg += f"Korean words learned: {progress.get('korean_words', 0)}\n"
    msg += f"Quiz accuracy: {progress.get('quiz_correct',0)}/{progress.get('quiz_total',0)}"
    if progress.get('quiz_total'):
        pct = int(progress['quiz_correct']/progress['quiz_total']*100)
        msg += f" ({pct}%)"
    msg += f"\nLevel achieved: {progress.get('quiz_level',1)}/5\n"
    msg += f"Active streak: {user_info.get('streak',0)} days\n\n"

    msg += f"━━ CULTURAL INTEGRATION ━━\n"
    msg += f"Integration score: {integration['percentage']}%\n"
    msg += f"Milestones completed: {integration['count']}/{len(INTEGRATION_MILESTONES)}\n\n"

    msg += f"━━ CHALLENGES NAVIGATED ━━\n"
    msg += f"Total situations handled: {len(situations)}\n"
    msg += f"High-risk situations navigated: {high_risk}\n"
    if scams_avoided:
        msg += f"Scam situations identified: {scams_avoided}\n"

    # Unique events
    if events:
        categories = {}
        for e in events:
            cat = e["category"]
            categories[cat] = categories.get(cat, 0) + 1
        msg += "\nKey achievements:\n"
        for cat, count in categories.items():
            msg += f"  • {cat.title()}: {count} recorded events\n"

    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d')}\n"
    msg += f"K-Transition OS v4.0\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    return msg
