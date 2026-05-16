# config.py — K-Transition OS v3.0
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
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"       # best free model as of 2025
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
BOT_VERSION = "5.0"
