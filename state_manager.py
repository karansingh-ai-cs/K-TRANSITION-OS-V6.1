# state_manager.py — K-Transition OS v6.1
# Persistent State Machine — survives bot restarts
# States saved to DB, loaded on first message after restart

import time
import json
import logging

logger = logging.getLogger(__name__)

STATE_TIMEOUT = 600  # 10 min auto-expire (same as before)


class State:
    IDLE                     = "IDLE"
    COOK_WAITING_INGREDIENTS = "COOK_WAITING_INGREDIENTS"
    MAP_WAITING_QUERY        = "MAP_WAITING_QUERY"
    SIM_WAITING_CHOICE       = "SIM_WAITING_CHOICE"
    PRACTICE_ACTIVE          = "PRACTICE_ACTIVE"
    BUDDY_ACTIVE             = "BUDDY_ACTIVE"
    INTERPRET_WAITING_TEXT   = "INTERPRET_WAITING_TEXT"
    TRACK_WAITING_VALUE      = "TRACK_WAITING_VALUE"
    NEWS_WAITING_TOPIC       = "NEWS_WAITING_TOPIC"
    QUIZ_ACTIVE              = "QUIZ_ACTIVE"


# ── In-memory cache (fast) ────────────────────────────────────
_cache: dict[int, dict] = {}


# ── DB helpers ───────────────────────────────────────────────

def _setup_state_table():
    """Create user_states table if it doesn't exist."""
    try:
        from db import get_conn
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id    INTEGER PRIMARY KEY,
                    state      TEXT    DEFAULT 'IDLE',
                    context    TEXT    DEFAULT '{}',
                    updated_at REAL    DEFAULT 0
                )
            """)
    except Exception as e:
        logger.warning("Could not create user_states table: %s", e)


def _save_to_db(user_id: int, state: str, context: dict, ts: float):
    """Persist state to database."""
    try:
        from db import get_conn
        with get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO user_states
                   (user_id, state, context, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, state, json.dumps(context, default=str), ts)
            )
    except Exception as e:
        logger.warning("State save failed for user %d: %s", user_id, e)


def _load_from_db(user_id: int) -> dict | None:
    """Load state from database."""
    try:
        from db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT state, context, updated_at FROM user_states WHERE user_id = ?",
                (user_id,)
            ).fetchone()
        if not row:
            return None
        ts = float(row["updated_at"] or 0)
        if time.time() - ts > STATE_TIMEOUT:
            return None  # expired
        ctx = json.loads(row["context"] or "{}")
        # Don't restore buddy history from DB state — too large, use chat_history table
        if "history" in ctx and len(str(ctx.get("history", []))) > 2000:
            ctx["history"] = []
        return {"state": row["state"], "context": ctx, "timestamp": ts}
    except Exception as e:
        logger.warning("State load failed for user %d: %s", user_id, e)
        return None


def _delete_from_db(user_id: int):
    """Remove state from database."""
    try:
        from db import get_conn
        with get_conn() as conn:
            conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    except Exception as e:
        logger.warning("State delete failed: %s", e)


# ── Public API (same interface as before) ─────────────────────

def get_state(user_id: int) -> str:
    # Check cache first
    entry = _cache.get(user_id)
    if entry:
        if time.time() - entry["timestamp"] > STATE_TIMEOUT:
            _cache.pop(user_id, None)
            _delete_from_db(user_id)
            return State.IDLE
        return entry["state"]

    # Load from DB (after restart)
    db_entry = _load_from_db(user_id)
    if db_entry:
        _cache[user_id] = db_entry
        return db_entry["state"]

    return State.IDLE


def get_context(user_id: int) -> dict:
    entry = _cache.get(user_id)
    if entry:
        if time.time() - entry["timestamp"] > STATE_TIMEOUT:
            _cache.pop(user_id, None)
            return {}
        return entry.get("context", {})

    db_entry = _load_from_db(user_id)
    if db_entry:
        _cache[user_id] = db_entry
        return db_entry.get("context", {})

    return {}


def set_state(user_id: int, state: str, context: dict = None):
    ts = time.time()
    entry = {"state": state, "context": context or {}, "timestamp": ts}
    _cache[user_id] = entry
    _save_to_db(user_id, state, context or {}, ts)
    logger.debug("State %d → %s", user_id, state)


def update_context(user_id: int, **kwargs):
    entry = _cache.get(user_id)
    if entry:
        entry["context"].update(kwargs)
        entry["timestamp"] = time.time()
        _save_to_db(user_id, entry["state"], entry["context"], entry["timestamp"])


def clear_state(user_id: int):
    _cache.pop(user_id, None)
    _delete_from_db(user_id)


# ── Intent Override Logic (unchanged) ─────────────────────────

_INTENT_TO_PREFIX = {
    "cook": "COOK", "map": "MAP", "buddy": "BUDDY",
    "emotional_support": "BUDDY", "simulate": "SIM",
    "practice": "PRACTICE", "interpret": "INTERPRET",
    "track": "TRACK", "news": "NEWS", "quiz": "QUIZ",
}


def should_override(user_id: int, new_intent: str, confidence: float) -> bool:
    current = get_state(user_id)
    if current == State.IDLE:
        return True
    current_prefix = current.split("_")[0]
    new_prefix = _INTENT_TO_PREFIX.get(new_intent, "")
    if new_prefix and new_prefix == current_prefix:
        return False
    if current == State.BUDDY_ACTIVE:
        return confidence >= 0.85
    if current == State.PRACTICE_ACTIVE:
        return confidence >= 0.80
    return confidence >= 0.75


# Auto-setup table on import
_setup_state_table()
