# predictor.py — K-Transition OS v4.0
# ═══════════════════════════════════════════════════════════
# THE "PREDICTIVE LIFE INSURANCE" SYSTEM
# ═══════════════════════════════════════════════════════════
#
# Core insight: international student struggles follow KNOWN patterns.
# Week 3 confusion, Month 3 loneliness peak, Month 4 academic clash —
# these are DOCUMENTED. Nobody built a tool that acts on them in advance.
#
# This module:
#   1. Tracks where every student is on the "Korea Timeline"
#   2. Sends proactive, personalized warnings BEFORE problems hit
#   3. Each warning = what's coming + why it affects YOU + one micro-action
#
# "We don't wait for the student to break. We notice before they do."

import json
import logging
from datetime import datetime, UTC, date
from typing import Optional

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# THE KOREA TIMELINE — research-backed challenge windows
# Each event has:
#   day_start / day_end : window when this is relevant
#   conditions          : profile filters (diet, etc.) — None = everyone
#   title               : short label
#   message             : personalized warning (uses {name}, {city}, {uni})
#   micro_action        : ONE concrete thing to do TODAY
#   category            : financial | social | mental | academic | bureaucratic
# ══════════════════════════════════════════════════════════════

TIMELINE_EVENTS = [
    # ── WEEK 1 ──────────────────────────────────────────────
    {
        "id": "arrival_shock",
        "day_start": 1, "day_end": 3,
        "category": "mental",
        "title": "Arrival Overwhelm is Normal",
        "message": (
            "Hey {name} — everything feeling like a LOT right now is completely expected.\n\n"
            "Researchers call this 'arrival overwhelm' — your brain is processing a new language, "
            "new faces, new food, new systems all at once. It peaks Day 1-3.\n\n"
            "You don't need to figure everything out today. You need to do exactly 3 things: "
            "SIM card, T-Money card, sleep."
        ),
        "micro_action": "Write down 3 things you noticed today that were different from home. That's it.",
        "conditions": None,
    },
    {
        "id": "halal_week1",
        "day_start": 2, "day_end": 7,
        "category": "food",
        "title": "Halal Food Reality Check",
        "message": (
            "Important heads up {name} — in {city}, finding halal food without research "
            "can be really stressful. The standard Korean campus food is almost never halal "
            "(hidden pork stock, alcohol marinades).\n\n"
            "The students who handle this best are the ones who map their options in Week 1, "
            "not Week 4 when they're exhausted."
        ),
        "micro_action": "Open Naver Maps, search '할랄 음식' right now. Save the top 2 nearest results.",
        "conditions": {"diet": "halal"},
    },

    # ── WEEK 2-3 ────────────────────────────────────────────
    {
        "id": "arc_urgency",
        "day_start": 10, "day_end": 20,
        "category": "bureaucratic",
        "title": "ARC Appointment Slots Fill Fast",
        "message": (
            "{name}, quick check — have you booked your ARC appointment at HiKorea.go.kr?\n\n"
            "Most students in {city} find that slots are 2-4 weeks out. If you book today "
            "vs booking in Week 4, the difference can mean 2 extra weeks without a bank account, "
            "proper phone plan, or ability to sign a housing contract.\n\n"
            "You have time — but that time is being used up right now."
        ),
        "micro_action": "Go to HiKorea.go.kr → Book Appointment → 외국인등록. Takes 15 minutes.",
        "conditions": None,
    },
    {
        "id": "convenience_trap",
        "day_start": 14, "day_end": 21,
        "category": "financial",
        "title": "The Convenience Store Trap",
        "message": (
            "Financial heads up {name} — Week 2 is when most international students "
            "accidentally set a very expensive habit.\n\n"
            "CU and GS25 are everywhere and convenient. But eating even 2 meals a day there "
            "costs 8,000-12,000 won/day = 240,000-360,000 won/month on food alone.\n\n"
            "Campus cafeteria: 3,500-5,000 won/meal. Cooking once a week: even cheaper.\n"
            "The difference over a semester: 300,000-500,000 won."
        ),
        "micro_action": "Find your campus cafeteria (학생식당) location today. Try it once this week.",
        "conditions": None,
    },

    # ── MONTH 1 END ─────────────────────────────────────────
    {
        "id": "jumin_deadline",
        "day_start": 12, "day_end": 14,
        "category": "bureaucratic",
        "title": "14-Day 주민센터 Deadline",
        "message": (
            "⚠️ {name} — if you moved into housing in your first week, you're approaching "
            "the 14-day deadline for 전입신고 at the 주민센터.\n\n"
            "This is not optional. Without 확정일자 your housing deposit has ZERO legal protection. "
            "If something goes wrong with your landlord, you lose everything.\n\n"
            "Cost: 600 won. Time: 1 hour. Protection: your entire deposit."
        ),
        "micro_action": "Search 주민센터 on Naver Maps right now. Go tomorrow morning.",
        "conditions": None,
    },
    {
        "id": "first_month_financial",
        "day_start": 28, "day_end": 35,
        "category": "financial",
        "title": "Month 1 Financial Reality Check",
        "message": (
            "Month 1 is almost done, {name}. This is when most students realize "
            "Korea is more expensive than they expected — not because Korea is expensive, "
            "but because the first month has one-time setup costs that never repeat "
            "(SIM, T-Money, household items, etc.).\n\n"
            "Month 2 onwards is significantly cheaper if you've established routines. "
            "The students who track their Month 1 spending — even roughly — make much "
            "better Month 2 decisions."
        ),
        "micro_action": "Rough estimate: what did you spend this month? Food / Transport / Setup / Other. Just estimate.",
        "conditions": None,
    },

    # ── MONTH 2 ─────────────────────────────────────────────
    {
        "id": "novelty_crash",
        "day_start": 40, "day_end": 55,
        "category": "mental",
        "title": "The Novelty Crash Window",
        "message": (
            "{name} — something you should know about this exact phase.\n\n"
            "The first month in Korea feels exciting because everything is new. "
            "Around Week 5-7, that novelty wears off — and what's left is just... reality. "
            "New country, hard language, systems that don't make sense, and no deep friendships yet.\n\n"
            "This phase is called the 'disenchantment stage.' It's documented. It's normal. "
            "And knowing it's coming makes it significantly easier to get through."
        ),
        "micro_action": "Name one thing about Korea that genuinely still interests you. Hold onto that.",
        "conditions": None,
    },

    # ── MONTH 3 — LONELINESS PEAK ───────────────────────────
    {
        "id": "loneliness_peak",
        "day_start": 75, "day_end": 100,
        "category": "social",
        "title": "Month 3 — The Loneliness Peak",
        "message": (
            "{name}, this is something almost nobody tells you before you come.\n\n"
            "Research on international students consistently shows Month 3 as the loneliness peak. "
            "Not Month 1 (too exciting), not Month 6 (adjusted). Month 3.\n\n"
            "Why? Because by now you know enough to know what you're missing — real conversations, "
            "inside jokes, people who actually know you — but haven't built that yet in Korea.\n\n"
            "If you're feeling this right now: you're not failing at Korea. You're at the "
            "statistically hardest point of the journey. It gets better after this."
        ),
        "micro_action": "Message one person from home today. Not to say you're struggling — just to connect.",
        "conditions": None,
    },
    {
        "id": "korean_friend_prompt",
        "day_start": 80, "day_end": 110,
        "category": "social",
        "title": "The Integration Window",
        "message": (
            "Quick honest question {name} — how many Korean students do you actually talk to?\n\n"
            "Not classmates you nod to. Actual conversations.\n\n"
            "Month 3-4 is the window where this either gets established or doesn't. "
            "Students who don't make a Korean friend by Month 4 statistically spend "
            "their entire Korea time in an international student bubble — which is fine, "
            "but it means missing the actual Korea experience.\n\n"
            "The easiest entry point: language exchange (언어교환). You help with English, "
            "they help with Korean. Zero awkwardness about why you're talking to them."
        ),
        "micro_action": "Search '[{uni}] 언어교환' on Google or check the university bulletin board this week.",
        "conditions": None,
    },

    # ── MONTH 4 — ACADEMIC CLASH ────────────────────────────
    {
        "id": "academic_culture_clash",
        "day_start": 100, "day_end": 130,
        "category": "academic",
        "title": "Korean Classroom ≠ What You're Used To",
        "message": (
            "{name} — if your grades feel off or you're not sure where you stand, "
            "this might be why.\n\n"
            "Korean academic culture has invisible rules:\n"
            "• Participation ≠ speaking up. It means showing prepared knowledge.\n"
            "• Professors notice who stays after class — it signals respect and interest.\n"
            "• Group projects: seniority matters. The oldest student often makes final calls.\n"
            "• Asking questions IN class can feel like challenging the professor.\n"
            "  Asking AFTER class = shows genuine interest.\n\n"
            "None of this is written anywhere. But it affects your grade and your relationships."
        ),
        "micro_action": "After your next class, stay 2 minutes and ask the professor ONE question. Anything.",
        "conditions": None,
    },

    # ── MONTH 5-6 ───────────────────────────────────────────
    {
        "id": "identity_drift",
        "day_start": 140, "day_end": 175,
        "category": "mental",
        "title": "The Identity Drift Phase",
        "message": (
            "Something subtle might be happening around now, {name}.\n\n"
            "After ~5 months, many international students start feeling... blurry. "
            "Not fully Korean, not fully themselves from before. "
            "Some habits from home feel weird now. Some Korean things feel normal. "
            "It can feel disorienting.\n\n"
            "This is not a crisis. This is called bicultural identity formation — "
            "and it's actually the sign that real integration is happening. "
            "The discomfort is the growth."
        ),
        "micro_action": "Write 3 ways Korea has changed how you think or behave. No judgment — just notice.",
        "conditions": None,
    },
    {
        "id": "nhis_approaching",
        "day_start": 165, "day_end": 185,
        "category": "bureaucratic",
        "title": "Health Insurance Enrolling Soon",
        "message": (
            "Heads up {name} — you're approaching the 6-month mark, which means "
            "NHIS (국민건강보험) will auto-enroll you soon.\n\n"
            "What this means:\n"
            "• ~30,000-40,000 won/month deducted automatically\n"
            "• BUT: hospital visits drop to 20-30% of the actual cost\n"
            "• Emergency care, clinic, pharmacy — all covered\n\n"
            "Action needed: check if your university has supplemental insurance "
            "that overlaps (some universities do — you might be able to opt out of one)."
        ),
        "micro_action": "Ask international office: '국민건강보험 학교 보험이랑 겹치나요?' (Does NHIS overlap with university insurance?)",
        "conditions": None,
    },

    # ── SEMESTER 2 ──────────────────────────────────────────
    {
        "id": "visa_extension",
        "day_start": 300, "day_end": 330,
        "category": "bureaucratic",
        "title": "Visa Extension — Start Now",
        "message": (
            "{name} — your visa extension window is coming up.\n\n"
            "Most D-2/D-4 visas need renewal around the 1-year mark. "
            "Immigration offices are slow and slots fill up. "
            "Students who start this process late sometimes end up in overstay situations "
            "which can affect future Korean visa applications for life.\n\n"
            "Start now: HiKorea.go.kr → Extend Stay → Book appointment."
        ),
        "micro_action": "Check your ARC card expiry date TODAY. If within 4 months → book extension appointment.",
        "conditions": None,
    },

    # ── YEAR 2 PLATEAU ──────────────────────────────────────
    {
        "id": "year2_plateau",
        "day_start": 365, "day_end": 400,
        "category": "academic",
        "title": "The Year 2 Plateau — Everyone Hits It",
        "message": (
            "One year in, {name}. That's genuinely remarkable.\n\n"
            "But here's something to watch for: Year 2 is when many students "
            "hit a plateau. The survival challenges are gone. Routines are set. "
            "And sometimes that safety becomes a comfort zone that stops growth.\n\n"
            "The students who look back on Korea with the most satisfaction are "
            "the ones who set a Year 2 challenge: Korean-only conversations for a month, "
            "a research project, an internship application, a city they've never visited.\n\n"
            "You survived Year 1. Year 2 should be different — not just more of the same."
        ),
        "micro_action": "Name one thing you want to do in Korea that you haven't done yet. Set a date.",
        "conditions": None,
    },
]


def days_since_arrival(arrival_date_str: str) -> Optional[int]:
    """Calculate days since arrival from stored date string."""
    if not arrival_date_str:
        return None
    try:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%B %Y", "%b %Y"):
            try:
                arrival = datetime.strptime(arrival_date_str, fmt).date()
                return (date.today() - arrival).days
            except ValueError:
                continue
        # Try partial like "September 2025"
        from dateutil import parser as dateparser
        arrival = dateparser.parse(arrival_date_str).date()
        return (date.today() - arrival).days
    except Exception:
        return None


def get_todays_predictions(user_info: dict) -> list[dict]:
    """
    Return list of timeline events relevant for this user today.
    Each returned dict has: title, message, micro_action, category
    """
    arrival_date = user_info.get("arrival_date", "")
    if not arrival_date:
        return []

    days = days_since_arrival(arrival_date)
    if days is None or days < 0:
        return []

    diet       = user_info.get("diet", "none")
    name       = user_info.get("first_name", "friend")
    city       = user_info.get("city", "your city")
    uni        = user_info.get("university", "your university")
    triggered  = []

    for event in TIMELINE_EVENTS:
        # Check if today is the exact day_start day for this event
        if days != event["day_start"]:
            continue

        # Check conditions
        cond = event.get("conditions")
        if cond:
            if "diet" in cond and cond["diet"] != diet:
                continue

        # Personalise message
        msg    = event["message"].format(name=name, city=city, uni=uni)
        action = event["micro_action"].format(name=name, city=city, uni=uni)

        triggered.append({
            "id":           event["id"],
            "title":        event["title"],
            "message":      msg,
            "micro_action": action,
            "category":     event["category"],
            "day":          days,
        })

    return triggered


def format_prediction(event: dict) -> str:
    """Format a prediction for Telegram."""
    category_icons = {
        "financial":    "💰",
        "social":       "👥",
        "mental":       "💙",
        "academic":     "📚",
        "bureaucratic": "🏛️",
        "food":         "🍽️",
    }
    icon = category_icons.get(event["category"], "🔮")
    day  = event.get("day", "?")

    msg  = f"{icon} Day {day} — {event['title']}\n"
    msg += "─" * 30 + "\n\n"
    msg += event["message"]
    msg += f"\n\n✅ One thing to do today:\n{event['micro_action']}"
    return msg


def get_days_in_korea_summary(days: int) -> str:
    """Give a context-aware milestone message."""
    if days < 7:
        return f"Day {days} — First week. Survival mode. You're doing great."
    elif days < 30:
        return f"Day {days} — First month. Foundation building."
    elif days < 90:
        weeks = days // 7
        return f"Week {weeks} — Finding your rhythm."
    elif days < 365:
        months = days // 30
        return f"Month {months} — Deep adjustment phase."
    else:
        years = days // 365
        months = (days % 365) // 30
        return f"Year {years}, Month {months} — Experienced expat."
