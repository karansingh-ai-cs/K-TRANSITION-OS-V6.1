# config.py — K-Transition OS v6.0
# All settings live here. Put real keys in .env (never commit .env!)
# Paths are always computed from THIS file's location — works on Windows/Mac/Linux

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN_HERE")

# ── AI Provider Keys ──────────────────────────────────────────────────────────
# Strictly using ONE key per provider to respect TOS and avoid abuse flags.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").split(",")[0].strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").split(",")[0].strip()

def get_groq_key() -> str:
    return GROQ_API_KEY

def get_gemini_key() -> str:
    return GEMINI_API_KEY

def lock_groq_key(api_key: str) -> None:
    """Log a Groq 429 rate limit event. Single-key mode = no rotation, just log."""
    import logging
    logging.getLogger(__name__).warning("Groq 429 rate limit hit — backing off. Key: ...%s", api_key[-6:] if api_key else "none")

def lock_gemini_key(api_key: str) -> None:
    """Log a Gemini 429 rate limit event. Single-key mode = no rotation, just log."""
    import logging
    logging.getLogger(__name__).warning("Gemini 429 rate limit hit — backing off. Key: ...%s", api_key[-6:] if api_key else "none")


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TIER MODEL ROUTING ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
# Task              | Primary Model          | RPM | RPD    | TPM
# ------------------+------------------------+-----+--------+-----------
# Buddy/Casual Chat | Gemma 4 27B (Gemini)   |  15 | 1,500  | UNLIMITED
# Complex Questions | Qwen3-32B (Groq)       |  60 | 1,000  | 6K
# Quiz Generation   | LLaMA 3.1 8B (Groq)   |  30 | 14,400 | 6K
# Image Analysis    | Gemini 2.5 Flash       |   5 | 20     | 250K
# News Summaries    | LLaMA 3.1 8B (Groq)   |  30 | 14,400 | 6K
# Voice Transcribe  | Whisper Turbo (Groq)   |  20 | 2,000  | —

# ── GEMINI MODELS ─────────────────────────────────────────────────────────────
# Tier A: Unlimited TPM + 1500 RPD — PRIMARY buddy/casual workhorse
GEMINI_BUDDY_MODEL  = "gemma-4-27b-it"        # 15 RPM, Unlimited TPM, 1500 RPD
GEMINI_BUDDY_BACKUP = "gemma-4-31b-it"         # 15 RPM, Unlimited TPM, 1500 RPD
# Tier B: 500 RPD — moderate volume tasks
GEMINI_FLASH_LITE   = "gemini-3.1-flash-lite"  # 15 RPM, 250K TPM, 500 RPD
# Tier C: 20 RPD — SPARINGLY, vision/complex only
GEMINI_VISION_MODEL = "gemini-2.5-flash"       # 5 RPM, 250K TPM, 20 RPD — IMAGE ONLY
GEMINI_MODEL        = "gemini-2.5-flash-lite"  # 10 RPM, 250K TPM, 20 RPD — final fallback
# Tier D: Extra text fallbacks (5 RPM, 20 RPD each)
GEMINI_35_FLASH     = "gemini-3.5-flash"       # 5 RPM, 250K TPM, 20 RPD
GEMINI_3_FLASH      = "gemini-3-flash"         # 5 RPM, 250K TPM, 20 RPD

# TTS (Text-to-Speech) — for Negotiator voice output
GEMINI_TTS_MODEL    = "gemini-2.5-flash-tts"       # 3 RPM, 10 RPD, 10K TPM
GEMINI_TTS_BACKUP   = "gemini-3.1-flash-tts"       # 3 RPM, 10 RPD, 10K TPM (backup TTS)

# Live Audio Dialog — UNLIMITED RPM + RPD! For real-time Negotiator voice sessions
GEMINI_LIVE_MODEL   = "gemini-2.5-flash-live"      # Unlimited RPM, 1M TPM, Unlimited RPD
GEMINI_LIVE_BACKUP  = "gemini-3-flash-live"        # Unlimited RPM, 65K TPM, Unlimited RPD

# Embeddings — semantic search / FAQ matching (saves AI calls!)
GEMINI_EMBED_MODEL  = "gemini-embedding-2"         # 100 RPM, 30K TPM, 1K RPD
GEMINI_EMBED_BACKUP = "gemini-embedding-1"         # 100 RPM, 30K TPM, 1K RPD

# Image Generation — for quiz flashcards / cultural illustrations
IMAGEN_MODEL        = "imagen-4-fast-generate"     # 25 RPD — fast generation
IMAGEN_HQ_MODEL     = "imagen-4-generate"          # 25 RPD — higher quality

# ── GROQ MODELS ───────────────────────────────────────────────────────────────
GROQ_LIGHT_MODEL  = "openai/gpt-oss-20b"            # 30 RPM, 1K RPD — quiz/summaries
GROQ_FAST_MODEL   = "openai/gpt-oss-120b"           # 30 RPM, 1K RPD — primary complex workhorse
GROQ_HEAVY_MODEL  = "openai/gpt-oss-120b"           # 30 RPM, 1K RPD — deep reasoning
GROQ_SCOUT_MODEL  = "qwen/qwen3.6-27b"              # 30 RPM, 1K RPD — active Qwen replacement
GROQ_ARABIC_MODEL = "openai/gpt-oss-20b"            # 30 RPM, 1K RPD — Arabic fallback
GROQ_GPT120B      = "openai/gpt-oss-120b"           # 30 RPM, 1K RPD — extra complex reasoning
GROQ_GPT20B       = "openai/gpt-oss-20b"            # 30 RPM, 1K RPD — medium complexity
GROQ_GUARD_MODEL  = "meta-llama/llama-prompt-guard-2-86m"  # 30 RPM, 14.4K RPD — safety filter!

# Groq general fallback chain (tried in this order on 429/fail)
GROQ_MODELS = [
    GROQ_FAST_MODEL,    # gpt-oss-120b: primary complex reasoning
    GROQ_SCOUT_MODEL,   # qwen3.6-27b: active Qwen model
    GROQ_LIGHT_MODEL,   # gpt-oss-20b: lighter fast tasks
]

# ── Voice Transcription ───────────────────────────────────────────────────────
WHISPER_MODEL = "whisper-large-v3-turbo"   # 20 RPM, 2K RPD — faster than v3

# ── Database & Settings ───────────────────────────────────────────────────────
DB_FILE              = BASE_DIR / os.getenv("DB_FILE", "ktransition.db")
NEWS_CACHE_TIME      = 1800
LOG_LEVEL            = os.getenv("LOG_LEVEL", "INFO")
MAX_MESSAGES_PER_MINUTE = 15

# ── Feature Flags ─────────────────────────────────────────────────────────────
FEATURE_KOREAN_LESSONS = True
FEATURE_NEWS           = True
FEATURE_MAPS           = True
FEATURE_SCHEDULE       = True
FEATURE_IMAGE_AI       = True
FEATURE_VOICE_NOTES    = True

# ── Bot Identity ──────────────────────────────────────────────────────────────
BOT_NAME    = "한국 선배 (Korean Senior)"
BOT_VERSION = "6.0"

