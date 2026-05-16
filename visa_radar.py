# visa_radar.py — K-Transition OS v5.0
# Visa & deadline tracking — auto-calculates from arrival date
# Missing a deadline = deportation risk. This feature saves students.

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DEADLINES = [
    {"id": "sim", "title": "📱 Get SIM Card", "days": 0, "window": 3, "urgency": "HIGH",
     "desc": "Korean phone number needed for EVERYTHING", "where": "Airport booth or CU/GS25",
     "docs": "Passport only", "cost": "₩30-50k/month"},
    {"id": "tmoney", "title": "🚇 Get T-Money Card", "days": 0, "window": 3, "urgency": "MEDIUM",
     "desc": "Transport card for subway/bus/taxi", "where": "Any CU/GS25/7-Eleven",
     "docs": "None", "cost": "₩4,000 + top-up"},
    {"id": "jumin", "title": "🏛️ Register at 주민센터", "days": 1, "window": 14, "urgency": "HIGH",
     "desc": "MANDATORY address registration within 14 days", "where": "Nearest 주민센터",
     "docs": "Passport + housing contract", "cost": "Free + ₩600 확정일자"},
    {"id": "arc_book", "title": "📋 Book ARC Appointment", "days": 3, "window": 14, "urgency": "CRITICAL",
     "desc": "외국인등록증 booking — slots fill fast!", "where": "HiKorea.go.kr",
     "docs": "Passport, enrollment cert, 2 photos, ₩30,000", "cost": "₩30,000"},
    {"id": "bank", "title": "🏦 Open Bank Account", "days": 7, "window": 30, "urgency": "HIGH",
     "desc": "For scholarship, rent, shopping", "where": "Shinhan/Kakao Bank",
     "docs": "Passport + ARC or enrollment cert", "cost": "Free"},
    {"id": "arc_visit", "title": "🏛️ ARC Immigration Visit", "days": 14, "window": 60, "urgency": "CRITICAL",
     "desc": "Go to immigration for ARC. Takes 2-4 weeks after.", "where": "Immigration office",
     "docs": "Passport, cert, photos, ₩30,000, housing proof", "cost": "₩30,000"},
    {"id": "nhis", "title": "🏥 NHIS Health Insurance", "days": 180, "window": 30, "urgency": "HIGH",
     "desc": "Auto-enrolls after 6 months. Check status!", "where": "nhis.or.kr",
     "docs": "ARC", "cost": "~₩30-40k/month"},
    {"id": "visa_renew", "title": "📝 Visa Extension Check", "days": 330, "window": 60, "urgency": "CRITICAL",
     "desc": "Apply at least 1 month BEFORE expiry!", "where": "HiKorea.go.kr",
     "docs": "Passport, ARC, enrollment, bank statement", "cost": "₩60,000"},
]


def _parse_arrival(date_str):
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%B %Y", "%b %Y", "%Y-%m"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    if any(w in date_str.lower() for w in ["already", "here", "arrived"]):
        return datetime.now() - timedelta(days=30)
    return None


def get_visa_status(arrival_str):
    arrival = _parse_arrival(arrival_str)
    if not arrival:
        return None
    today = datetime.now()
    days_in = (today - arrival).days
    results = []
    for dl in DEADLINES:
        deadline = arrival + timedelta(days=dl["days"])
        window_end = deadline + timedelta(days=dl["window"])
        days_until = (deadline - today).days
        days_window = (window_end - today).days
        if days_window < 0:
            status = "OVERDUE" if dl["urgency"] == "CRITICAL" else "PAST"
        elif days_until <= 0:
            status = "NOW"
        elif days_until <= 7:
            status = "SOON"
        else:
            status = "UPCOMING"
        results.append({**dl, "days_until": days_until, "days_window": days_window, "status": status})
    return {"arrival": arrival, "days_in": days_in, "deadlines": results}


def format_visa_status(data):
    if not data:
        return "📡 Visa Radar\n\nSet arrival date first:\n/setarrival 2025-09-01\n\nThen use /visa to see deadlines!"
    msg = f"📡 Visa & Deadline Radar\n━━━━━━━━━━━━━━━━━━━━━━━━\n📅 Day {data['days_in']} in Korea\n\n"
    overdue = [d for d in data["deadlines"] if d["status"] == "OVERDUE"]
    now = [d for d in data["deadlines"] if d["status"] == "NOW"]
    soon = [d for d in data["deadlines"] if d["status"] == "SOON"]
    upcoming = [d for d in data["deadlines"] if d["status"] == "UPCOMING"]
    if overdue:
        msg += "🔴 OVERDUE:\n"
        for d in overdue:
            msg += f"  ⚠️ {d['title']} — {abs(d['days_window'])} days overdue!\n"
        msg += "\n"
    if now:
        msg += "🟡 DO NOW:\n"
        for d in now:
            msg += f"  ➡️ {d['title']} — {d['days_window']} days left\n"
        msg += "\n"
    if soon:
        msg += "🟠 THIS WEEK:\n"
        for d in soon:
            msg += f"  📌 {d['title']} — in {d['days_until']} days\n"
        msg += "\n"
    if upcoming:
        msg += "🟢 UPCOMING:\n"
        for d in upcoming[:3]:
            msg += f"  📋 {d['title']} — in {d['days_until']} days\n"
        msg += "\n"
    if not overdue and not now:
        msg += "✅ All deadlines on track! 👍\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n/visa checklist — Document details"
    return msg


def format_visa_checklist(data):
    if not data:
        return "Set arrival date: /setarrival 2025-09-01"
    msg = "📋 Document Checklist\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    icons = {"OVERDUE": "🔴", "NOW": "🟡", "SOON": "🟠", "UPCOMING": "⬜", "PAST": "✅"}
    for d in data["deadlines"]:
        msg += f"{icons.get(d['status'], '⬜')} {d['title']}\n"
        msg += f"   📍 {d['where']}\n   📄 {d['docs']}\n   💰 {d['cost']}\n\n"
    return msg
