<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python" />
  <img src="https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?logo=telegram" />
  <img src="https://img.shields.io/badge/AI-Groq%20%2B%20Gemini-FF6F00?logo=google" />
  <img src="https://img.shields.io/badge/DB-Turso%20Cloud-00C389" />
  <img src="https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
</p>

# 🇰🇷 K-Transition OS v6.0

**The AI-Powered Survival Operating System for International Students in South Korea**

> _"We don't wait for the student to break. We notice before they do."_

K-Transition OS is a production-grade Telegram bot + voice negotiation MiniApp that acts as a **24/7 AI senior (선배)** for GKS scholarship students and international students arriving in Korea. It combines multi-model AI routing, real-time safety detection, cultural intelligence, and proactive mental health monitoring into a single conversational platform.

---

## 🎯 What Makes This Different

| Generic Chatbot | K-Transition OS |
|---|---|
| "Ask me anything" | Detects deposit scams **before** you lose ₩5M |
| Google Translate | Cultural interpreter that warns "don't say this to your professor" |
| Mental health survey | **Silent** behavioral pattern detection — no surveys, just care |
| Recipe app | DormChef that knows your dorm has only a microwave + CU ingredients |
| Map search | Tri-engine maps (Naver + Kakao + Google) with **Korean search strings** |
| Language app | AI roleplay in 12 real Korean scenarios adapted to your level |
| Generic chatbot | **Minsu (민수)** — an AI friend who texts like a real Korean student |

---

## ✨ Feature Overview

### 🌟 Killer Features
| Feature | Module | Description |
|---------|--------|-------------|
| 🧑 **Buddy (Minsu)** | `buddy_mode.py` | AI best friend with affection system, human texting style, emotional adaptation |
| 🎮 **Culture Simulator** | `culture_sim.py` | Choose-your-adventure Korean scenarios with real consequences |
| 🔮 **Cultural Interpreter** | `smart_interpreter.py` | Not translation — full cultural breakdown with formality levels |
| 🧑‍🍳 **DormChef** | `dormchef.py` | Microwave-only recipes from convenience store ingredients, diet-safe |
| 🧠 **Korean Brain** | `korean_brain.py` | AI roleplay practice in 12 real-life scenarios |
| 🎙️ **Negotiator** | `negotiator2/` | Voice-powered AI negotiation assistant (WebSocket + TTS) |

### 🛡️ Safety & Detection
| Feature | Module | Description |
|---------|--------|-------------|
| 🆘 **SOS Mode** | `sos_mode.py` | One-tap emergency system with Korean phrases + step-by-step guides |
| 🔍 **Risk Detector** | `risk_detector.py` | Pre-AI rule engine: crisis, scams, haram, allergens — instant, reliable |
| 💙 **Emotional Weather** | `emotional_weather.py` | Passive mental health monitoring with adaptive Bayesian baselines |
| 🔴 **Scam Scanner** | `differentiator.py` | 11 red-flag patterns with instant verdict |

### 📊 Tracking & Gamification
| Feature | Module | Description |
|---------|--------|-------------|
| 🏆 **Level System** | `level_system.py` | 6 levels (Newbie → 선배) with XP rewards for every interaction |
| 📡 **Visa Radar** | `visa_radar.py` | Auto-calculated deadlines from arrival date (ARC, NHIS, extension) |
| 🔮 **Predictor** | `predictor.py` | Research-backed proactive warnings (Month 3 loneliness, financial traps) |
| 📊 **Smart Tracker** | `smart_tracker.py` | Custom budget/habit trackers with auto-emoji |
| 🎯 **Daily Challenge** | `daily_challenge.py` | Real-world micro-tasks with XP |

#### 🧠 Zero-Command Natural Intelligence Budget & Task Logger
No slash commands or formatted inputs required. The AI context router and state manager seamlessly extract and log your expenses, habit entries, and survival checklist tasks:
- **Natural Spending Logging:** Simply say *"I spent 5000 won on coffee"* or *"paid 12000 for dinner"*. The system automatically extracts the amount, categorizes the purchase, and logs it to your active `spending` tracker while instantly displaying your daily and weekly totals.
- **Conversational Task Manager:** Simply type *"I need to pick up my ARC"* or *"remind me to register for classes"*. The system automatically adds it to your checklist and sets a reminder. Mark tasks as finished via *"done with ARC"* or *"finished class registration"*.
- **Natural Queries:** Ask *"how much did I spend today?"* or *"what is my budget?"* to get structured weekly/monthly financial reports.
- **Morning Briefings Integration:** Wake up to daily budget updates! Your morning briefing automatically appends your total expenditure from yesterday and the current month.

### 🌐 Information
| Feature | Module | Description |
|---------|--------|-------------|
| 🗺️ **Maps** | `maps_helper.py` | Naver + Kakao + Google with 70+ Korean translations |
| 💱 **Exchange Rates** | `differentiator.py` | Live KRW rates for 20 currencies (free API, no key) |
| 📰 **News** | `news_fetcher.py` | Korea news with student-relevance filter |
| 📅 **Schedule** | `schedule_maker.py` | Diet-aware, city-specific first-week planner |
| 📱 **Apps & Hacks** | `apps_hacks.py` | Must-have Korean apps + AI life hacks |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────┐
│                   TELEGRAM USER                     │
└──────────────────────┬─────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │        bot.py           │
          │   (Command Handlers)    │
          │   (State Machine)       │
          │   (Intent Router)       │
          └────────────┬────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌──────────┐  ┌───────────┐  ┌──────────┐
  │ Feature  │  │ ai_brain  │  │  risk    │
  │ Modules  │  │ (Multi-   │  │ detector │
  │ (cook,   │  │  Model    │  │ (safety  │
  │  map,    │  │  Cascade) │  │  first)  │
  │  buddy)  │  └─────┬─────┘  └──────────┘
  └──────────┘        │
              ┌───────┼───────┐
              ▼       ▼       ▼
         ┌────────┐ ┌─────┐ ┌────────┐
         │ Gemini │ │Groq │ │Whisper │
         │Gemma4  │ │Qwen3│ │ Turbo  │
         │Flash   │ │LLaMA│ │        │
         └────────┘ └─────┘ └────────┘
                       │
              ┌────────▼────────┐
              │    db.py        │
              │ Turso ↔ SQLite  │
              └─────────────────┘
```

> See [ARCHITECTURE.md](ARCHITECTURE.md) for the full module tree, DB schema, and AI routing table.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Groq API Key (free at [console.groq.com](https://console.groq.com))
- Gemini API Key (free at [aistudio.google.com](https://aistudio.google.com))

### Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/k-transition-os.git
cd k-transition-os/ktransition

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   TELEGRAM_TOKEN=your_bot_token
#   GROQ_API_KEY=your_groq_key
#   GEMINI_API_KEY=your_gemini_key

# (Optional) Cloud DB — add Turso credentials:
#   TURSO_URL=libsql://your-db.turso.io
#   TURSO_TOKEN=your_token

# Run tests
python test_bot.py

# Start the bot
python bot.py
```

### Deploy to Render

```bash
# The Dockerfile is pre-configured for Render
# 1. Push to GitHub
# 2. Connect repo to Render (Web Service)
# 3. Set environment variables in Render dashboard
# 4. Deploy — bot starts automatically on port 10000
```

---

## 🤖 AI Model Strategy

K-Transition uses a **Single-Key, Multi-Model Cascading** architecture — TOS-compliant, no key abuse:

| Task Type | Model | Why This Model |
|-----------|-------|---------------|
| Casual Chat (Minsu) | Gemma 4 27B (Gemini) | **Unlimited TPM** — handles all chat volume |
| Complex Questions | GPT-OSS-120B (Groq) | Primary workhorse for complex reasoning |
| Quizzes & Summaries | GPT-OSS-20B (Groq) | Fast, light model for quizzes and summaries |
| Scout / Fallback | Qwen 3.6 27B (Groq) | Active Qwen model for fallback routing |
| Image Analysis | Gemini 2.5 Flash | Vision-capable for food labels & signs |
| Voice Notes | Whisper Turbo (Groq) | Korean+English mixed transcription |
| Safety Filter | LLaMA Prompt Guard 86M | Tiny model, instant jailbreak detection |

Every route has **automatic fallback cascading** — if the primary model returns 429, it silently falls to the next tier. The user never sees an error.

---

## 📁 Project Structure

```
ktransition/
├── bot.py              # Main entry point (Telegram + FastAPI)
├── ai_brain.py         # Multi-model AI routing engine
├── config.py           # Configuration & model definitions
├── db.py               # Universal DB connector (Turso/SQLite)
├── memory.py           # All persistence (users, history, progress)
├── intent_router.py    # LLM-powered intent classification
├── state_manager.py    # Conversation state machine (DB-persisted)
├── risk_detector.py    # Pre-AI safety scanning
├── helpers.py          # Utilities (logging, rate limiting, validation)
│
├── buddy_mode.py       # Minsu AI friend
├── culture_sim.py      # Culture shock simulator
├── smart_interpreter.py # Cultural interpreter
├── dormchef.py         # Dorm cooking assistant
├── korean_brain.py     # Korean practice engine
├── korean_teacher.py   # Word/quiz/phrase module
├── maps_helper.py      # Tri-engine map system
├── differentiator.py   # Exchange rates, names, scam scanner
├── visa_radar.py       # Visa deadline tracker
├── predictor.py        # Proactive timeline warnings
├── emotional_weather.py # Mental health pattern detection
├── sos_mode.py         # Emergency response system
├── notifier.py         # Scheduled notifications (APScheduler)
├── bridge_builder.py   # Integration milestones + career
├── community_bot.py    # Group management system
├── level_system.py     # XP & gamification
├── smart_tracker.py    # Custom habit/budget trackers
├── daily_challenge.py  # Daily survival challenges
├── schedule_maker.py   # First-week planner
├── news_fetcher.py     # Korea news aggregator
├── apps_hacks.py       # App recommendations
│
├── negotiator2/        # Voice AI MiniApp (FastAPI + WebSocket)
├── data/               # Static rule data (food, housing, Korean)
├── test_bot.py         # 25-test automated suite
├── Dockerfile          # Production container
├── requirements.txt    # Dependencies
└── ARCHITECTURE.md     # Full architecture documentation
```

---

## 🧪 Testing

```bash
python test_bot.py
```

Runs 25 tests covering:
- ✅ Database connection (Turso/SQLite)
- ✅ Config & data file loading
- ✅ User CRUD & chat history
- ✅ State machine persistence
- ✅ AI connectivity (Groq + Gemini)
- ✅ Quiz generation & parsing
- ✅ Buddy mode human-likeness (rejects AI-sounding phrases)
- ✅ Risk detection (crisis, scam, halal, allergen)
- ✅ Korean teacher, maps, visa, SOS
- ✅ Intent routing accuracy

---

## 🗺️ Roadmap

- [ ] **Webhook migration** — Replace polling with webhooks to save Render CPU
- [ ] **Split bot.py** — Extract handlers into `handlers/` package
- [ ] **Frontend CDN** — Host Negotiator UI on Vercel/GitHub Pages
- [ ] **Emergency fallback** — Hugging Face Space as circuit breaker
- [ ] **Multi-language** — Arabic, Vietnamese, Mongolian support
- [ ] **Alumni network** — Connect current + graduated students

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`python test_bot.py`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- **GKS (Global Korea Scholarship)** — The mission that inspired this project
- **Groq** — Free-tier AI inference that makes this possible
- **Google Gemini** — Unlimited TPM models for chat workloads
- **Turso** — Edge database for global student access
- **python-telegram-bot** — Robust Telegram framework

---

<p align="center">
  <b>Built with ❤️ for every international student who ever felt lost in Korea</b><br>
  <i>한국에서 길을 잃은 모든 유학생을 위해</i>
</p>
