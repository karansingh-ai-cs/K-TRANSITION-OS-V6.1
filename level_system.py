# level_system.py — K-Transition OS v5.0
# XP + gamification system — every interaction earns XP
# Levels: Newbie → Explorer → Survivor → Local → 선배 (Senior)

import logging

logger = logging.getLogger(__name__)

LEVELS = [
    {"level": 1, "name": "🌱 Newbie", "title": "신입생", "min_xp": 0, "perks": "Basic access"},
    {"level": 2, "name": "🌿 Explorer", "title": "탐험가", "min_xp": 100, "perks": "Unlock /simulate topics"},
    {"level": 3, "name": "🌳 Survivor", "title": "생존자", "min_xp": 300, "perks": "Unlock AI hacks"},
    {"level": 4, "name": "🏅 Adapter", "title": "적응자", "min_xp": 600, "perks": "Unlock advanced Korean scenarios"},
    {"level": 5, "name": "🏆 Local", "title": "현지인", "min_xp": 1000, "perks": "Unlock AI buddy proactive mode"},
    {"level": 6, "name": "👑 선배 (Senior)", "title": "선배", "min_xp": 1500, "perks": "You ARE Korea now. Legend status."},
]

XP_REWARDS = {
    "quiz_correct": 15,
    "quiz_attempt": 5,
    "challenge_done": 30,
    "word_learned": 5,
    "cook_recipe": 10,
    "practice_session": 20,
    "simulate_perfect": 30,
    "simulate_ok": 10,
    "tracker_log": 5,
    "daily_login": 10,
    "streak_bonus_7": 50,
    "streak_bonus_30": 200,
    "milestone_done": 25,
}


from db import get_conn as _get_conn


def setup_level_tables():
    with _get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS user_xp (
            user_id INTEGER PRIMARY KEY, total_xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1, title TEXT DEFAULT '신입생')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL, reason TEXT, earned_at TEXT)""")
        conn.commit()


def get_user_level(user_id):
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM user_xp WHERE user_id=?", (user_id,)).fetchone()
    if row:
        return dict(row)
    return {"user_id": user_id, "total_xp": 0, "level": 1, "title": "신입생"}


def add_xp(user_id, amount, reason=""):
    from datetime import datetime, UTC
    now = datetime.now(UTC).isoformat()
    with _get_conn() as conn:
        row = conn.execute("SELECT total_xp, level FROM user_xp WHERE user_id=?", (user_id,)).fetchone()
        if row:
            new_xp = row["total_xp"] + amount
            new_level = _calc_level(new_xp)
            conn.execute("UPDATE user_xp SET total_xp=?, level=?, title=? WHERE user_id=?",
                         (new_xp, new_level["level"], new_level["title"], user_id))
        else:
            new_xp = amount
            new_level = _calc_level(new_xp)
            conn.execute("INSERT INTO user_xp (user_id, total_xp, level, title) VALUES (?,?,?,?)",
                         (user_id, new_xp, new_level["level"], new_level["title"]))
        conn.execute("INSERT INTO xp_log (user_id, amount, reason, earned_at) VALUES (?,?,?,?)",
                     (user_id, amount, reason, now))
        conn.commit()
    old_level = dict(row)["level"] if row else 1
    leveled_up = new_level["level"] > old_level
    return {"new_xp": new_xp, "added": amount, "level": new_level, "leveled_up": leveled_up}


def _calc_level(xp):
    result = LEVELS[0]
    for lv in LEVELS:
        if xp >= lv["min_xp"]:
            result = lv
    return result


def format_level_status(user_id):
    data = get_user_level(user_id)
    xp = data["total_xp"]
    current = _calc_level(xp)
    # Find next level
    next_lv = None
    for lv in LEVELS:
        if lv["min_xp"] > xp:
            next_lv = lv
            break

    msg = f"🏆 Your Korea Level\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"{current['name']} — {current['title']}\n"
    msg += f"⭐ XP: {xp:,}\n\n"

    if next_lv:
        needed = next_lv["min_xp"] - xp
        progress = int((xp - current["min_xp"]) / (next_lv["min_xp"] - current["min_xp"]) * 10)
        bar = "█" * progress + "░" * (10 - progress)
        msg += f"Next: {next_lv['name']} ({next_lv['title']})\n"
        msg += f"[{bar}] {needed} XP needed\n"
        msg += f"🔓 Unlocks: {next_lv['perks']}\n\n"
    else:
        msg += "🎌 MAX LEVEL — You ARE Korea now! 🎌\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "Earn XP:\n"
    msg += "  /quiz — 15 XP per correct\n"
    msg += "  /challenge done — 30 XP\n"
    msg += "  /simulate — up to 30 XP\n"
    msg += "  /practice — 20 XP per session\n"
    msg += "  /cook — 10 XP per recipe\n"
    msg += "  Daily login — 10 XP"
    return msg


def format_levelup(level_data):
    lv = level_data["level"]
    return (
        f"🎉🎉🎉 LEVEL UP! 🎉🎉🎉\n\n"
        f"You reached {lv['name']}!\n"
        f"Title: {lv['title']}\n"
        f"🔓 Unlocked: {lv['perks']}\n\n"
        f"Keep going! 🚀"
    )
