# memory.py — K-Transition OS v3.0
# All SQLite persistence. WAL mode = no "database is locked" errors.
# Stores: user profiles, conversation history, situations, progress, custom features.

import json
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 6   # Reduce history to 6 messages to save API tokens heavily


from config import DB_FILE
from db import get_conn  # noqa: F401 — imported here so all memory.py code uses it


def setup(db_path=None):
    """Create all tables if they don't exist. Safe to call on every startup."""
    global DB_FILE
    if db_path:
        from pathlib import Path
        DB_FILE = Path(db_path)

    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT    DEFAULT '',
                first_name   TEXT    DEFAULT '',
                diet         TEXT    DEFAULT 'none',
                allergies    TEXT    DEFAULT '[]',
                university   TEXT    DEFAULT '',
                city         TEXT    DEFAULT '',
                language     TEXT    DEFAULT 'en',
                streak       INTEGER DEFAULT 0,
                last_active  TEXT    DEFAULT '',
                arrival_date TEXT    DEFAULT '',
                created_at   TEXT    DEFAULT '',
                onboarding_step INTEGER DEFAULT -1
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER,
                role      TEXT,
                content   TEXT,
                timestamp TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS situations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER,
                category  TEXT,
                risk      TEXT,
                summary   TEXT,
                rule_id   TEXT,
                timestamp TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                user_id       INTEGER PRIMARY KEY,
                korean_words  INTEGER DEFAULT 0,
                quiz_correct  INTEGER DEFAULT 0,
                quiz_total    INTEGER DEFAULT 0,
                quiz_level    INTEGER DEFAULT 1,
                tasks_done    TEXT    DEFAULT '[]',
                badges        TEXT    DEFAULT '[]'
            )
        """)

        # Personal tasks (/task add ...)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                title      TEXT,
                due_time   TEXT    DEFAULT '',
                due_date   TEXT    DEFAULT '',
                done       INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # ARCHITECTURAL FIX: Decoupled notification queue.
        # FastAPI process writes here. Bot process reads and sends.
        # Solves the 3-event-loop conflict without Redis (which costs money).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_notifications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                message    TEXT    NOT NULL,
                sent       INTEGER DEFAULT 0,
                created_at TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_unsent "
            "ON pending_notifications(sent, created_at)"
        )

        # User settings — Mini App preferences (currency, theme, onboarding flag)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id        INTEGER PRIMARY KEY,
                home_currency  TEXT    DEFAULT 'USD',
                home_country   TEXT    DEFAULT '',
                notifications  INTEGER DEFAULT 1,
                theme          TEXT    DEFAULT 'dark',
                onboarded_app  INTEGER DEFAULT 0,
                updated_at     TEXT    DEFAULT ''
            )
        """)

        # Checklist progress — arrival survival checklist tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_progress (
                user_id    INTEGER,
                item_id    TEXT,
                done       INTEGER DEFAULT 0,
                done_at    TEXT    DEFAULT '',
                PRIMARY KEY (user_id, item_id)
            )
        """)

        # Nudge cards — proactive contextual nudges shown once
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nudge_log (
                user_id    INTEGER,
                nudge_id   TEXT,
                shown_at   TEXT,
                dismissed  INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, nudge_id)
            )
        """)

        # Voice AI Negotiator MiniApp tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS negotiator_sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       TEXT,
                session_date  TEXT,
                goal          TEXT,
                type          TEXT,
                outcome       TEXT,
                duration_mins REAL,
                score         INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS negotiator_stats (
                user_id        TEXT PRIMARY KEY,
                total_sessions INTEGER DEFAULT 0,
                total_wins     INTEGER DEFAULT 0,
                total_duration REAL    DEFAULT 0.0,
                avg_score      REAL    DEFAULT 0.0
            )
        """)

        # NOTE: user_levels table removed — XP is managed solely by level_system.py (user_xp table)

        # Check existing columns first to avoid logging false duplicate column error messages
        cursor = conn.execute("PRAGMA table_info(users)")
        existing_cols = [row["name"] for row in cursor.fetchall()]

        # Add affection score dynamically if it doesn't exist
        if "affection_score" not in existing_cols:
            try:
                conn.execute("ALTER TABLE users ADD COLUMN affection_score INTEGER DEFAULT 0")
            except Exception:
                pass

        # Self-Updating Memory: Add new profile columns for conversational learning
        for col, default in [("visa_type", "''"), ("major", "''"), ("age", "''"), ("country", "''")]:
            if col not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT {default}")
                except Exception:
                    pass

        conn.commit()

    # Automatically initialize other component tables
    try:
        from level_system import setup_level_tables
        setup_level_tables()
    except Exception as e:
        logger.warning("Could not setup level tables: %s", e)

    try:
        from smart_tracker import setup_tracker_tables
        setup_tracker_tables()
    except Exception as e:
        logger.warning("Could not setup tracker tables: %s", e)

    try:
        from emotional_weather import setup_weather_tables
        setup_weather_tables()
    except Exception as e:
        logger.warning("Could not setup weather tables: %s", e)

    try:
        from bridge_builder import setup_bridge_tables
        setup_bridge_tables()
    except Exception as e:
        logger.warning("Could not setup bridge tables: %s", e)

    try:
        from community_bot import setup_community_tables
        setup_community_tables()
    except Exception as e:
        logger.warning("Could not setup community tables: %s", e)

    logger.info("Database ready at %s", DB_FILE)


# ── User CRUD ─────────────────────────────────────────────────────────────────

def get_user(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    user = dict(row)
    user["allergies"] = json.loads(user.get("allergies", "[]"))
    return user


def get_or_create_user(user_id, username="", first_name=""):
    user = get_user(user_id)
    if user:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET last_active = ? WHERE user_id = ?",
                (datetime.now(UTC).isoformat(), user_id)
            )
        return user

    now = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (user_id, username, first_name, diet, allergies,
               streak, last_active, created_at, onboarding_step)
               VALUES (?, ?, ?, 'none', '[]', 0, ?, ?, 0)""",
            (user_id, username, first_name, now, now)
        )
        conn.commit()
    logger.info("New user: %d (%s)", user_id, first_name)
    return get_user(user_id)


def update_user(user_id, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        conn.commit()


def set_diet(user_id, diet):
    update_user(user_id, diet=diet.lower().strip())

def add_allergy(user_id, allergy):
    user = get_user(user_id)
    if not user:
        return
    allergies = user.get("allergies", [])
    allergy = allergy.lower().strip()
    if allergy not in allergies:
        allergies.append(allergy)
    update_user(user_id, allergies=json.dumps(allergies))

def remove_allergy(user_id, allergy):
    user = get_user(user_id)
    if not user:
        return
    allergies = [a for a in user.get("allergies", []) if a != allergy.lower()]
    update_user(user_id, allergies=json.dumps(allergies))

def set_university(user_id, uni):
    update_user(user_id, university=uni)

def set_city(user_id, city):
    update_user(user_id, city=city)

def set_arrival_date(user_id, date_str):
    update_user(user_id, arrival_date=date_str)

def set_onboarding_step(user_id, step):
    update_user(user_id, onboarding_step=step)

def get_affection(user_id):
    user = get_user(user_id)
    return user.get("affection_score", 0) if user else 0

def update_affection(user_id, amount):
    """Add or subtract affection score. Bounded between -100 and 100."""
    current = get_affection(user_id)
    new_score = max(-100, min(100, current + amount))
    update_user(user_id, affection_score=new_score)
    return new_score


# ── Conversation History ───────────────────────────────────────────────────────

def save_message(user_id, role, content):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, role, str(content)[:2000], datetime.now(UTC).isoformat())
        )
        conn.execute(
            """DELETE FROM chat_history WHERE user_id = ? AND role IN ('user', 'assistant') AND id NOT IN (
               SELECT id FROM chat_history WHERE user_id = ? AND role IN ('user', 'assistant')
               ORDER BY id DESC LIMIT ?)""",
            (user_id, user_id, MAX_HISTORY_LENGTH)
        )
        conn.commit()


def get_history(user_id, limit=6):
    """Get conversation history. Uses last `limit` messages for AI context."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT role, content FROM chat_history
               WHERE user_id = ? AND role IN ('user', 'assistant') ORDER BY id DESC LIMIT ?""",
            (user_id, limit)
        ).fetchall()
    # Reverse so oldest first (correct order for AI)
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def save_buddy_message(user_id, role, content):
    """Save buddy conversation separately to avoid OS AI confusion."""
    buddy_role = f"buddy_{role}"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, buddy_role, str(content)[:2000], datetime.now(UTC).isoformat())
        )
        conn.execute(
            """DELETE FROM chat_history WHERE user_id = ? AND role LIKE 'buddy_%' AND id NOT IN (
               SELECT id FROM chat_history WHERE user_id = ? AND role LIKE 'buddy_%'
               ORDER BY id DESC LIMIT ?)""",
            (user_id, user_id, MAX_HISTORY_LENGTH)
        )
        conn.commit()


def get_buddy_history(user_id, limit=6):
    """Get only the buddy conversation history."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT role, content FROM chat_history
               WHERE user_id = ? AND role LIKE 'buddy_%' ORDER BY id DESC LIMIT ?""",
            (user_id, limit)
        ).fetchall()
    return [
        {"role": "user" if r["role"] == "buddy_user" else "assistant", "content": r["content"]}
        for r in reversed(rows)
    ]


def clear_history(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        conn.commit()


# ── Situation Log ─────────────────────────────────────────────────────────────

def log_situation(user_id, category, risk, summary, rule_id=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO situations (user_id, category, risk, summary, rule_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, category, risk, summary[:200], rule_id,
             datetime.now(UTC).strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()


def get_situations(user_id, limit=5):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, risk, summary, rule_id, timestamp FROM situations "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Progress / Gamification ───────────────────────────────────────────────────

def get_progress(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM progress WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        with get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO progress (user_id) VALUES (?)", (user_id,))
            conn.commit()
        return {"user_id": user_id, "korean_words": 0, "quiz_correct": 0,
                "quiz_total": 0, "quiz_level": 1, "tasks_done": [], "badges": []}
    p = dict(row)
    p["tasks_done"] = json.loads(p.get("tasks_done", "[]"))
    p["badges"]     = json.loads(p.get("badges", "[]"))
    return p


def add_korean_word_learned(user_id):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO progress (user_id) VALUES (?)", (user_id,))
        conn.execute("UPDATE progress SET korean_words = korean_words + 1 WHERE user_id = ?", (user_id,))
        conn.commit()


def record_quiz_answer(user_id, correct: bool):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO progress (user_id) VALUES (?)", (user_id,))
        if correct:
            conn.execute(
                "UPDATE progress SET quiz_correct = quiz_correct + 1, quiz_total = quiz_total + 1 WHERE user_id = ?",
                (user_id,)
            )
        else:
            conn.execute(
                "UPDATE progress SET quiz_total = quiz_total + 1 WHERE user_id = ?",
                (user_id,)
            )
        conn.commit()
    # Level up every 10 correct answers
    p = get_progress(user_id)
    if correct and p["quiz_correct"] > 0 and p["quiz_correct"] % 10 == 0:
        new_level = min(p["quiz_level"] + 1, 5)
        with get_conn() as conn:
            conn.execute("UPDATE progress SET quiz_level = ? WHERE user_id = ?", (new_level, user_id))
            conn.commit()


def get_quiz_level(user_id) -> int:
    return get_progress(user_id).get("quiz_level", 1)


def mark_task_done(user_id, task_id):
    p = get_progress(user_id)
    tasks = p.get("tasks_done", [])
    if task_id not in tasks:
        tasks.append(task_id)
        with get_conn() as conn:
            conn.execute(
                "UPDATE progress SET tasks_done = ? WHERE user_id = ?",
                (json.dumps(tasks), user_id)
            )
            conn.commit()


def update_streak(user_id) -> int:
    user = get_user(user_id)
    if not user:
        return 0
    last_active = user.get("last_active", "")
    now = datetime.now(UTC)
    try:
        last = datetime.fromisoformat(last_active)
        days_diff = (now.date() - last.date()).days
        streak = user.get("streak", 0)
        if days_diff == 0:
            return streak
        elif days_diff == 1:
            new_streak = streak + 1
        else:
            new_streak = 1
    except Exception:
        new_streak = 1
    update_user(user_id, streak=new_streak)
    return new_streak


# ── Personal Tasks (/task commands) ───────────────────────────────────────────

def add_task(user_id, title, due_time="", due_date="") -> int:
    now = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (user_id, title, due_time, due_date, done, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (user_id, title, due_time, due_date, now)
        )
        conn.commit()
        return cur.lastrowid


def get_tasks(user_id, include_done=False):
    with get_conn() as conn:
        if include_done:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC", (user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND done = 0 ORDER BY id DESC", (user_id,)
            ).fetchall()
    return [dict(r) for r in rows]


def complete_task(user_id, task_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ?", (task_id, user_id)
        )
        conn.commit()


def delete_task(user_id, task_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()


# ── User Settings (Mini App preferences) ──────────────────────────────────────

def get_user_settings(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return dict(row)
    # Create defaults
    now = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_settings (user_id, updated_at) VALUES (?, ?)",
            (user_id, now)
        )
        conn.commit()
    return {"user_id": user_id, "home_currency": "USD", "home_country": "",
            "notifications": 1, "theme": "dark", "onboarded_app": 0}


def update_user_settings(user_id, **kwargs):
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.now(UTC).isoformat()
    # Ensure row exists
    get_user_settings(user_id)
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE user_settings SET {fields} WHERE user_id = ?", values)
        conn.commit()


# ── Checklist Progress (Arrival survival tracking) ────────────────────────────

ARRIVAL_CHECKLIST = [
    {"id": "sim_card",         "title": "Get SIM Card",              "phase": "Day 1",    "emoji": "📱", "priority": "high"},
    {"id": "tmoney",           "title": "Get T-Money Card",          "phase": "Day 1-2",  "emoji": "🚌", "priority": "high"},
    {"id": "apps_setup",       "title": "Install Naver/Kakao/Papago","phase": "Day 1-2",  "emoji": "📲", "priority": "high"},
    {"id": "trash_learn",      "title": "Learn Trash Sorting System","phase": "Day 2-3",  "emoji": "🗑️", "priority": "medium"},
    {"id": "campus_cafeteria", "title": "Find Campus Cafeteria",     "phase": "Day 2-3",  "emoji": "🍽️", "priority": "medium"},
    {"id": "arc_booking",      "title": "Book ARC Appointment",      "phase": "Week 2",   "emoji": "🏛️", "priority": "critical"},
    {"id": "bank_account",     "title": "Open Korean Bank Account",  "phase": "Week 2",   "emoji": "🏦", "priority": "high"},
    {"id": "jumin_register",   "title": "Register at 주민센터",       "phase": "Within 14d","emoji": "🏢", "priority": "critical"},
    {"id": "halal_map",        "title": "Map Halal Food Options",    "phase": "Week 1",   "emoji": "🕌", "priority": "medium", "condition_diet": "halal"},
    {"id": "emergency_save",   "title": "Save Emergency Numbers",    "phase": "Day 1",    "emoji": "🚨", "priority": "high"},
    {"id": "health_insurance",  "title": "Check Health Insurance",   "phase": "Month 1",  "emoji": "🏥", "priority": "medium"},
    {"id": "korean_greeting",  "title": "Say 안녕하세요 to Someone",  "phase": "Week 1",   "emoji": "🇰🇷", "priority": "low"},
]


def get_checklist(user_id, diet="none"):
    """Return full checklist with user's completion status."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT item_id, done, done_at FROM checklist_progress WHERE user_id = ?",
            (user_id,)
        ).fetchall()
    done_map = {r["item_id"]: {"done": r["done"], "done_at": r["done_at"]} for r in rows}

    result = []
    for item in ARRIVAL_CHECKLIST:
        # Filter diet-specific items
        if item.get("condition_diet") and item["condition_diet"] != diet:
            continue
        status = done_map.get(item["id"], {"done": 0, "done_at": ""})
        result.append({
            **item,
            "done": bool(status["done"]),
            "done_at": status["done_at"],
        })
    return result


def complete_checklist_item(user_id, item_id):
    """Mark a checklist item as done. Returns True if it was newly completed."""
    now = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT done FROM checklist_progress WHERE user_id = ? AND item_id = ?",
            (user_id, item_id)
        ).fetchone()
        if existing and existing["done"]:
            return False  # already done
        conn.execute(
            "INSERT OR REPLACE INTO checklist_progress (user_id, item_id, done, done_at) VALUES (?, ?, 1, ?)",
            (user_id, item_id, now)
        )
        conn.commit()
    # Award XP for completing checklist items
    xp_map = {"critical": 50, "high": 30, "medium": 20, "low": 10}
    item = next((i for i in ARRIVAL_CHECKLIST if i["id"] == item_id), None)
    if item:
        add_xp(user_id, xp_map.get(item.get("priority", "low"), 10), f"checklist:{item_id}")
    return True


def uncomplete_checklist_item(user_id, item_id):
    """Uncheck a checklist item (toggle support)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE checklist_progress SET done = 0, done_at = '' WHERE user_id = ? AND item_id = ?",
            (user_id, item_id)
        )
        conn.commit()


# ── Nudge Log (Show contextual cards only once) ───────────────────────────────

def has_seen_nudge(user_id, nudge_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT dismissed FROM nudge_log WHERE user_id = ? AND nudge_id = ?",
            (user_id, nudge_id)
        ).fetchone()
    return bool(row)


def mark_nudge_shown(user_id, nudge_id):
    now = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO nudge_log (user_id, nudge_id, shown_at) VALUES (?, ?, ?)",
            (user_id, nudge_id, now)
        )
        conn.commit()


def dismiss_nudge(user_id, nudge_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE nudge_log SET dismissed = 1 WHERE user_id = ? AND nudge_id = ?",
            (user_id, nudge_id)
        )
        conn.commit()


# ── XP / Level System (Gamified progression) ──────────────────────────────────

LEVEL_THRESHOLDS = [
    {"level": 1,  "xp": 0,    "title": "Newcomer 🌱",       "personas": ["korea_senior"]},
    {"level": 2,  "xp": 100,  "title": "Explorer 🧭",        "personas": ["korea_senior", "seoul_guide"]},
    {"level": 3,  "xp": 300,  "title": "Adapter 🌿",         "personas": ["korea_senior", "seoul_guide", "food_detective"]},
    {"level": 4,  "xp": 600,  "title": "Connected 🌉",       "personas": ["korea_senior", "seoul_guide", "food_detective", "culture_mentor"]},
    {"level": 5,  "xp": 1000, "title": "Integrated 🌳",      "personas": ["korea_senior", "seoul_guide", "food_detective", "culture_mentor", "career_coach"]},
    {"level": 6,  "xp": 1500, "title": "Korea Veteran 🏆",   "personas": ["korea_senior", "seoul_guide", "food_detective", "culture_mentor", "career_coach", "legal_advisor"]},
    {"level": 7,  "xp": 2500, "title": "한국 마스터 👑",      "personas": ["korea_senior", "seoul_guide", "food_detective", "culture_mentor", "career_coach", "legal_advisor", "life_philosopher"]},
]


def get_user_level(user_id):
    """Delegate to level_system."""
    from level_system import get_user_level as _ls_get
    return _ls_get(user_id)


def add_xp(user_id, amount, reason=""):
    """Delegate to level_system to avoid dual XP tracking."""
    from level_system import add_xp as _ls_add_xp
    return _ls_add_xp(user_id, amount, reason)
