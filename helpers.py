# helpers.py — K-Transition OS v3.0
# Small utilities used across the whole bot.

import re
import time
import logging
import sys
from config import LOG_LEVEL

logger = logging.getLogger(__name__)


def setup_logging():
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stdout
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def clean_text(text: str) -> str:
    """Remove control chars and normalise whitespace."""
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', text)
    text = re.sub(r' {3,}', '  ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def short_summary(text: str, max_words: int = 8) -> str:
    words = text.split()[:max_words]
    s = " ".join(words)
    if len(text.split()) > max_words:
        s += "..."
    return s


def has_korean(text: str) -> bool:
    return bool(re.search(r'[\uAC00-\uD7A3]', text))


def chunk_text(text: str, max_len: int = 4000) -> list[str]:
    """Split text into Telegram-safe chunks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks


# ── Rate limiting (in-memory) ─────────────────────────────────────────────────

_user_times: dict[int, list[float]] = {}

def is_rate_limited(user_id: int, max_per_minute: int = 15) -> bool:
    now = time.time()
    times = [t for t in _user_times.get(user_id, []) if now - t < 60]
    if len(times) >= max_per_minute:
        return True
    times.append(now)
    _user_times[user_id] = times
    return False


# ── Validation ────────────────────────────────────────────────────────────────

VALID_DIETS = ["halal", "vegetarian", "vegan", "none", "kosher"]

def validate_diet(diet: str) -> tuple[bool, str]:
    d = diet.lower().strip()
    return (True, d) if d in VALID_DIETS else (False, f"Choose from: {', '.join(VALID_DIETS)}")


VALID_ALLERGIES = ["nuts", "peanut", "dairy", "gluten", "eggs", "fish", "shellfish", "soy", "sesame"]

def validate_allergy(allergy: str) -> tuple[bool, str]:
    a = allergy.lower().strip()
    if a in VALID_ALLERGIES:
        return True, a
    for v in VALID_ALLERGIES:
        if a in v or v in a:
            return True, v
    return False, f"Unknown. Common ones: {', '.join(VALID_ALLERGIES)}"


def format_risk_badge(risk: str) -> str:
    return {"HIGH": "🔴 HIGH RISK", "MEDIUM": "🟡 MEDIUM RISK", "LOW": "🟢 LOW RISK"}.get(risk, "⚪ UNKNOWN")
