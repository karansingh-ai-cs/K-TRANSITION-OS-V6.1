# 🏗️ K-Transition OS — Architecture Map

> **Version:** 6.0 · **Status:** Production-Grade Student Companion
> **Stack:** Python 3.12 · Telegram Bot API · Groq/Gemini AI · Turso Cloud DB · FastAPI

---

## 📂 Project Tree

```
ktransition/
│
├── 🧠 CORE ENGINE ──────────────────────────────────────────
│   ├── bot.py                    # 🎯 MAIN ENTRY POINT (2309 lines)
│   │   ├── Telegram Application boot & polling
│   │   ├── 40+ command handlers (/start, /quiz, /cook, /map...)
│   │   ├── Persistent ReplyKeyboard (12-button grid)
│   │   ├── Onboarding wizard (5-step profile setup)
│   │   ├── State-aware message router (delegates to _handle_active_state)
│   │   ├── Intent executor (LLM-classified natural language → action)
│   │   ├── process_message() — full AI pipeline with risk scan
│   │   └── FastAPI thread (serves Negotiator on PORT 10000)
│   │
│   ├── config.py                 # ⚙️ CONFIGURATION HUB
│   │   ├── Environment loader (.env → os.getenv)
│   │   ├── Single-key TOS-compliant API management
│   │   ├── Multi-tier model routing table (13 Gemini + 8 Groq models)
│   │   ├── Feature flags (FEATURE_NEWS, FEATURE_MAPS, etc.)
│   │   └── Path resolution (BASE_DIR, DATA_DIR)
│   │
│   ├── ai_brain.py               # 🧠 AI ROUTING ENGINE (638 lines)
│   │   ├── KOREA_SYSTEM_PROMPT — "Korean Senior" persona (109 lines)
│   │   ├── _detect_task() — keyword classifier (buddy vs complex)
│   │   ├── check_message_safety() — LLaMA Prompt Guard jailbreak filter
│   │   ├── _call_gemini_model() — unified Gemini caller + context pruning
│   │   ├── _call_groq_model() — unified Groq caller + tool calling
│   │   ├── _route_buddy() — 6-tier Gemini cascade (Gemma→Flash→fallbacks)
│   │   ├── _route_complex() — 5-tier Groq cascade (Qwen→Scout→GPT→LLaMA)
│   │   ├── ask_ai() — MAIN ENTRY: safety→task detect→route→respond
│   │   ├── generate_quiz_question() — structured JSON quiz via LLaMA 8B
│   │   ├── analyze_image() — Gemini 2.5 Flash vision (food labels, signs)
│   │   ├── transcribe_audio() — Groq Whisper (voice notes → text)
│   │   ├── call_gemini() — legacy wrapper with Smart Interceptor
│   │   └── call_groq() — legacy wrapper with Smart Interceptor
│   │
│   ├── intent_router.py          # 🎯 LLM INTENT CLASSIFIER
│   │   ├── 25+ intent categories (cook, map, buddy, visa, quiz...)
│   │   ├── Entity extraction (ingredients, destinations, moods)
│   │   ├── Korean query auto-translation for map intents
│   │   ├── Quick pre-filter (single-word → skip LLM call)
│   │   └── Keyword fallback when LLM fails
│   │
│   └── state_manager.py          # 🔄 CONVERSATION STATE MACHINE
│       ├── 10 states (IDLE, COOK_WAITING, BUDDY_ACTIVE, QUIZ_ACTIVE...)
│       ├── DB-persisted states (survives restarts)
│       ├── In-memory cache (fast reads)
│       ├── 10-minute auto-expiry
│       └── Intent override logic (confidence-based state switching)
│
├── 💾 DATA LAYER ───────────────────────────────────────────
│   ├── db.py                     # 🗄️ UNIVERSAL DB CONNECTOR
│   │   ├── _TursoHTTPConnection — cloud DB via HTTP pipeline API
│   │   ├── _SQLiteConnection — local dev fallback
│   │   ├── get_conn() — auto-selects Turso or SQLite
│   │   ├── _DictRow — sqlite3.Row-compatible interface
│   │   └── check_connection() — health check
│   │
│   ├── memory.py                 # 📝 PERSISTENCE LAYER (617 lines)
│   │   ├── 8 DB tables (users, chat_history, situations, progress...)
│   │   ├── User CRUD (get_or_create_user, update_user, set_diet...)
│   │   ├── Chat history (save/get/clear + MAX_HISTORY_LENGTH=6)
│   │   ├── Buddy history (separate table for Minsu conversations)
│   │   ├── Situation logging (risk events for portfolio)
│   │   ├── Progress tracking (korean_words, quiz_correct/total)
│   │   ├── Affection system (Minsu relationship score)
│   │   └── Pending notifications queue (FastAPI → Bot bridge)
│   │
│   └── data/                     # 📦 STATIC RULE DATA
│       ├── food_rules.json       # Haram ingredient list + food safety rules
│       ├── housing_rules.json    # Deposit scam patterns + tenant rights
│       ├── general_rules.json    # Daily life rules (garbage, transport...)
│       └── korean_lessons.json   # Word bank + quiz question pool
│
├── 🌟 KILLER FEATURES ─────────────────────────────────────
│   ├── buddy_mode.py             # 🧑 MINSU — AI Best Friend
│   │   ├── Human-like texting (typos, slang, ㅋㅋ, ㅠㅠ)
│   │   ├── Dynamic affection system (-20 to 50+ score)
│   │   ├── Relationship levels (Cold → Acquaintance → Good Friend → Bestie)
│   │   ├── Emotional context detection (sad/happy → tone adaptation)
│   │   ├── 14 random proactive check-in messages
│   │   └── Homesick-specific empathetic responses
│   │
│   ├── culture_sim.py            # 🎮 CULTURE SHOCK SIMULATOR
│   │   ├── 8 pre-built scenarios (professor email, taxi scam, subway...)
│   │   ├── 3-choice consequence system with scoring (-30 to +30)
│   │   ├── Cultural lesson after each scenario
│   │   └── AI-generated dynamic scenarios by topic
│   │
│   ├── smart_interpreter.py      # 🔮 CULTURAL INTERPRETER
│   │   ├── Korean→English with cultural breakdown
│   │   ├── English→Korean with formality levels (반말/존댓말/격식체)
│   │   ├── "What NOT to say" warnings
│   │   └── Quick phrase categories (survive, eating, transport...)
│   │
│   ├── dormchef.py               # 🧑‍🍳 DORMCHEF — AI Cooking Assistant
│   │   ├── Microwave/kettle-only recipes
│   │   ├── CU/GS25/7-Eleven ingredient-aware
│   │   ├── Diet-safe (halal/vegan/allergy-aware)
│   │   ├── 10 quick recipe categories
│   │   └── Daiso equipment guide (₩8,000 starter kit)
│   │
│   └── korean_brain.py           # 🧠 KOREAN PRACTICE ENGINE
│       ├── 12 real-life scenarios (restaurant, pharmacy, professor...)
│       ├── AI roleplay with Korean level adaptation (1-5)
│       └── Inline feedback (✅ correct, 🔧 improve, 💡 next phrase)
│
├── 🛡️ SAFETY & DETECTION ──────────────────────────────────
│   ├── risk_detector.py          # 🔍 PRE-AI RULE ENGINE
│   │   ├── Crisis detection (suicide keywords → immediate 1393/1345)
│   │   ├── Deposit scam pattern matching
│   │   ├── Haram ingredient scanner (user diet-aware)
│   │   ├── Allergen cross-reference (8 categories, Korean labels)
│   │   ├── Message classification (9 categories)
│   │   └── Context builder for AI augmentation
│   │
│   ├── sos_mode.py               # 🆘 EMERGENCY SYSTEM
│   │   ├── 5 emergency phrase categories (60+ Korean phrases)
│   │   ├── 5 step-by-step response guides (lost, sick, scam, accident...)
│   │   ├── Pharmacy item reference (Korean names + prices)
│   │   └── Common scam red flags list
│   │
│   └── emotional_weather.py      # 💙 "3 AM PROBLEM" DETECTOR
│       ├── Passive behavioral signal tracking (no surveys)
│       ├── Late-night messaging detection (KST 11PM-5AM)
│       ├── Distress/personal/task word frequency analysis
│       ├── Adaptive Bayesian baseline (per-user, not global threshold)
│       ├── Graduated support (peer → university → professional)
│       └── Alarm fatigue prevention (max 1 check-in per 4 days)
│
├── 📊 TRACKING & GAMIFICATION ──────────────────────────────
│   ├── level_system.py           # 🏆 XP & LEVELING
│   │   ├── 6 levels: Newbie → Explorer → Survivor → Adapter → Local → 선배
│   │   ├── 12 XP reward categories (quiz, cook, simulate, streak...)
│   │   └── Visual progress bar + perk unlocks
│   │
│   ├── visa_radar.py             # 📡 VISA DEADLINE TRACKER
│   │   ├── 8 critical deadlines (SIM → ARC → NHIS → Visa Extension)
│   │   ├── Auto-calculates from arrival date
│   │   └── OVERDUE/NOW/SOON/UPCOMING status system
│   │
│   ├── smart_tracker.py          # 📊 CUSTOM TRACKER ENGINE
│   │   ├── User-created trackers (budget, sleep, gym...)
│   │   ├── Auto-emoji and unit guessing
│   │   └── Stats with averages and totals
│   │
│   ├── daily_challenge.py        # 🎯 DAILY SURVIVAL CHALLENGES
│   │   └── Rotating real-world micro-tasks with XP rewards
│   │
│   └── predictor.py              # 🔮 PREDICTIVE LIFE INSURANCE
│       ├── 13 research-backed timeline events
│       ├── Day-specific proactive warnings (Week 1 → Year 2)
│       ├── Condition-aware (halal-specific events)
│       └── Personalized micro-actions
│
├── 🌐 INFORMATION MODULES ─────────────────────────────────
│   ├── maps_helper.py            # 🗺️ TRI-ENGINE MAP SYSTEM
│   │   ├── Naver + Kakao + Google Maps link generation
│   │   ├── 70+ Korean term translations
│   │   ├── Place info database (with GPS coordinates)
│   │   └── Direction links with Korean search strings
│   │
│   ├── differentiator.py         # ⭐ UNIQUE FEATURES
│   │   ├── Live KRW exchange rates (20 currencies, cached 1hr)
│   │   ├── Korean name generator (phonetic + nature + modern styles)
│   │   ├── 10 cultural tip cards with Do/Don't format
│   │   ├── Scam scanner (11 red flag patterns)
│   │   ├── 29 daily tips rotation
│   │   └── Legacy onboarding flow
│   │
│   ├── korean_teacher.py         # 🇰🇷 LANGUAGE MODULE
│   │   ├── Word of the day (from JSON bank)
│   │   ├── Static quiz pool + AI quiz generation
│   │   ├── Alphabet/numbers lessons
│   │   └── Survival phrase categories
│   │
│   ├── news_fetcher.py           # 📰 NEWS ENGINE
│   │   └── RSS feed parser with student-relevance filter
│   │
│   ├── schedule_maker.py         # 📅 FIRST WEEK PLANNER
│   │   └── Diet-aware, city-specific daily checklist
│   │
│   └── apps_hacks.py             # 📱 APP RECOMMENDATIONS
│       └── Must-have Korean apps + AI life hacks
│
├── 🤝 SOCIAL & COMMUNITY ──────────────────────────────────
│   ├── bridge_builder.py         # 🌉 INTEGRATION TRACKER
│   │   ├── 10 integration milestones (greeting → Korean-only day)
│   │   ├── Career compass (Korean CV + interview guide)
│   │   ├── Workplace culture scenarios
│   │   └── Graduation portfolio generator
│   │
│   └── community_bot.py          # 👥 GROUP MANAGEMENT
│       ├── 10 Forum topic definitions
│       ├── Anonymous posting system
│       ├── Weekly challenge system
│       └── Leaderboard + community points
│
├── ⏰ PROACTIVE ENGINE ─────────────────────────────────────
│   └── notifier.py               # 📢 SCHEDULED NOTIFICATIONS
│       ├── APScheduler-based cron system (KST timezone)
│       ├── 08:30 morning briefing (word + tasks + prediction)
│       ├── 09:00 arrival milestone check
│       ├── 21:00 evening check-in (first 14 days only)
│       ├── 14:00 emotional weather silent analysis
│       ├── Every 6h silence detection
│       ├── Every 10s notification queue flush (FastAPI bridge)
│       ├── Every 3d DB keep-alive ping
│       └── Custom reminder scheduler
│
├── 🎙️ NEGOTIATOR (Voice AI MiniApp) ───────────────────────
│   ├── negotiator2/              # v2 — ACTIVE
│   │   ├── main.py               # FastAPI + WebSocket server
│   │   ├── ai_brain.py           # Dedicated AI routing for voice
│   │   └── index.html            # Glassmorphism UI (76KB)
│   │
│   └── negotiator/               # v1 — LEGACY
│       ├── main.py               # Original FastAPI app
│       └── index.html            # Original UI
│
├── 🧰 INFRASTRUCTURE ──────────────────────────────────────
│   ├── helpers.py                # Logging, rate limiting, validation
│   ├── Dockerfile                # Python 3.12-slim + ffmpeg
│   ├── requirements.txt          # 15 dependencies
│   ├── .env                      # API keys (gitignored)
│   ├── .gitignore
│   ├── test_bot.py               # 25-test suite (DB, AI, risk, intent...)
│   └── .github/workflows/
│       └── keepalive.yml         # GitHub Actions uptime ping
│
└── 📚 DOCUMENTATION ────────────────────────────────────────
    ├── README.md                 # ← YOU ARE HERE
    ├── ARCHITECTURE.md           # ← THIS FILE
    ├── model_audit.md            # AI model usage audit
    ├── gks_masterplan.md         # GKS scholarship strategy
    ├── codebase_study_guide.md   # Developer onboarding
    └── run_guide.md              # Quick start guide
```

---

## 🔄 Request Flow

```
User Message
    │
    ▼
┌─────────────────┐
│   bot.py        │  ← Telegram handler
│  (onboarding?)  │
└────────┬────────┘
         │
    ▼ (text)
┌─────────────────┐
│ state_manager   │  ← Is user in an active flow?
│ (BUDDY? COOK?)  │
└────────┬────────┘
    │ IDLE          │ ACTIVE
    ▼               ▼
┌──────────┐   ┌──────────────┐
│ intent   │   │ _handle_     │
│ _router  │   │ active_state │
│ (LLM)    │   └──────────────┘
└────┬─────┘
     │
     ▼
┌──────────────────┐
│ _execute_intent  │  ← Routes to feature module
│ (cook/map/buddy) │
└────────┬─────────┘
         │
    ▼ (general_question)
┌─────────────────┐
│ risk_detector   │  ← Pre-AI safety scan
│ (crisis/scam?)  │
└────────┬────────┘
         │
    ▼
┌─────────────────┐
│  ai_brain.py    │  ← Smart model routing
│  ask_ai()       │
│  buddy → Gemini │
│  complex → Groq │
└─────────────────┘
```

---

## 🗃️ Database Schema

```
┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐
│     users        │  │  chat_history     │  │    situations      │
├─────────────────┤  ├──────────────────┤  ├───────────────────┤
│ user_id (PK)    │  │ user_id          │  │ user_id           │
│ username        │  │ role             │  │ category          │
│ first_name      │  │ content          │  │ risk              │
│ diet            │  │ timestamp        │  │ summary           │
│ allergies       │  └──────────────────┘  │ rule_id           │
│ university      │                         └───────────────────┘
│ city            │  ┌──────────────────┐
│ arrival_date    │  │    user_xp        │  ┌───────────────────┐
│ streak          │  ├──────────────────┤  │  user_states       │
│ onboarding_step │  │ user_id (PK)     │  ├───────────────────┤
└─────────────────┘  │ total_xp         │  │ user_id (PK)      │
                     │ level            │  │ state             │
┌─────────────────┐  │ title            │  │ context (JSON)    │
│  buddy_history   │  └──────────────────┘  │ updated_at        │
├─────────────────┤                         └───────────────────┘
│ user_id         │  ┌──────────────────┐
│ role            │  │ emotional_signals │  ┌───────────────────┐
│ content         │  ├──────────────────┤  │ weather_scores     │
│ timestamp       │  │ user_id          │  ├───────────────────┤
└─────────────────┘  │ signal_type      │  │ user_id (PK)      │
                     │ value            │  │ score (0-100)     │
                     │ timestamp        │  │ consecutive_low   │
                     └──────────────────┘  └───────────────────┘
```

---

## 🤖 AI Model Routing

| Task | Primary Model | Provider | RPD | Why |
|------|--------------|----------|-----|-----|
| Buddy/Chat | Gemma 4 27B | Gemini | 1,500 | **Unlimited TPM** — handles volume |
| Complex (Visa/Legal) | Qwen3-32B | Groq | 1,000 | 60 RPM — best concurrency |
| Quiz Generation | LLaMA 3.1 8B | Groq | 14,400 | High RPD for frequent quizzes |
| Intent Classification | LLaMA 3.1 8B | Groq | 14,400 | Lightweight, fast classification |
| Image Analysis | Gemini 2.5 Flash | Gemini | 20 | Vision-capable |
| Voice Transcription | Whisper Turbo | Groq | 2,000 | Korean+English mixed |
| Safety Filter | LLaMA Prompt Guard | Groq | 14,400 | Tiny 86M model, instant |
| DormChef | LLaMA 3.1 8B | Groq | 14,400 | Simple recipe generation |
| Negotiator Voice | LLaMA 3.3 70B | Groq | 1,000 | Deep reasoning for negotiations |

---

## 📊 Deep Analysis Summary

### ✅ Production Strengths
- **24 integrated feature modules** — not a prototype
- **Multi-model AI cascade** — never returns empty to user
- **Crisis-first safety** — rule-based detection before AI (instant, reliable)
- **Adaptive emotional intelligence** — Bayesian per-user baselines
- **Diet/allergy-aware** — life-safety for halal/vegan students
- **Cloud-native DB** — Turso with SQLite fallback
- **Comprehensive test suite** — 25 automated tests

### ⚠️ Known Gaps
- `bot.py` is 2309 lines — needs splitting into handler modules
- Webhook migration pending (currently uses polling)
- No Redis/queue for horizontal scaling
- `lock_groq_key()` referenced in `ai_brain.py` but not defined in `config.py`
- `community_bot.py` + `bridge_builder.py` wired but not actively called from `bot.py`
- Negotiator v1 (`negotiator/`) is dead code — should be removed
