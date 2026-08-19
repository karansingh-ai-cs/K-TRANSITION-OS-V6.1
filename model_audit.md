# MODEL AUDIT — K-Transition OS v6.0
# Every model from user's Gemini + Groq list — status explained

## GEMINI MODELS STATUS

| Model | RPM | RPD | TPM | Status | Use Case |
|:------|:----|:----|:----|:-------|:---------|
| Gemini 2.5 Flash | 5 | 20 | 250K | ✅ USED | Image vision (GEMINI_VISION_MODEL) |
| Gemini 2.5 Flash Lite | 10 | 20 | 250K | ✅ USED | Final text fallback (GEMINI_MODEL) |
| Gemini 3.1 Flash Lite | 15 | 500 | 250K | ✅ USED | Tier B fallback (GEMINI_FLASH_LITE) |
| Gemma 4 26B | 15 | 1,500 | UNLIMITED | ✅ USED | Primary buddy (GEMINI_BUDDY_MODEL) |
| Gemma 4 31B | 15 | 1,500 | UNLIMITED | ✅ USED | Buddy backup (GEMINI_BUDDY_BACKUP) |
| **Gemini 2.5 Flash TTS** | 3 | 10 | 10K | ✅ ADDED | Voice output for Negotiator |
| **Gemini 3.1 Flash TTS** | 3 | 10 | 10K | ✅ ADDED | TTS backup |
| **Gemini 2.5 Flash Audio Dialog** | UNLIMITED | UNLIMITED | 1M | ✅ ADDED | Live voice chat in Negotiator — MASSIVE limit! |
| **Gemini 3 Flash Live** | UNLIMITED | UNLIMITED | 65K | ✅ ADDED | Live audio backup |
| **Gemini 3.5 Flash** | 5 | 20 | 250K | ✅ ADDED | Extra text fallback tier |
| **Gemini 3 Flash** | 5 | 20 | 250K | ✅ ADDED | Extra text fallback tier |
| **Gemini Embedding 2** | 100 | 1,000 | 30K | ✅ ADDED | Semantic search → saves AI calls! |
| **Gemini Embedding 1** | 100 | 1,000 | 30K | ✅ ADDED | Embedding backup |
| **Imagen 4 Fast Generate** | — | 25 | — | ✅ ADDED | Generate quiz images/illustrations |
| **Imagen 4 Generate** | — | 25 | — | ✅ ADDED | Higher quality image gen |
| Gemini 2.5 Pro | 0 | 0 | 0 | ❌ NOT AVAILABLE | Free tier quota = 0, cannot use |
| Gemini 2 Flash | 0 | 0 | 0 | ❌ DEPRECATED | Shuts down June 1, 2026 |
| Gemini 2 Flash Lite | 0 | 0 | 0 | ❌ DEPRECATED | Shuts down June 1, 2026 |
| Gemini 2.5 Pro TTS | 0 | 0 | 0 | ❌ NOT AVAILABLE | Free quota = 0 |
| Gemini 3.1 Pro | 0 | 0 | 0 | ❌ NOT AVAILABLE | Free quota = 0 |
| Nano Banana (2.5 Flash Preview Image) | 0 | 0 | 0 | ❌ NOT AVAILABLE | Preview, quota = 0 |
| Nano Banana Pro (3 Pro Image) | 0 | 0 | 0 | ❌ NOT AVAILABLE | Preview, quota = 0 |
| Nano Banana 2 (3.1 Flash Image) | 0 | 0 | 0 | ❌ NOT AVAILABLE | Preview, quota = 0 |
| Lyria 3 Clip | 0 | 0 | 0 | ❌ NOT USEFUL | Music generation — irrelevant for chatbot |
| Lyria 3 Pro | 0 | 0 | 0 | ❌ NOT USEFUL | Music generation — irrelevant |
| Veo 3 Generate | 0 | 0 | — | ❌ NOT USEFUL | Video generation — irrelevant |
| Veo 3 Fast Generate | 0 | 0 | — | ❌ NOT USEFUL | Video generation — irrelevant |
| Veo 3 Lite Generate | 0 | 0 | — | ❌ NOT USEFUL | Video generation — irrelevant |
| Gemini Robotics ER 1.5 | 10 | 20 | 250K | ❌ WRONG TYPE | Robotics control model, not for chat |
| Gemini Robotics ER 1.6 | 5 | 20 | 250K | ❌ WRONG TYPE | Robotics control model, not for chat |
| Computer Use Preview | 0 | 0 | 0 | ❌ NOT AVAILABLE | Preview, quota = 0 |
| Antigravity (Agent) | 0 | 0 | 0 | ❌ NOT AVAILABLE | Agent quota = 0 |
| Deep Research Pro Preview | 0 | 0 | 0 | ❌ NOT AVAILABLE | Preview, quota = 0 |
| Imagen 4 Ultra Generate | — | 25 | — | ⚠️ SKIP | Same limit as Fast, no extra benefit |

## GROQ MODELS STATUS

| Model | RPM | RPD | TPM | Status | Use Case |
|:------|:----|:----|:----|:-------|:---------|
| **openai/gpt-oss-120b** | 30 | 1,000 | 8K | ✅ ACTIVE | Primary complex workhorse & negotiator |
| **qwen/qwen3.6-27b** | 30 | 1,000 | 8K | ✅ ACTIVE | Secondary Scout & Qwen model |
| **openai/gpt-oss-20b** | 30 | 1,000 | 8K | ✅ ACTIVE | Quiz, summaries & light fallback |
| qwen/qwen3-32b | 0 | 0 | 0 | ❌ DEPRECATED | Shutdown July 17, 2026 -> Replaced by gpt-oss-120b |
| llama-3.1-8b-instant | 30 | 14,400 | 6K | ❌ DEPRECATED | Shutdown August 16, 2026 -> Replaced by gpt-oss-20b |
| llama-3.3-70b-versatile | 30 | 1,000 | 12K | ❌ DEPRECATED | Shutdown August 16, 2026 -> Replaced by gpt-oss-120b |
| allam-2-7b | 30 | 7,000 | 6K | ❌ DEPRECATED | Replaced by gpt-oss-20b |
| meta-llama/llama-4-scout-17b | 0 | 0 | 0 | ❌ DEPRECATED | Shutdown July 17, 2026 -> Replaced by qwen/qwen3.6-27b |
| **meta-llama/llama-prompt-guard-2-86m** | 30 | 14,400 | 15K | ✅ ADDED | Content safety filter (14.4K RPD!) |
| whisper-large-v3-turbo | 20 | 2,000 | — | ✅ USED | Voice transcription |
| canopylabs/orpheus-arabic-saudi | 10 | 100 | 1.2K | ❌ TOO LIMITED | 100 RPD = 100 messages/day total. Useless for group bot |
| canopylabs/orpheus-v1-english | 10 | 100 | 1.2K | ❌ TOO LIMITED | Same — 100 RPD is nothing |
| **groq/compound** | 30 | 250 | 70K | ✅ ACTIVE | High-throughput burst capacity (70K TPM!) |
| **groq/compound-mini** | 30 | 250 | 70K | ✅ ACTIVE | Lightweight compound fallback (70K TPM!) |
| openai/gpt-oss-safeguard-20b | 30 | 1,000 | 8K | ❌ REDUNDANT | Same as prompt-guard but lower RPD. llama-prompt-guard better |
| whisper-large-v3 | 20 | 2,000 | — | ❌ REPLACED | Turbo is faster with same limits |
| meta-llama/llama-prompt-guard-2-22m | 30 | 14,400 | 15K | ⚠️ REDUNDANT | 22m = smaller version of 86m. Use 86m instead |

## KEY NEW ADDITIONS EXPLAINED

### 1. Gemini 2.5 Flash Audio Dialog (UNLIMITED RPM + RPD!)
- This is the LIVE API — designed for real-time voice conversations
- Your Negotiator already does voice — THIS can power it with zero rate limit fears
- Can be used in negotiator2/ for real-time bargaining voice sessions

### 2. Gemini Embedding 2 (100 RPM, 1K RPD)
- Converts text into numbers (vectors) to find "similar meaning" questions
- Use case: "How do I get ARC?" and "What is 외국인등록증?" mean the same
- SAVES API CALLS by matching FAQ questions locally before calling AI

### 3. TTS Models (Gemini 2.5 Flash TTS + 3.1 Flash TTS)
- Text-to-Speech — bot can SPEAK responses
- Perfect for the Negotiator: instead of text, bot replies with voice

### 4. Imagen 4 Fast (25 RPD)
- Generates images from text descriptions
- Use case: generate quiz flashcard images, cultural images for lessons

### 5. LLaMA Prompt Guard (14,400 RPD!)
- Safety filter — checks if a message is a "jailbreak attempt" or harmful
- Run EVERY message through this before sending to AI (it's tiny, super fast)
- 14.4K RPD means it can check ALL messages for 100 users with no issue
