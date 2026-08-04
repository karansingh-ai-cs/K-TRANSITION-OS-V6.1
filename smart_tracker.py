# smart_tracker.py — K-Transition OS v5.0
# Dynamic user-defined tracker — user says "track X" and bot creates it
import json, logging
from datetime import datetime, UTC
logger = logging.getLogger(__name__)

from db import get_conn as _get_conn

def setup_tracker_tables():
    with _get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS user_trackers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            name TEXT NOT NULL, emoji TEXT DEFAULT '📊', unit TEXT DEFAULT '',
            created_at TEXT NOT NULL, active INTEGER DEFAULT 1)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tracker_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tracker_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL, value REAL NOT NULL, note TEXT DEFAULT '',
            logged_at TEXT NOT NULL)""")
        conn.commit()

def create_tracker(user_id, name, emoji="📊", unit=""):
    now = datetime.now(UTC).isoformat()
    with _get_conn() as conn:
        cur = conn.execute("INSERT INTO user_trackers (user_id,name,emoji,unit,created_at) VALUES (?,?,?,?,?)",
            (user_id, name, emoji, unit, now))
        conn.commit()
        return cur.lastrowid

def log_entry(user_id, tracker_id, value, note=""):
    now = datetime.now(UTC).isoformat()
    with _get_conn() as conn:
        conn.execute("INSERT INTO tracker_entries (tracker_id,user_id,value,note,logged_at) VALUES (?,?,?,?,?)",
            (tracker_id, user_id, value, note, now))
        conn.commit()

def get_user_trackers(user_id):
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM user_trackers WHERE user_id=? AND active=1 ORDER BY created_at DESC",(user_id,)).fetchall()
    return [dict(r) for r in rows]

def get_tracker_by_name(user_id, name):
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM user_trackers WHERE user_id=? AND LOWER(name)=LOWER(?) AND active=1",(user_id,name)).fetchone()
    return dict(row) if row else None

def get_tracker_entries(tracker_id, limit=30):
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM tracker_entries WHERE tracker_id=? ORDER BY logged_at DESC LIMIT ?",(tracker_id,limit)).fetchall()
    return [dict(r) for r in rows]

def get_tracker_stats(tracker_id):
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as count, SUM(value) as total, AVG(value) as avg, MIN(value) as min, MAX(value) as max FROM tracker_entries WHERE tracker_id=?",(tracker_id,)).fetchone()
    return dict(row) if row else {"count":0,"total":0,"avg":0,"min":0,"max":0}

def delete_tracker(user_id, tracker_id):
    with _get_conn() as conn:
        conn.execute("UPDATE user_trackers SET active=0 WHERE id=? AND user_id=?",(tracker_id,user_id))
        conn.commit()

TRACKER_EMOJIS = {"spend":"💸","money":"💰","expense":"💸","budget":"💰","sleep":"😴","water":"💧","study":"📚","exercise":"🏃","gym":"💪","mood":"😊","food":"🍽️","weight":"⚖️","coffee":"☕","korean":"🇰🇷","save":"🏦","work":"💼"}
TRACKER_UNITS = {"spend":"₩","money":"₩","expense":"₩","budget":"₩","sleep":"hours","water":"cups","study":"hours","exercise":"min","gym":"min","weight":"kg","coffee":"cups","save":"₩","work":"hours"}

def guess_emoji(name):
    for kw, em in TRACKER_EMOJIS.items():
        if kw in name.lower(): return em
    return "📊"

def guess_unit(name):
    for kw, un in TRACKER_UNITS.items():
        if kw in name.lower(): return un
    return ""

def format_tracker_list(trackers):
    if not trackers:
        return "📊 No trackers yet!\n\n/track new [name]\n\nExamples:\n• /track new spending\n• /track new sleep\n• /track new study hours\n• /track new mood\n\nTrack ANYTHING — the bot adapts to you!"
    msg = "📊 Your Trackers\n\n"
    for t in trackers:
        msg += f"{t['emoji']} {t['name']}"
        if t['unit']: msg += f" ({t['unit']})"
        msg += f" — #{t['id']}\n"
    msg += "\nLog: /track [name] [value]\nStats: /track stats [name]\nNew: /track new [name]"
    return msg

def format_tracker_stats(tracker, stats, recent):
    msg = f"{tracker['emoji']} {tracker['name']} — Stats\n\n"
    if stats['count'] == 0:
        return msg + f"No entries yet! /track {tracker['name'].lower()} [value]"
    u = tracker.get('unit','')
    msg += f"📈 Entries: {stats['count']}\n📊 Total: {stats['total']:,.1f} {u}\n📉 Avg: {stats['avg']:,.1f} {u}\n⬆️ Max: {stats['max']:,.1f} {u}\n⬇️ Min: {stats['min']:,.1f} {u}\n"
    if recent:
        msg += f"\n📋 Recent:\n"
        for e in recent[:5]:
            note = f" — {e['note']}" if e.get('note') else ""
            msg += f"  {e['logged_at'][:10]}: {e['value']:,.1f} {u}{note}\n"
    return msg

def get_today_total(user_id, tracker_id):
    import datetime
    today_start = datetime.datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    with _get_conn() as conn:
        row = conn.execute("SELECT SUM(value) FROM tracker_entries WHERE user_id=? AND tracker_id=? AND logged_at >= ?", (user_id, tracker_id, today_start)).fetchone()
    return row[0] if row and row[0] is not None else 0.0

def get_yesterday_total(user_id, tracker_id):
    import datetime
    now_utc = datetime.datetime.now(datetime.UTC)
    yesterday_start = (now_utc - datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    with _get_conn() as conn:
        row = conn.execute("SELECT SUM(value) FROM tracker_entries WHERE user_id=? AND tracker_id=? AND logged_at >= ? AND logged_at < ?", (user_id, tracker_id, yesterday_start, today_start)).fetchone()
    return row[0] if row and row[0] is not None else 0.0

def get_week_total(user_id, tracker_id):
    import datetime
    now_utc = datetime.datetime.now(datetime.UTC)
    weekday = now_utc.weekday()
    week_start = (now_utc - datetime.timedelta(days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    with _get_conn() as conn:
        row = conn.execute("SELECT SUM(value) FROM tracker_entries WHERE user_id=? AND tracker_id=? AND logged_at >= ?", (user_id, tracker_id, week_start)).fetchone()
    return row[0] if row and row[0] is not None else 0.0

def get_month_total(user_id, tracker_id):
    import datetime
    month_start = datetime.datetime.now(datetime.UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    with _get_conn() as conn:
        row = conn.execute("SELECT SUM(value) FROM tracker_entries WHERE user_id=? AND tracker_id=? AND logged_at >= ?", (user_id, tracker_id, month_start)).fetchone()
    return row[0] if row and row[0] is not None else 0.0

def format_spending_summary(user_id, period):
    tracker = get_tracker_by_name(user_id, "spending")
    if not tracker:
        tracker = get_tracker_by_name(user_id, "expense")
    if not tracker:
        all_t = get_user_trackers(user_id)
        for t in all_t:
            if "spend" in t['name'].lower() or "expense" in t['name'].lower():
                tracker = t
                break

    if not tracker:
        return "💰 No spending or expense tracker has been created yet. You can log expenses automatically with natural sentences, like: 'I spent 5000 won on coffee'."

    tracker_id = tracker['id']
    emoji = tracker.get('emoji', '💸')
    unit = tracker.get('unit', '₩')
    name = tracker['name']

    period = period.lower().strip()
    if period == "today":
        val = get_today_total(user_id, tracker_id)
        return f"{emoji} Today's total {name}: {val:,.0f} {unit}"
    elif period == "yesterday":
        val = get_yesterday_total(user_id, tracker_id)
        return f"{emoji} Yesterday's total {name}: {val:,.0f} {unit}"
    elif period == "week":
        val = get_week_total(user_id, tracker_id)
        return f"{emoji} This week's total {name}: {val:,.0f} {unit}"
    elif period == "month":
        val = get_month_total(user_id, tracker_id)
        return f"{emoji} This month's total {name}: {val:,.0f} {unit}"
    else:
        today_val = get_today_total(user_id, tracker_id)
        yest_val = get_yesterday_total(user_id, tracker_id)
        week_val = get_week_total(user_id, tracker_id)
        month_val = get_month_total(user_id, tracker_id)
        return (f"{emoji} {name.capitalize()} Summary:\n"
                f"• Today: {today_val:,.0f} {unit}\n"
                f"• Yesterday: {yest_val:,.0f} {unit}\n"
                f"• This Week: {week_val:,.0f} {unit}\n"
                f"• This Month: {month_val:,.0f} {unit}")
