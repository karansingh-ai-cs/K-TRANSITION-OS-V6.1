# config.py — K-Transition OS v6.0
# All settings live here. Put real keys in .env (never commit .env!)
# Paths are always computed from THIS file's location — works on Windows/Mac/Linux

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent      # always the project root
DATA_DIR = BASE_DIR / "data"                    # always points to data/ folder

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN_HERE")

# ── AI: Groq (primary) ────────────────────────────────────────────────────────
# Free key: console.groq.com — no credit card needed
# Can be a single key, or multiple keys separated by commas
_groq_keys_str = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEYS = [k.strip() for k in _groq_keys_str.split(",") if k.strip()]

import random
def get_groq_key():
    """Return a random Groq API key to load-balance and avoid rate limits."""
    return random.choice(GROQ_API_KEYS) if GROQ_API_KEYS else ""

GROQ_MODELS = [
    "llama-3.3-70b-versatile",    # Best, but strict limits (1K requests/day)
    "llama-3.1-8b-instant",       # Great fallback (14.4K requests/day)
    "gemma2-9b-it",               # Great fallback (14.4K requests/day)
    "mixtral-8x7b-32768"          # Final fallback (14.4K requests/day)
]
GROQ_LIGHT_MODEL = "llama-3.1-8b-instant"  # For simple tasks (quizzes, briefings) to save 70B quota

WHISPER_MODEL = "whisper-large-v3"             # for voice note transcription

# ── AI: Gemini (fallback + image vision) ─────────────────────────────────────
# Free key: aistudio.google.com — no credit card needed
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.0-flash-lite"       # lighter model, less quota burn

# ── Database ──────────────────────────────────────────────────────────────────
DB_FILE = BASE_DIR / os.getenv("DB_FILE", "ktransition.db")  # always absolute path

# ── News ──────────────────────────────────────────────────────────────────────
NEWS_CACHE_TIME  = 1800   # 30 minutes

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Feature Flags ─────────────────────────────────────────────────────────────
FEATURE_KOREAN_LESSONS = True
FEATURE_NEWS           = True
FEATURE_MAPS           = True
FEATURE_SCHEDULE       = True
FEATURE_IMAGE_AI       = True   # requires GEMINI_API_KEY
FEATURE_VOICE_NOTES    = True   # requires GROQ_API_KEY (Whisper)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
MAX_MESSAGES_PER_MINUTE = 15

# ── Bot Identity ──────────────────────────────────────────────────────────────
BOT_NAME    = "한국 선배 (Korean Senior)"
BOT_VERSION = "6.0"
