# emotional_weather.py — K-Transition OS v4.0
# ═══════════════════════════════════════════════════════════
# THE "3 AM PROBLEM" DETECTOR
# ═══════════════════════════════════════════════════════════
#
# Problem: mental health crises don't appear suddenly.
# There's a long "functional suffering" stage before crisis —
# student is going to class, eating, replying — but slowly hollow.
#
# This module passively tracks behavioral signals WITHOUT being intrusive.
# No mood surveys. No "rate your day 1-10". Just pattern detection.
#
# Signals tracked:
#   • Message timing (late night = concerning signal)
#   • Frequency drop (going quiet)
#   • Topic shift toward distress keywords
#   • No personal messages — only task/info requests
#   • Not responding to check-ins
#
# When 2+ signals deteriorate → gentle check-in (NOT an alarm)
# Graduated support: peer connection → university resource → professional
#
# "We don't wait for the student to break. We notice before they do."

import json
import logging
from datetime import datetime, UTC, timedelta

logger = logging.getLogger(__name__)


# ── Distress signal keywords ──────────────────────────────────────────────────
DISTRESS_WORDS = [
    "lonely", "alone", "nobody", "no friends", "miss home", "homesick",
    "tired", "exhausted", "pointless", "give up", "pointless", "struggling",
    "can't sleep", "not sleeping", "crying", "cried", "sad", "depressed",
    "anxious", "anxious", "scared", "scared", "overwhelmed",
    "외롭다", "힘들다", "우울", "불안", "무서워", "지쳐",
]

# Personal topic words (healthy signal — user sharing life, not just asking)
PERSONAL_WORDS = [
    "today", "yesterday", "i went", "i ate", "i met", "my friend", "my class",
    "i feel", "i think", "i love", "i hate", "i enjoyed", "surprised me",
    "오늘", "어제", "나는", "내가",
]

# Pure task/info words (neutral-to-concerning if ONLY these appear)
TASK_WORDS = [
    "how to", "where is", "what is", "can you", "tell me", "show me",
    "what does", "how much", "do i need", "is it",
]


from db import get_conn as _get_conn


def setup_weather_tables():
    """Create tables for emotional weather tracking."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emotional_signals (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                signal_type  TEXT,
                value        REAL,
                timestamp    TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weather_checkins (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER,
                sent_at         TEXT,
                responded       INTEGER DEFAULT 0,
                response_text   TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weather_scores (
                user_id         INTEGER PRIMARY KEY,
                score           REAL DEFAULT 70.0,
                last_updated    TEXT,
                consecutive_low INTEGER DEFAULT 0
            )
        """)
        conn.commit()


def _log_signal(user_id: int, signal_type: str, value: float):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO emotional_signals (user_id, signal_type, value, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, signal_type, value, datetime.now(UTC).isoformat())
        )
        conn.commit()


def analyze_message(user_id: int, text: str):
    """
    Called on every message. Extracts signals silently.
    Does NOT read content for any other purpose.
    """
    text_lower = text.lower()
    now        = datetime.now(UTC)
    hour       = now.hour

    # Signal 1: Late night messaging (11pm-5am KST = concerning)
    # KST = UTC+9, so UTC 14:00-20:00 = KST 23:00-05:00
    if 14 <= hour <= 20:
        _log_signal(user_id, "late_night", 1.0)
    else:
        _log_signal(user_id, "late_night", 0.0)

    # Signal 2: Distress words
    distress_count = sum(1 for w in DISTRESS_WORDS if w in text_lower)
    if distress_count > 0:
        _log_signal(user_id, "distress_words", min(distress_count / 3.0, 1.0))

    # Signal 3: Personal sharing (healthy signal)
    personal_count = sum(1 for w in PERSONAL_WORDS if w in text_lower)
    if personal_count > 0:
        _log_signal(user_id, "personal_sharing", min(personal_count / 5.0, 1.0))

    # Signal 4: Pure task mode (no personal content)
    task_count     = sum(1 for w in TASK_WORDS if w in text_lower)
    is_pure_task   = task_count > 0 and personal_count == 0 and distress_count == 0
    _log_signal(user_id, "pure_task", 1.0 if is_pure_task else 0.0)

    # Recalculate score
    _recalculate_score(user_id)


def _recalculate_score(user_id: int):
    """
    Score 0-100. 100 = healthy, 0 = concerning.
    Uses last 7 days of signals.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT signal_type, value FROM emotional_signals WHERE user_id = ? AND timestamp > ?",
            (user_id, cutoff)
        ).fetchall()

    if not rows:
        return

    signals = {}
    for row in rows:
        t = row["signal_type"]
        if t not in signals:
            signals[t] = []
        signals[t].append(row["value"])

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    # Calculate weighted score
    score = 70.0  # baseline

    # Negative signals
    late_night_avg = avg(signals.get("late_night", []))
    score -= late_night_avg * 15

    distress_avg = avg(signals.get("distress_words", []))
    score -= distress_avg * 25

    pure_task_avg = avg(signals.get("pure_task", []))
    score -= pure_task_avg * 10

    # Positive signals
    personal_avg = avg(signals.get("personal_sharing", []))
    score += personal_avg * 15

    score = max(0.0, min(100.0, score))

    # Update score and consecutive_low counter
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT score, consecutive_low FROM weather_scores WHERE user_id = ?", (user_id,)
        ).fetchone()

        if existing:
            prev_score  = existing["score"]
            consec_low  = existing["consecutive_low"]
            new_consec  = consec_low + 1 if score < 45 else 0
            conn.execute(
                "UPDATE weather_scores SET score = ?, last_updated = ?, consecutive_low = ? WHERE user_id = ?",
                (score, datetime.now(UTC).isoformat(), new_consec, user_id)
            )
        else:
            conn.execute(
                "INSERT INTO weather_scores (user_id, score, last_updated, consecutive_low) VALUES (?, ?, ?, ?)",
                (user_id, score, datetime.now(UTC).isoformat(), 1 if score < 45 else 0)
            )
        conn.commit()


def log_message_time(user_id: int):
    """Track message frequency — silence can be a signal."""
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO emotional_signals (user_id, signal_type, value, timestamp) VALUES (?, 'active', 1.0, ?)",
            (user_id, datetime.now(UTC).isoformat())
        )
        conn.commit()


def get_weather_score(user_id: int) -> dict:
    """Return current emotional weather score and recommendation."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT score, last_updated, consecutive_low FROM weather_scores WHERE user_id = ?",
            (user_id,)
        ).fetchone()

    if not row:
        return {"score": 70, "status": "unknown", "consecutive_low": 0}

    score      = row["score"]
    consec_low = row["consecutive_low"]

    if score >= 65:
        status = "healthy"
    elif score >= 45:
        status = "monitor"
    elif score >= 25:
        status = "concerning"
    else:
        status = "critical"

    return {
        "score":          round(score, 1),
        "status":         status,
        "consecutive_low": consec_low,
        "last_updated":   row["last_updated"],
    }


def get_user_baseline(user_id: int) -> float:
    """
    ADAPTIVE ML FIX: Instead of fixed threshold (score < 45 for everyone),
    learn each user's personal baseline from their last 30 days of signals.
    A user who naturally scores 55 hitting 40 is more concerning than
    a user who normally scores 35 hitting 40.
    This is a simple Bayesian update: posterior = weighted average of
    prior (population mean=70) and observed (user's 30-day mean).
    """
    cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT score FROM weather_scores WHERE user_id = ? "
            "UNION ALL "
            "SELECT value FROM emotional_signals "
            "WHERE user_id = ? AND signal_type = 'personal_sharing' AND timestamp > ? LIMIT 30",
            (user_id, user_id, cutoff)
        ).fetchall()

    if not rows or len(rows) < 5:
        return 70.0  # not enough data — use population prior

    observed_scores = [r[0] for r in rows if r[0] is not None]
    if not observed_scores:
        return 70.0

    observed_mean = sum(observed_scores) / len(observed_scores)
    population_prior = 70.0
    # Bayesian weight: more observations = trust observed more
    n = len(observed_scores)
    weight_observed = min(n / 20.0, 0.8)  # max 80% weight on observed
    weight_prior    = 1.0 - weight_observed
    return (weight_prior * population_prior) + (weight_observed * observed_mean)


def should_checkin(user_id: int) -> tuple[bool, str]:
    """
    Returns (should_checkin, reason).
    ADAPTIVE THRESHOLD: trigger is personalised to this user's baseline.
    A drop of 20+ points below personal baseline triggers check-in,
    not a fixed score < 45. This prevents false positives for users
    whose natural baseline is lower, and catches drops for optimistic users.
    Don't send more than one check-in per 4 days to avoid alarm fatigue.
    """
    weather  = get_weather_score(user_id)
    score    = weather["score"]
    consec   = weather["consecutive_low"]
    baseline = get_user_baseline(user_id)
    drop     = baseline - score  # how far below personal baseline

    # Check last checkin time — alarm fatigue prevention
    with _get_conn() as conn:
        last = conn.execute(
            "SELECT sent_at FROM weather_checkins WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        ).fetchone()

    if last:
        try:
            last_dt = datetime.fromisoformat(last["sent_at"])
            if (datetime.now(UTC) - last_dt).days < 4:
                return False, ""
        except Exception:
            pass

    # Adaptive triggers
    if consec >= 3 and drop >= 15:
        return True, f"baseline_drop_{drop:.0f}pts_over_3days"
    if drop >= 25:
        return True, f"acute_drop_{drop:.0f}pts_below_baseline"
    if score < 25:
        return True, "absolute_critical"

    return False, ""


def record_checkin_sent(user_id: int) -> int:
    """Record that a check-in was sent. Returns checkin id."""
    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO weather_checkins (user_id, sent_at, responded) VALUES (?, ?, 0)",
            (user_id, datetime.now(UTC).isoformat())
        )
        conn.commit()
        return cur.lastrowid


def record_checkin_response(checkin_id: int, response: str):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE weather_checkins SET responded = 1, response_text = ? WHERE id = ?",
            (response[:500], checkin_id)
        )
        conn.commit()


def get_checkin_message(user_info: dict) -> str:
    """
    The "3 AM" intervention message.
    NOT alarming. NOT clinical. Just a human-feeling check-in.
    Graduated support embedded naturally.
    """
    name = user_info.get("first_name", "friend")
    return (
        f"Hey {name} — how's it going lately?\n\n"
        "Not asking for a status update. Just genuinely curious — "
        "anything interesting happening in Korea these days, or anything feeling heavy?\n\n"
        "Both are okay to share. I'm here either way. 💙"
    )


def get_peer_support_message(user_info: dict) -> str:
    """Second-level: suggest peer connection before professional resources."""
    city = user_info.get("city", "your city")
    uni  = user_info.get("university", "your university")
    return (
        "Something that actually helps more than most people expect:\n\n"
        "Talking to someone who's been through the same thing — not a counselor, "
        "just another student who survived the hard months.\n\n"
        f"The K-Transition community has students at every stage. "
        f"You can post anonymously if you want. Sometimes just knowing "
        f"someone else felt exactly this way makes it feel less permanent.\n\n"
        f"Also at {uni}: 학생상담센터 (Student Counseling Center) — "
        f"free, confidential, often has English speakers. "
        f"Just walking in and saying 'I haven't been doing well' is enough."
    )


def check_silence(user_id: int, days: int = 5) -> bool:
    """Returns True if user has been silent for {days} days."""
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM emotional_signals WHERE user_id = ? AND signal_type = 'active' AND timestamp > ?",
            (user_id, cutoff)
        ).fetchone()
    return row["cnt"] == 0 if row else True
