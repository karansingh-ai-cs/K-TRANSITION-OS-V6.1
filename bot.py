#!/usr/bin/env python3
# bot.py — K-Transition OS v5.0
# Main Telegram bot entry point.
#
# Message flow:
#  1. Onboarding check (new users go through wizard first)
#  2. Rate limit check
#  3. Rule-based risk scan (instant)
#  4. AI response (Groq → Gemini fallback)
#  5. Send + save
#
# Special inputs: voice notes (transcribed), photos (Gemini Vision), inline button callbacks.
import os 
import logging
import asyncio
import json
import http.server
import socketserver
import threading
from datetime import datetime, UTC
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode, ChatAction

from config import (
    TELEGRAM_TOKEN, BOT_NAME, BOT_VERSION,
    FEATURE_KOREAN_LESSONS, FEATURE_NEWS, FEATURE_MAPS,
    FEATURE_SCHEDULE, FEATURE_IMAGE_AI, FEATURE_VOICE_NOTES,
    GEMINI_API_KEY
)
from ai_brain import (
    ask_ai_async, analyze_image_async, transcribe_audio_async,
    generate_quiz_question_async
)
from risk_detector import scan_message, build_context_for_ai
from memory import (
    setup, get_or_create_user, save_message, get_history,
    save_buddy_message, get_buddy_history,
    log_situation, get_situations, set_diet, add_allergy, remove_allergy,
    set_university, set_city, set_arrival_date, get_progress,
    add_korean_word_learned, record_quiz_answer, mark_task_done,
    update_streak, set_onboarding_step, update_user,
    add_task, get_tasks, complete_task, delete_task
)
from korean_teacher import (
    get_word_of_the_day, format_word_of_day,
    get_survival_phrases, format_phrases_list,
    get_static_quiz_question, build_quiz_options,
    format_ai_quiz_message, format_quiz_result,
    get_alphabet_lesson, get_numbers_lesson, get_pronunciation_tips,
    get_topic_list, _next_category
)
from schedule_maker import (
    get_first_week_checklist, get_task_detail, get_month_overview,
    generate_ai_schedule, get_week_tasks, FIRST_WEEK_TASKS
)
from news_fetcher import get_news, format_news, get_news_for_students, filter_news_by_topic
from maps_helper import format_map_response, format_place_info, get_area_guide, IMPORTANT_PLACES, translate_to_korean, format_map_guide, format_transport_links
from differentiator import (
    format_exchange_rates, format_korean_name, format_cultural_tip,
    format_scam_scan, format_daily_tip, get_all_cultural_topics,
    get_cultural_tip
)
from helpers import (
    setup_logging, clean_text, short_summary,
    is_rate_limited, validate_diet, validate_allergy
)

# ── V4: Predictive + Emotional + Community ────────────────────────────────────
from predictor import (
    get_todays_predictions, format_prediction,
    days_since_arrival, get_days_in_korea_summary
)
from emotional_weather import (
    setup_weather_tables, analyze_message, log_message_time,
    get_weather_score, get_peer_support_message, should_checkin,
    record_checkin_sent, get_checkin_message
)
from bridge_builder import (
    setup_bridge_tables, get_integration_score, format_integration_status,
    format_milestone_list, complete_milestone, generate_portfolio,
    log_portfolio_event, CAREER_CONTENT, INTEGRATION_MILESTONES
)
from community_bot import (
    setup_community_tables, get_or_create_community_profile,
    add_community_points, complete_challenge as complete_weekly_challenge,
    get_leaderboard, get_this_weeks_challenge, format_weekly_challenge,
    get_welcome_message, get_group_rules, get_topic_intro,
    TOPICS, SEED_QA, format_seed_post, next_anon_number,
    log_anon_post, route_message_to_topic, WEEKLY_CHALLENGES
)
from notifier import start_scheduler

# ── V5: New Killer Features ────────────────────────────────────────────────────
from dormchef import get_chef_recipe, get_quick_recipe, get_equipment_guide, get_recipe_categories
from daily_challenge import get_todays_challenge, format_challenge, get_challenge_stats_text
from korean_brain import start_practice, continue_practice, get_scenario_list, SCENARIOS as KB_SCENARIOS
from smart_tracker import (
    setup_tracker_tables, create_tracker, log_entry, get_user_trackers,
    get_tracker_by_name, get_tracker_stats, get_tracker_entries,
    guess_emoji, guess_unit, format_tracker_list, format_tracker_stats
)
from buddy_mode import chat_with_buddy, get_random_checkin
from sos_mode import format_sos_general, format_sos_guide, format_sos_phrases
from visa_radar import get_visa_status, format_visa_status, format_visa_checklist
from culture_sim import (
    get_random_scenario, format_scenario, evaluate_choice,
    generate_ai_scenario, get_scenario_topics, evaluate_ai_choice
)
from smart_interpreter import interpret_text, get_phrase_list, get_formality_guide
from apps_hacks import get_apps_list, get_hacks, get_ai_hack
from level_system import setup_level_tables, add_xp, format_level_status, format_levelup, XP_REWARDS
from state_manager import State, get_state, get_context, set_state, update_context, clear_state, should_override
from intent_router import route_intent
import random

setup_logging()
logger = logging.getLogger(__name__)

# ── Active quiz state (in-memory) ─────────────────────────────────────────────
# Maps user_id → {question dict, options list, correct_index}
_active_quizzes: dict[int, dict] = {}

# ── Onboarding state (in-memory) ──────────────────────────────────────────────
# Maps user_id → step index (0-4)
_onboarding: dict[int, dict] = {}

# ── V5/V6: Interactive state now managed by state_manager.py ──────────────────
# _active_sims, _active_practice, _buddy_history moved to state_manager

ONBOARDING_STEPS = [
    {"field": "arrival_date",  "q": "1️⃣ When did you arrive in Korea (or when are you arriving)?\n\nExamples: 'Already here', 'September 2025', '2025-09-01', 'Next month'"},
    {"field": "university",    "q": "2️⃣ Which university are you attending?\n\n(e.g. KAIST, SNU, Yonsei, POSTECH, Hanyang, Konkuk...)"},
    {"field": "city",          "q": "3️⃣ Which city is your university in?\n\n(e.g. Seoul, Daejeon, Busan, Daegu, Incheon...)"},
    {"field": "diet",          "q": "4️⃣ Any diet restrictions?", "keyboard": [["halal","vegetarian"],["vegan","kosher"],["none (no restrictions)"]]},
    {"field": "allergies",     "q": "5️⃣ Any food allergies?\n\nType them (e.g. 'nuts, dairy') or tap Skip.", "keyboard": [["nuts","dairy"],["gluten","eggs"],["fish","shellfish"],["none"]]},
]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def safe_send(update: Update, text: str, parse_mode=None, reply_markup=None):
    """Send message, splitting into ≤4000-char chunks if needed."""
    MAX = 4000
    chunks = [text[i:i+MAX] for i in range(0, max(len(text),1), MAX)]
    for i, chunk in enumerate(chunks):
        markup = reply_markup if i == len(chunks)-1 else None
        try:
            await update.message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup)
        except Exception as e:
            logger.warning("Send with parse_mode failed (%s), retrying plain.", e)
            try:
                await update.message.reply_text(chunk, reply_markup=markup)
            except Exception as e2:
                logger.error("Even plain send failed: %s", e2)
        if i < len(chunks)-1:
            await asyncio.sleep(0.3)


def nav_keyboard() -> InlineKeyboardMarkup:
    """Inline navigation bar — kept for specific messages."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏠 Home",     callback_data="nav_home"),
            InlineKeyboardButton("📅 Schedule", callback_data="nav_schedule"),
            InlineKeyboardButton("🗺️ Maps",     callback_data="nav_maps"),
        ],
        [
            InlineKeyboardButton("🇰🇷 Korean",  callback_data="nav_korean"),
            InlineKeyboardButton("🛡️ Safety",   callback_data="nav_safety"),
            InlineKeyboardButton("📰 News",     callback_data="nav_news"),
        ],
    ])


def room_keyboard() -> InlineKeyboardMarkup:
    """Escape hatch button shown inside active Rooms (Buddy, Chef, Practice, etc.)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Back to Main Bot", callback_data="soft_exit_room")]
    ])


def simulate_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for simulator options."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("A", callback_data="sim_choice_a"),
            InlineKeyboardButton("B", callback_data="sim_choice_b"),
            InlineKeyboardButton("C", callback_data="sim_choice_c")
        ],
        [InlineKeyboardButton("🏠 Back to Main Bot", callback_data="soft_exit_room")]
    ])


def main_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard — always visible at bottom. Full feature coverage."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/speak")],
            [KeyboardButton("🍳 Cook"), KeyboardButton("🗺️ Maps"), KeyboardButton("💬 Buddy"), KeyboardButton("📰 News")],
            [KeyboardButton("🎮 Simulate"), KeyboardButton("🔮 Interpret"), KeyboardButton("🇰🇷 Korean"), KeyboardButton("📊 Status")],
            [KeyboardButton("🛡️ SOS"), KeyboardButton("📅 Schedule"), KeyboardButton("🏆 Level"), KeyboardButton("⚙️ More")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def _build_status_card(user_id: int, user_info: dict) -> str:
    """Full status card — shown on 📊 Status tap."""
    progress = get_progress(user_id)
    uni = user_info.get("university", "not set")
    city = user_info.get("city", "not set")
    diet = user_info.get("diet", "not set")
    allergies = ", ".join(user_info.get("allergies", [])) or "none"
    streak = user_info.get("streak", 0)
    words = progress.get("korean_words", 0)
    correct = progress.get("quiz_correct", 0)
    total = progress.get("quiz_total", 0)
    pct = f"{int(correct/total*100)}%" if total else "N/A"

    # Visa info
    visa_line = ""
    arrival = user_info.get("arrival_date", "")
    if arrival:
        try:
            data = get_visa_status(arrival)
            if data and data.get("days_since"):
                visa_line = f"\n🛡️ Days in Korea: {data['days_since']} | ARC: {'✅' if data.get('arc_done') else '⏰ needed'}"
        except Exception:
            pass

    # Level info
    try:
        level_data = format_level_status(user_id)
        level_line = level_data.split("\n")[1] if "\n" in level_data else ""
    except Exception:
        level_line = ""

    return (
        f"━━━━ 📊 Your Status ━━━━\n\n"
        f"👤 {user_info.get('first_name', 'Student')}\n"
        f"🎓 {uni} · 📍 {city}\n"
        f"🍽️ Diet: {diet} · ⚠️ Allergies: {allergies}\n"
        f"🔥 Streak: {streak} days{visa_line}\n\n"
        f"🇰🇷 Korean: {words} words · Quiz {pct} ({correct}/{total})\n"
        f"{level_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"/setup — Edit profile · /visa — Visa details"
    )


# ── Button Text → Action Map ─────────────────────────────────────────────────
BUTTON_ACTIONS = {
    "🍳 Cook": "cook_start", "🗺️ Maps": "map_start", "💬 Buddy": "buddy_start",
    "📰 News": "news_fetch", "🎮 Simulate": "sim_start", "🔮 Interpret": "interpret_start",
    "🇰🇷 Korean": "korean_menu", "📊 Status": "status_show", "🛡️ SOS": "sos_show",
    "📅 Schedule": "schedule_show", "🏆 Level": "level_show", "⚙️ More": "help_show",
}


async def _handle_button_text(update, context, user_id, user_info, text):
    """Handle persistent keyboard button taps. Returns True if handled."""
    action = BUTTON_ACTIONS.get(text.strip())
    if not action:
        return False

    # Clear any previous state when tapping a new button
    clear_state(user_id)
    kb = main_keyboard()

    if action == "cook_start":
        set_state(user_id, State.COOK_WAITING_INGREDIENTS)
        await safe_send(update, "🧑‍🍳 What's in your fridge? Tell me your ingredients!\n\nOr describe a craving — I'll make it work with convenience store stuff 🔥", reply_markup=room_keyboard())
    elif action == "map_start":
        set_state(user_id, State.MAP_WAITING_QUERY)
        await safe_send(update, "🗺️ Where do you want to go?\n\n• Place name: \"pharmacy\", \"halal restaurant\"\n• Directions: \"from Hongdae to Gangnam\"\n• Nearby: \"nearest ATM\"\n\nAll links work with Naver + Kakao + Google Maps!", reply_markup=room_keyboard())
    elif action == "buddy_start":
        db_history = get_buddy_history(user_id, limit=20)
        set_state(user_id, State.BUDDY_ACTIVE, {"history": db_history})
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(random.uniform(0.5, 1.2))
        response = await chat_with_buddy("hey! what's up?", user_info, db_history)
        save_buddy_message(user_id, "user", "hey! what's up?")
        save_buddy_message(user_id, "assistant", response)
        db_history.append({"role": "user", "content": "hey! what's up?"})
        db_history.append({"role": "assistant", "content": response})
        update_context(user_id, history=db_history[-16:])
        await safe_send(update, f"🧑 민수:\n{response}", reply_markup=room_keyboard())
    elif action == "news_fetch":
        await update.message.reply_text("📰 Fetching latest Korea news...")
        news = get_news(max_items=5)
        await safe_send(update, format_news(news), reply_markup=kb)
    elif action == "sim_start":
        scenario = get_random_scenario()
        set_state(user_id, State.SIM_WAITING_CHOICE, {"scenario": scenario})
        await safe_send(update, format_scenario(scenario), reply_markup=simulate_keyboard())
    elif action == "interpret_start":
        set_state(user_id, State.INTERPRET_WAITING_TEXT)
        await safe_send(update, "🔮 Send me any text!\n\n• Korean → translate + cultural breakdown\n• English → Korean version with formality levels\n• Situation: \"how do I tell my professor I'll be late\"", reply_markup=room_keyboard())
    elif action == "korean_menu":
        msg = ("🇰🇷 Korean Learning\n━━━━━━━━━━━━━━━━━━\n\n"
               "📚 /word — Word of the day\n🎯 /quiz — AI quiz (adapts to level)\n"
               "🧠 /practice — Roleplay scenarios\n💬 /phrase — Survival phrases\n"
               "🔤 /alphabet — Learn Hangeul\n🔢 /numbers — Korean numbers\n"
               "📊 /progress — Your learning stats\n\nOr just ask me anything in Korean!")
        await safe_send(update, msg, reply_markup=kb)
    elif action == "status_show":
        await safe_send(update, _build_status_card(user_id, user_info), reply_markup=kb)
    elif action == "sos_show":
        await safe_send(update, format_sos_general(), reply_markup=kb)
    elif action == "schedule_show":
        await safe_send(update, get_first_week_checklist(user_info), reply_markup=kb)
    elif action == "level_show":
        await safe_send(update, format_level_status(user_id), reply_markup=kb)
    elif action == "help_show":
        msg = ("⚙️ All Features\n━━━━━━━━━━━━━━\n\n"
               "🔥 KILLER\n/simulate — Culture Shock Simulator\n/interpret [text] — Cultural Interpreter\n"
               "/buddy [msg] — Chat with Minsu\n/cook [ingredients] — DormChef\n\n"
               "📅 DAILY\n/challenge — Today's challenge\n/visa — Visa tracker\n/news — Korea news\n\n"
               "🇰🇷 KOREAN\n/practice — AI roleplay\n/quiz — Korean quiz\n/word — Word of the day\n\n"
               "📊 TRACKING\n/track — Custom trackers\n/task — Task manager\n\n"
               "📱 INFO\n/apps — Must-have apps\n/hack — Life hacks\n/map — Find places\n"
               "/rate — Exchange rates\n/culture — Culture tips\n\n"
               "⚙️ SETUP\n/setup — Profile wizard\n/profile — View profile\n\n"
               "💡 Or just type naturally — I understand everything!")
        await safe_send(update, msg, reply_markup=kb)
    return True


# ── Active State Handler ──────────────────────────────────────────────────────

async def _handle_active_state(update, context, user_id, user_info, text, state):
    """Handle user input within an active conversation state."""
    kb = main_keyboard()

    if state == State.COOK_WAITING_INGREDIENTS:
        diet = user_info.get("diet", "none")
        allergies = ", ".join(user_info.get("allergies", [])) or "none"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        result = await get_chef_recipe(text, diet, allergies)
        add_xp(user_id, XP_REWARDS["cook_recipe"], "cook_recipe")
        clear_state(user_id)
        await safe_send(update, result, reply_markup=kb)

    elif state == State.MAP_WAITING_QUERY:
        city = user_info.get("city", "")
        info, venue = format_place_info(text.lower().strip(), city)
        if info:
            clear_state(user_id)
            if venue:
                await update.message.reply_venue(
                    latitude=venue["lat"], longitude=venue["lng"],
                    title=venue["title"], address=venue["address"], reply_markup=kb
                )
            await safe_send(update, info, reply_markup=kb)
            return
        korean_q = translate_to_korean(text)
        korean_override = korean_q if korean_q.lower() != text.lower() else None
        clear_state(user_id)
        await safe_send(update, format_map_response(text, city, korean_override), reply_markup=kb)

    elif state == State.SIM_WAITING_CHOICE:
        ctx = get_context(user_id)
        scenario = ctx.get("scenario")
        if scenario and text.strip().lower() in ("a", "b", "c"):
            if isinstance(scenario, dict) and scenario.get("is_ai"):
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                eval_res = await evaluate_ai_choice(scenario.get("text"), text.strip(), user_info)
                clear_state(user_id)
                if eval_res:
                    msg, score = eval_res
                    if score > 20:
                        add_xp(user_id, XP_REWARDS["simulate_perfect"], "simulate_perfect")
                    elif score > 0:
                        add_xp(user_id, XP_REWARDS["simulate_ok"], "simulate_ok")
                    await safe_send(update, msg, reply_markup=room_keyboard())
                else:
                    await safe_send(update, "Couldn't evaluate. Try /simulate again!", reply_markup=room_keyboard())
            else:
                result = evaluate_choice(scenario, text.strip())
                clear_state(user_id)
                if result:
                    msg, score = result
                    if score > 20:
                        add_xp(user_id, XP_REWARDS["simulate_perfect"], "simulate_perfect")
                    elif score > 0:
                        add_xp(user_id, XP_REWARDS["simulate_ok"], "simulate_ok")
                    await safe_send(update, msg, reply_markup=room_keyboard())
                else:
                    await safe_send(update, "Couldn't evaluate. Try /simulate again!", reply_markup=room_keyboard())
        else:
            await safe_send(update, "Pick A, B, or C! 👆", reply_markup=simulate_keyboard())

    elif state == State.PRACTICE_ACTIVE:
        ctx = get_context(user_id)
        if text.strip().lower() in ("/stop", "stop", "quit", "exit"):
            clear_state(user_id)
            await update.message.reply_text("Practice ended! Great effort 👏", reply_markup=kb)
            return
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        response = await continue_practice(text, ctx.get("scenario", ""), ctx.get("history", []), ctx.get("level", 1))
        ctx.setdefault("history", []).append({"role": "user", "content": text})
        ctx["history"].append({"role": "assistant", "content": response})
        if len(ctx["history"]) > 16:
            ctx["history"] = ctx["history"][-12:]
        await safe_send(update, response, reply_markup=room_keyboard())

    elif state == State.BUDDY_ACTIVE:
        ctx = get_context(user_id)
        history = ctx.get("history", [])
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(random.uniform(0.5, 1.8))
        response = await chat_with_buddy(text, user_info, history)
        save_buddy_message(user_id, "user", text)
        save_buddy_message(user_id, "assistant", response)
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": response})
        if len(history) > 20:
            ctx["history"] = history[-16:]
        await safe_send(update, f"🧑 민수:\n{response}", reply_markup=room_keyboard())

    elif state == State.INTERPRET_WAITING_TEXT:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        result = await interpret_text(text, user_info)
        clear_state(user_id)
        await safe_send(update, f"🔮 Cultural Interpreter\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{result}", reply_markup=kb)

    elif state == State.NEWS_WAITING_TOPIC:
        news = filter_news_by_topic(text.strip())
        clear_state(user_id)
        await safe_send(update, format_news(news), reply_markup=kb)

    else:
        clear_state(user_id)
        await process_message(update, context, text)


# ── Intent Executor (Soft-Routing Architecture) ──────────────────────────────

# Maps intent → (emoji, label, callback_data) for suggestion buttons
_SOFT_BUTTONS = {
    "cook":       ("🧑‍🍳", "Open AI DormChef",      "soft_cook"),
    "map":        ("🗺️",  "Get Map Directions",    "soft_map"),
    "buddy":      ("💬",  "Chat with Minsu",       "soft_buddy"),
    "interpret":  ("🔮",  "Open Cultural Interpreter", "soft_interpret"),
    "simulate":   ("🎮",  "Try Culture Simulator",  "soft_simulate"),
    "practice":   ("🧠",  "Start Korean Practice",  "soft_practice"),
    "news":       ("📰",  "Open News Feed",         "soft_news"),
    "visa":       ("📡",  "Open Visa Radar",        "soft_visa"),
    "challenge":  ("🎯",  "Open Daily Challenge",   "soft_challenge"),
    "quiz":       ("📝",  "Start Korean Quiz",      "soft_quiz"),
    "word":       ("📚",  "Get Word of the Day",    "soft_word"),
    "phrase":     ("💬",  "Survival Phrases",       "soft_phrase"),
    "apps":       ("📱",  "Show Recommended Apps",  "soft_apps"),
    "hack":       ("💡",  "Korea Life Hacks",       "soft_hack"),
    "schedule":   ("📅",  "Open Schedule",          "soft_schedule"),
    "rate":       ("💱",  "Check Exchange Rates",   "soft_rate"),
    "culture":    ("🎎",  "Cultural Tips",          "soft_culture"),
    "scam":       ("🔍",  "Run Scam Check",         "soft_scam"),
    "track":      ("📊",  "Open Tracker",           "soft_track"),
    "reminder":   ("⏰",  "Set Reminder",           "soft_reminder"),
}


async def _execute_intent(update, context, user_id, user_info, intent_result, original_text):
    """Soft-Routing: Answer naturally, then suggest a module via inline button.
    The user's message is stored so clicking the button auto-forwards it."""
    intent = intent_result["intent"]
    entities = intent_result.get("entities", {})
    korean_q = intent_result.get("korean_query")
    kb = main_keyboard()

    # ── Direct execution intents (no soft-routing needed) ─────────────────
    if intent in ("sos", "emergency"):
        await safe_send(update, format_sos_general(), reply_markup=kb)
        return

    if intent == "greeting":
        name = user_info.get("first_name", "friend")
        msg = (f"안녕 {name}! 👋\n\nJust type what you need — I understand natural language!\n\n"
               f"Examples:\n• \"I have eggs and cheese, what can I cook?\"\n"
               f"• \"find nearest pharmacy\"\n• \"I feel lonely\"\n"
               f"• \"what does 대박 mean?\"\n\nOr tap any button below 👇")
        await safe_send(update, msg, reply_markup=kb)
        return

    if intent == "level":
        await safe_send(update, format_level_status(user_id), reply_markup=kb)
        return

    if intent == "profile":
        await safe_send(update, _build_status_card(user_id, user_info), reply_markup=kb)
        return

    # ── Self-Updating Memory ──────────────────────────────────────────────
    if intent == "save_memory":
        key = entities.get("key", "").lower().strip()
        value = entities.get("value", "").strip()
        if key and value:
            # Map to known DB columns
            MEMORY_MAP = {
                "visa": "visa_type", "university": "university", "uni": "university",
                "city": "city", "diet": "diet", "major": "major",
                "age": "age", "country": "country", "arrival": "arrival_date",
            }
            db_key = MEMORY_MAP.get(key, key)
            # Only save to known user columns
            SAFE_COLUMNS = {"university", "city", "diet", "arrival_date", "visa_type", "major", "age", "country"}
            if db_key in SAFE_COLUMNS:
                try:
                    update_user(user_id, **{db_key: value})
                    await safe_send(update, f"✅ Got it! I'll remember your {key}: **{value}**\nThis is saved permanently to your profile.", reply_markup=kb)
                except Exception as e:
                    logger.warning("Memory save failed for %s: %s", key, e)
                    await safe_send(update, f"I noted your {key} is {value}, but couldn't save it right now. Tell me again later!", reply_markup=kb)
            else:
                # For unknown keys, just acknowledge conversationally
                await safe_send(update, f"Got it, I'll keep that in mind! Your {key} is {value}.", reply_markup=kb)
        else:
            # Fallback to general question
            await process_message(update, context, original_text)
        return

    # ── Soft-Routing: AI answers + suggestion button ──────────────────────
    if intent in _SOFT_BUTTONS:
        emoji, label, callback_data = _SOFT_BUTTONS[intent]

        # Save the user's original message so we can auto-forward it when they click
        save_message(user_id, "user", original_text)

        # Fast, predictable conversational response (bypasses heavy LLM to avoid reasoning hallucinations)
        fast_replies = {
            "cook": "🧑‍🍳 I can help you cook that! Tap below to open DormChef.",
            "map": "🗺️ I can find directions for that! Tap below to open Maps.",
            "buddy": "💬 I'm right here! Tap below to chat with me.",
            "interpret": "🔮 I can translate and explain that! Tap below to use the Interpreter.",
            "simulate": "🎮 Let's simulate that! Tap below to start.",
            "practice": "🧠 Want to practice saying that in Korean? Tap below.",
            "news": "📰 I can fetch the latest news on that! Tap below.",
            "visa": "📡 Need visa info? Tap below to open Visa Radar.",
        }
        ai_response = fast_replies.get(intent, f"{emoji} I can help with that! Tap below to start.")

        # Build suggestion button
        suggestion_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{emoji} {label}", callback_data=callback_data)]
        ])

        await safe_send(update, ai_response, reply_markup=suggestion_kb)
        save_message(user_id, "assistant", ai_response[:500])
        return

    # ── Default: general_question — full AI pipeline ──────────────────────
    await process_message(update, context, original_text)





# ── Onboarding ────────────────────────────────────────────────────────────────

def _start_onboarding(user_id: int) -> str:
    _onboarding[user_id] = {"step": 0, "data": {}}
    step = ONBOARDING_STEPS[0]
    return (
        "Welcome! Let me set up your profile so I can give you personalised help.\n\n"
        "Takes about 1 minute. Type 'skip' for any question.\n\n"
        f"{step['q']}"
    )


def _is_in_onboarding(user_id: int) -> bool:
    return user_id in _onboarding


def _onboarding_keyboard(user_id: int) -> ReplyKeyboardMarkup | None:
    state = _onboarding.get(user_id)
    if not state:
        return None
    step = ONBOARDING_STEPS[state["step"]]
    if "keyboard" not in step:
        return None
    rows = [[KeyboardButton(opt) for opt in row] for row in step["keyboard"]]
    rows.append([KeyboardButton("skip")])
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)


async def _process_onboarding(update: Update, user_id: int, answer: str):
    state = _onboarding[user_id]
    step_idx = state["step"]
    step = ONBOARDING_STEPS[step_idx]

    # Save answer
    if answer.lower().strip() not in ("skip", "s", "-", "none"):
        state["data"][step["field"]] = answer.strip()

    state["step"] += 1

    if state["step"] >= len(ONBOARDING_STEPS):
        # Complete — persist to DB
        data = state["data"]
        del _onboarding[user_id]
        update_user(user_id, onboarding_step=-1)

        if data.get("arrival_date"):   set_arrival_date(user_id, data["arrival_date"])
        if data.get("university"):     set_university(user_id, data["university"])
        if data.get("city"):           set_city(user_id, data["city"])
        if data.get("diet"):
            ok, val = validate_diet(data["diet"].split()[0])  # handle "none (no restrictions)"
            if ok:
                set_diet(user_id, val)
        if data.get("allergies"):
            for a in data["allergies"].replace(",", " ").split():
                ok, val = validate_allergy(a.strip())
                if ok:
                    add_allergy(user_id, val)

        summary = "\n".join(f"  {k}: {v}" for k, v in data.items() if v)
        msg = (
            "✅ Profile saved!\n\n"
            f"{summary}\n\n"
            "I'll use this to personalise food safety, housing, and schedule advice.\n\n"
            "Try:\n"
            "  📅 /schedule — your first week plan\n"
            "  🇰🇷 /word — today's Korean word\n"
            "  🗺️ /map immigration — find the ARC office\n\n"
            "Or just describe any situation you're facing."
        )
        await safe_send(update, msg, reply_markup=nav_keyboard())
        return

    # Next step
    next_step = ONBOARDING_STEPS[state["step"]]
    msg = f"Got it!\n\n{next_step['q']}"
    kb = _onboarding_keyboard(user_id)
    await safe_send(update, msg, reply_markup=kb)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          text: str, image_bytes: bytes = None):
    user    = update.effective_user
    user_id = user.id
    name    = user.first_name or "friend"

    if is_rate_limited(user_id):
        await update.message.reply_text("⏳ Slow down a bit! Wait a moment before sending more.")
        return

    user_info = get_or_create_user(user_id, user.username or "", name)
    streak    = update_streak(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    text_lower = text.lower().strip()

    # Quick keyword routing removed — Soft-Routing handles all module suggestions via buttons

    # ── Risk scan ───────────────────────────────────────────────────────────
    scan_result = scan_message(text, user_info)
    category    = scan_result.get("category", "general")
    risk_level  = scan_result.get("risk_level", "LOW")

    logger.info("User %d | cat:%s risk:%s crisis:%s scam:%s",
                user_id, category, risk_level,
                scan_result.get("is_crisis"), scan_result.get("is_scam"))

    # Crisis: immediate — no AI delay
    if scan_result.get("is_crisis"):
        msg = (
            "🆘 You Matter — Help Is Available Right Now\n\n"
            "I hear that you're going through something really painful. You don't have to face this alone.\n\n"
            "Please reach out right now:\n"
            "📞 1393 — Korea Crisis Line (24/7, Korean/English, free)\n"
            "📞 1345 — Foreigner Support Line (24/7, multilingual)\n"
            "📞 119 — Emergency services\n\n"
            "At your university:\n"
            "학생상담센터 (Student Counseling Center) — FREE, confidential, often has English speakers.\n"
            "Just saying 'I'm not doing well' is enough. They've seen this before.\n\n"
            "This feeling won't last forever, even though it feels like it will right now. 💙"
        )
        await safe_send(update, msg)
        log_situation(user_id, "mental", "HIGH", short_summary(text), "CRISIS")
        return

    # ── AI context ──────────────────────────────────────────────────────────
    ai_context = build_context_for_ai(scan_result, user_info)
    history    = get_history(user_id)

    if image_bytes:
        ai_response = await analyze_image_async(image_bytes, text)
        provider    = "gemini"
    else:
        ai_response, provider = await ask_ai_async(
            text,
            conversation_history=history[-6:],
            extra_context=ai_context,
        )

    if ai_response:
        prefix = "🔴 RISK DETECTED\n\n" if risk_level == "HIGH" and not scan_result.get("is_crisis") else ""
        final  = prefix + ai_response
    else:
        final = _fallback(scan_result)

    await safe_send(update, final, reply_markup=nav_keyboard())

    save_message(user_id, "user", text)
    if ai_response:
        save_message(user_id, "assistant", ai_response[:1000])
    log_situation(user_id, category, risk_level, short_summary(text))

    if streak > 0 and streak % 7 == 0:
        await update.message.reply_text(f"🔥 {streak}-day streak! You're building your Korea survival skills!")


def _fallback(scan_result: dict) -> str:
    category = scan_result.get("category", "general")
    return {
        "food":     "For food safety: always check for 돼지고기 (pork) and 주정 (alcohol). Add GROQ_API_KEY to .env for full AI responses.",
        "housing":  "NEVER pay deposit without a written contract. Check property at iros.go.kr. Register at 주민센터 within 14 days.",
        "mental":   "You're not alone. Call 1345 (24/7, English) or visit your university's 학생상담센터.",
        "general":  "Emergency: 112 police, 119 ambulance, 1345 foreigner help. Add GROQ_API_KEY to .env for AI responses.",
    }.get(category, "Add GROQ_API_KEY to your .env file to enable AI responses. Emergency: 112 / 119 / 1345.")


# ── Command Handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = get_or_create_user(user.id, user.username or "", user.first_name or "")

    # New user → start onboarding
    if user_info.get("onboarding_step") == 0 and not user_info.get("university"):
        msg = _start_onboarding(user.id)
        kb = _onboarding_keyboard(user.id)
        await safe_send(update, msg, reply_markup=kb)
        return

    msg = (
        f"안녕 {user.first_name}! 👋 I'm your Korea survival companion 🇰🇷\n\n"
        "I understand natural language — no commands needed!\n\n"
        "Try typing:\n"
        "• \"I have 2 eggs, what can I cook?\"\n"
        "• \"find nearest halal restaurant\"\n"
        "• \"I feel lonely\"\n"
        "• \"what does 대박 mean?\"\n\n"
        "Or tap any button below 👇"
    )
    await safe_send(update, msg, reply_markup=main_keyboard())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "K-Transition OS v5 — Commands\n"
        "══════════════════════════════\n\n"
        "🔥 KILLER FEATURES\n"
        "/simulate — Culture Shock Simulator (interactive!)\n"
        "/interpret [text] — AI Cultural Interpreter\n"
        "/buddy [message] — Chat with your AI friend Minsu\n"
        "/cook [ingredients] — DormChef AI recipes\n\n"
        "📅 DAILY ESSENTIALS\n"
        "/challenge — Today's survival challenge\n"
        "/visa — Visa & deadline tracker\n"
        "/sos — Emergency quick access\n"
        "/level — Your Korea level & XP\n\n"
        "🇰🇷 KOREAN LEARNING\n"
        "/practice [scenario] — AI Korean roleplay\n"
        "/quiz — Adaptive Korean quiz\n"
        "/word — Word of the day\n"
        "/phrase [topic] — Survival phrases\n\n"
        "📊 TRACKING & PLANNING\n"
        "/track — Your custom trackers\n"
        "/schedule — First week plan\n"
        "/task — Personal task manager\n\n"
        "📱 USEFUL INFO\n"
        "/apps — Must-have Korean apps\n"
        "/hack [topic] — Life hacks\n"
        "/map [place] — Find places\n"
        "/rate — Exchange rates\n"
        "/news — Korea news\n\n"
        "⚙️ SETUP\n"
        "/setup — Profile wizard\n"
        "/profile — View profile\n"
        "/setdiet /setallergy /setuni /setcity\n\n"
        "Or just describe ANY situation naturally!"
    )
    await safe_send(update, msg, reply_markup=nav_keyboard())


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username or "", user.first_name or "")
    msg = _start_onboarding(user.id)
    kb  = _onboarding_keyboard(user.id)
    await safe_send(update, msg, reply_markup=kb)


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    progress  = get_progress(user_id)
    history   = get_situations(user_id, 3)

    diet      = user_info.get("diet", "not set")
    allergies = ", ".join(user_info.get("allergies", [])) or "none"
    uni       = user_info.get("university", "not set")
    city      = user_info.get("city", "not set")
    streak    = user_info.get("streak", 0)
    words     = progress.get("korean_words", 0)
    correct   = progress.get("quiz_correct", 0)
    total     = progress.get("quiz_total", 0)
    level     = progress.get("quiz_level", 1)
    pct       = f"{int(correct/total*100)}%" if total else "N/A"

    msg = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Your Profile\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎓 University: {uni}\n"
        f"🏙️ City: {city}\n"
        f"🍽️ Diet: {diet}\n"
        f"⚠️ Allergies: {allergies}\n"
        f"🔥 Streak: {streak} days\n\n"
        f"Korean Progress (Level {level}/5):\n"
        f"📚 Words learned: {words}\n"
        f"🎯 Quiz accuracy: {pct} ({correct}/{total})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"/setdiet  /setallergy  /setuni  /setcity"
    )
    await safe_send(update, msg, reply_markup=nav_keyboard())


async def cmd_setdiet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts   = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Usage: /setdiet halal  or  /setdiet vegetarian  or  /setdiet none")
        return
    get_or_create_user(user_id)
    ok, val = validate_diet(parts[1])
    if not ok:
        await update.message.reply_text(f"❌ {val}")
        return
    set_diet(user_id, val)
    await update.message.reply_text(f"✅ Diet saved as {val}. I'll check food questions against your {val} requirements.")


async def cmd_setallergy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts   = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Usage: /setallergy nuts  (options: nuts, peanut, dairy, gluten, eggs, fish, shellfish, soy)")
        return
    get_or_create_user(user_id)
    ok, val = validate_allergy(parts[1])
    if not ok:
        await update.message.reply_text(f"❌ {val}")
        return
    add_allergy(user_id, val)
    await update.message.reply_text(f"✅ Added allergy: {val}. I'll warn you when this appears in food you ask about.")


async def cmd_remove_allergy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts   = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Usage: /removeallergy nuts")
        return
    remove_allergy(user_id, parts[1])
    await update.message.reply_text(f"✅ Removed {parts[1]} from your allergies.")


async def cmd_setuni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts   = update.message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /setuni KAIST")
        return
    get_or_create_user(user_id)
    set_university(user_id, parts[1])
    await update.message.reply_text(f"✅ University set to: {parts[1]}")


async def cmd_setcity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts   = update.message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /setcity Seoul")
        return
    get_or_create_user(user_id)
    set_city(user_id, parts[1])
    await update.message.reply_text(f"✅ City set to: {parts[1]}")


async def cmd_setarrival(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts   = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Usage: /setarrival 2025-09-01")
        return
    get_or_create_user(user_id)
    set_arrival_date(user_id, parts[1])
    await update.message.reply_text(f"✅ Arrival date saved: {parts[1]}")


# ── Korean Learning ───────────────────────────────────────────────────────────

async def cmd_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=1)
    query = parts[1].strip() if len(parts) > 1 else ""

    if query:
        from korean_teacher import search_vocab_and_phrases
        result = search_vocab_and_phrases(query)
        await safe_send(update, result, reply_markup=nav_keyboard())
    else:
        word = get_word_of_the_day()
        add_korean_word_learned(user_id)
        await safe_send(update, format_word_of_day(word), reply_markup=nav_keyboard())


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI-powered adaptive quiz. Falls back to static pool if Groq unavailable."""
    user_id  = update.effective_user.id
    progress = get_progress(user_id)
    level    = progress.get("quiz_level", 1)
    category = _next_category(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text(f"🎯 Generating quiz question (Level {level})...")

    # Try AI-generated quiz
    question = await generate_quiz_question_async(level, category)

    # Fallback to static if AI unavailable
    if not question:
        question = get_static_quiz_question()
        if not question:
            await update.message.reply_text("Quiz unavailable right now. Try /word instead!")
            return
        question["source"] = "static"

    question["level"] = level

    # Build shuffled options
    options, correct_idx = build_quiz_options(question)
    question["_options"]     = options
    question["_correct_idx"] = correct_idx

    _active_quizzes[user_id] = question

    # Keyboard: one button per option
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"quiz_{user_id}_{i}")]
                for i, opt in enumerate(options)]

    msg = format_ai_quiz_message(question)
    await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz button press. Validates callback before processing (Bug 7 fix)."""
    query = update.callback_query
    await query.answer()

    data = query.data
    # Validate format: quiz_{user_id}_{option_index}
    parts = data.split("_")
    if len(parts) != 3 or parts[0] != "quiz":
        await query.edit_message_text("This quiz expired. Start a new one with /quiz")
        return

    try:
        user_id  = int(parts[1])
        selected = int(parts[2])
    except ValueError:
        await query.edit_message_text("This quiz expired. Start a new one with /quiz")
        return

    question = _active_quizzes.get(user_id)
    if not question:
        await query.edit_message_text("Quiz expired! Start a new one with /quiz")
        return

    correct_idx = question["_correct_idx"]
    is_correct  = (selected == correct_idx)

    record_quiz_answer(user_id, is_correct)
    if is_correct:
        add_korean_word_learned(user_id)

    result = format_quiz_result(question, selected, correct_idx)

    # Check if levelled up
    progress = get_progress(user_id)
    new_level = progress.get("quiz_level", 1)
    old_level = question.get("level", 1)
    if is_correct and new_level > old_level:
        result += f"\n\n🎉 Level up! You're now Level {new_level}/5!"

    await query.edit_message_text(result)
    _active_quizzes.pop(user_id, None)


async def cmd_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split(maxsplit=1)
    topic = parts[1].strip().lower() if len(parts) > 1 else ""
    if not topic:
        topics = get_topic_list()
        msg = "📚 Phrase Topics:\n\n" + "\n".join(f"• /phrase {t}" for t in topics)
        await safe_send(update, msg, reply_markup=nav_keyboard())
        return

    # If the topic matches any predefined topic, show the phrases
    available_topics = [t.lower() for t in get_topic_list()]
    if topic in available_topics:
        phrases = get_survival_phrases(topic)
        await safe_send(update, format_phrases_list(phrases, f"Phrases — {topic.title()}"), reply_markup=nav_keyboard())
    else:
        # Otherwise, globally search!
        from korean_teacher import search_vocab_and_phrases
        result = search_vocab_and_phrases(topic)
        await safe_send(update, result, reply_markup=nav_keyboard())


async def cmd_alphabet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send(update, get_alphabet_lesson(), reply_markup=nav_keyboard())


async def cmd_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send(update, get_numbers_lesson(), reply_markup=nav_keyboard())


async def cmd_pronunciation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send(update, get_pronunciation_tips(), reply_markup=nav_keyboard())


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    progress  = get_progress(user_id)

    words   = progress.get("korean_words", 0)
    correct = progress.get("quiz_correct", 0)
    total   = progress.get("quiz_total", 0)
    level   = progress.get("quiz_level", 1)
    streak  = user_info.get("streak", 0)
    pct     = f"{int(correct/total*100)}%" if total else "0%"

    labels = {1:"Beginner 🌱", 2:"Elementary 🌿", 3:"Intermediate 🌳", 4:"Upper-Intermediate 🏅", 5:"Advanced 🏆"}
    msg = (
        f"📊 Learning Progress\n\n"
        f"🔥 Streak: {streak} days\n"
        f"📚 Words learned: {words}\n"
        f"🎯 Quiz: {correct}/{total} ({pct})\n"
        f"🇰🇷 Level: {level}/5 — {labels.get(level,'')}\n\n"
        f"Next level in: {10 - (correct % 10)} correct answers\n\n"
        f"Keep going! /quiz and /word daily = fastest improvement."
    )
    await safe_send(update, msg, reply_markup=nav_keyboard())


# ── Schedule ──────────────────────────────────────────────────────────────────

async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts     = update.message.text.strip().split()
    sub       = parts[1].lower() if len(parts) > 1 else ""

    if sub == "ai":
        await update.message.reply_text("🤖 Generating your personalised schedule...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        result = await generate_ai_schedule(user_info)
        await safe_send(update, result, reply_markup=nav_keyboard())
    elif sub in ("week2", "week3", "week4"):
        week = int(sub[-1])
        await safe_send(update, get_week_tasks(week), reply_markup=nav_keyboard())
    else:
        await safe_send(update, get_first_week_checklist(user_info), reply_markup=nav_keyboard())


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send(update, get_month_overview(), reply_markup=nav_keyboard())


# ── Personal Tasks ────────────────────────────────────────────────────────────

async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    parts   = update.message.text.strip().split(maxsplit=2)

    if len(parts) < 2:
        await update.message.reply_text(
            "Task commands:\n"
            "/task add [title] — add a task\n"
            "/task list — see pending tasks\n"
            "/task done [id] — mark complete\n"
            "/task delete [id] — delete"
        )
        return

    sub = parts[1].lower()

    if sub == "add":
        title = parts[2] if len(parts) > 2 else ""
        if not title:
            await update.message.reply_text("Usage: /task add Get T-Money card")
            return
        tid = add_task(user_id, title)
        await update.message.reply_text(f"✅ Task #{tid} added: {title}")

    elif sub == "list":
        tasks = get_tasks(user_id)
        if not tasks:
            await update.message.reply_text("No pending tasks! Add one with /task add [title]")
            return
        msg = "📋 Pending Tasks:\n\n"
        for t in tasks:
            msg += f"#{t['id']}  {t['title']}\n"
        await update.message.reply_text(msg)

    elif sub == "done":
        try:
            tid = int(parts[2])
            complete_task(user_id, tid)
            await update.message.reply_text(f"✅ Task #{tid} completed!")
        except (ValueError, IndexError):
            await update.message.reply_text("Usage: /task done [id]  (get id from /task list)")

    elif sub == "delete":
        try:
            tid = int(parts[2])
            delete_task(user_id, tid)
            await update.message.reply_text(f"🗑️ Task #{tid} deleted.")
        except (ValueError, IndexError):
            await update.message.reply_text("Usage: /task delete [id]")
    else:
        await update.message.reply_text("Unknown sub-command. Try: add | list | done | delete")


# ── News / Maps / Emergency ───────────────────────────────────────────────────

async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📰 Fetching latest Korea news...")
    news = get_news(max_items=5)
    await safe_send(update, format_news(news), reply_markup=nav_keyboard())


async def cmd_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split(maxsplit=1)
    user_info = get_or_create_user(update.effective_user.id)
    city = user_info.get("city", "")
    kb = main_keyboard()
    if len(parts) < 2:
        msg = "🗺️ Find a Place\n\nType /map [place] or just describe where you want to go\n\nShortcuts:\n"
        for key, place in list(IMPORTANT_PLACES.items())[:7]:
            msg += f"• /map {key} — {place['name']}\n"
        msg += "\nAll results show Naver + Kakao + Google Maps links!"
        await safe_send(update, msg, reply_markup=kb)
        return
    query = parts[1].lower().strip()
    # Zero-Click Map Guide — show download + how-to-use
    if query in ("guide", "help", "apps", "download"):
        await safe_send(update, format_map_guide(), reply_markup=kb)
        return
    msg, venue = format_place_info(query, city)
    if msg:
        await safe_send(update, msg, reply_markup=kb)
        return
    korean_q = translate_to_korean(query)
    korean_override = korean_q if korean_q.lower() != query.lower() else None
    await safe_send(update, format_map_response(parts[1], city, korean_override), reply_markup=kb)


async def cmd_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🚨 Emergency Numbers — Korea\n\n"
        "📞 112 — Police (say 'English please')\n"
        "📞 119 — Fire + Ambulance\n"
        "📞 1345 — Foreigner Helpline (24/7, many languages)\n"
        "📞 1393 — Crisis/Suicide Line (24/7, free)\n"
        "📞 182 — Cyber crime\n\n"
        "Non-emergency:\n"
        "🏥 Nearest hospital: search 응급실 on Naver Maps\n"
        "🏛️ Immigration: HiKorea.go.kr or 1345\n\n"
        "Useful phrases:\n"
        "도와주세요! = Help!\n"
        "영어 통역사 불러주세요 = Please call English interpreter\n\n"
        "💡 Save 112, 119, 1345 in your phone RIGHT NOW"
    )
    await safe_send(update, msg, reply_markup=nav_keyboard())


async def cmd_speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open the AI Korean Speaker MiniApp (Negotiator)."""
    negotiator_url = os.getenv("NEGOTIATOR_URL", "")
    if not negotiator_url:
        await safe_send(update, "⚠️ AI Speaker URL not configured. Set NEGOTIATOR_URL in .env", reply_markup=main_keyboard())
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 Open AI Korean Speaker", web_app=WebAppInfo(url=negotiator_url))]
    ])
    msg = (
        "🤝 AI Korean Speaker\n\n"
        "AI speaks Korean FOR YOU in real-time!\n\n"
        "📱 How it works:\n"
        "1. Pick a situation (market, pharmacy, restaurant...)\n"
        "2. Describe your goal\n"
        "3. AI speaks Korean to the person for you\n"
        "4. Record their response → AI translates + responds\n\n"
        "Features:\n"
        "• 🎙️ Real-time voice translation\n"
        "• 🤫 Whisper secret instructions to AI\n"
        "• 🚨 SOS fake bail-out button\n"
        "• 📊 Post-session analysis + score\n"
        "• 🧠 Survival vocab extraction\n\n"
        "Tap below to start 👇"
    )
    await safe_send(update, msg, reply_markup=kb)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = get_situations(user_id, 5)
    if not history:
        await update.message.reply_text("No history yet! Ask me about your first situation.")
        return
    icons = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    msg = "📋 Recent Situations\n\n"
    for item in history:
        icon = icons.get(item.get("risk", "LOW"), "⚪")
        msg += f"{icon} [{item.get('category','?').upper()}] {item.get('summary','')} — {item.get('timestamp','')}\n"
    await safe_send(update, msg, reply_markup=nav_keyboard())


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from memory import clear_history
    clear_history(update.effective_user.id)
    await update.message.reply_text("Memory cleared! Your profile (diet, allergies, uni) is still saved.")


# ── Differentiator commands ───────────────────────────────────────────────────

async def cmd_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_or_create_user(update.effective_user.id)
    parts  = update.message.text.strip().split()
    amount = 10000
    if len(parts) > 1:
        try:
            amount = int(parts[1].replace(",", ""))
        except ValueError:
            pass
    await update.message.reply_text("Fetching live rates...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await safe_send(update, format_exchange_rates(amount), reply_markup=nav_keyboard())


async def cmd_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts     = update.message.text.strip().split(maxsplit=1)
    name      = parts[1].strip() if len(parts) > 1 else (user_info.get("first_name") or update.effective_user.first_name or "")
    if not name:
        await update.message.reply_text("Usage: /name Ahmed")
        return
    await safe_send(update, format_korean_name(name), reply_markup=nav_keyboard())


async def cmd_culture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_or_create_user(update.effective_user.id)
    parts = update.message.text.strip().split(maxsplit=1)
    tip = None
    if len(parts) > 1:
        if parts[1].lower() == "list":
            topics = get_all_cultural_topics()
            msg = "Korean Culture Topics:\n\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))
            msg += "\n\n/culture [number] for specific topic"
            await safe_send(update, msg, reply_markup=nav_keyboard())
            return
        try:
            from differentiator import CULTURAL_TIPS
            idx = int(parts[1]) - 1
            if 0 <= idx < len(CULTURAL_TIPS):
                tip = CULTURAL_TIPS[idx]
        except (ValueError, IndexError):
            pass
    if tip is None:
        tip = get_cultural_tip()
    await safe_send(update, format_cultural_tip(tip), reply_markup=nav_keyboard())


async def cmd_scam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Describe the situation after /scam:\n\n"
            "Example: /scam landlord wants 5M won before signing contract"
        )
        return
    await safe_send(update, format_scam_scan(parts[1]), reply_markup=nav_keyboard())


async def cmd_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_or_create_user(update.effective_user.id)
    await safe_send(update, format_daily_tip(), reply_markup=nav_keyboard())


async def cmd_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts     = update.message.text.strip().split(maxsplit=1)
    city      = parts[1].strip() if len(parts) > 1 else user_info.get("city", "")
    if not city:
        await update.message.reply_text("Usage: /area Seoul  or  set city with /setcity Seoul")
        return
    await safe_send(update, get_area_guide(city), reply_markup=nav_keyboard())


async def cmd_places(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Important Places\n────────────────\n\n"
    for key, place in IMPORTANT_PLACES.items():
        msg += f"/map {key}\n  {place['name']}\n\n"
    msg += "Type /map [key] to get directions."
    await safe_send(update, msg, reply_markup=nav_keyboard())


async def cmd_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send(update, get_news_for_students(), reply_markup=nav_keyboard())


# ── Message Handlers ──────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """V6: Zero-command engine. State machine + LLM intent router."""
    user_id = update.effective_user.id
    text = clean_text(update.message.text or "")

    if len(text) < 2:
        await update.message.reply_text(
            "Just type naturally! Examples:\n"
            "• I have 2 eggs, what can I cook?\n"
            "• Find nearest pharmacy\n"
            "• I feel lonely\n"
            "• What does 대박 mean?",
            reply_markup=main_keyboard()
        )
        return

    # 1. Onboarding takes priority
    if _is_in_onboarding(user_id):
        await _process_onboarding(update, user_id, text)
        return

    user_info = get_or_create_user(user_id)
    streak = update_streak(user_id)

    # 2. Button text detection (persistent keyboard)
    if await _handle_button_text(update, context, user_id, user_info, text):
        log_message_time(user_id)
        return

    # 3. Active state check
    current_state = get_state(user_id)
    if current_state != State.IDLE:
        # Check if user is switching context (rapid intent change)
        intent_result = await route_intent(text, user_info, current_state=current_state)
        
        # If the user is just continuing the state, skip override checks
        if intent_result["intent"] == "state_continue":
            log_message_time(user_id)
            analyze_message(user_id, text)
            await _handle_active_state(update, context, user_id, user_info, text, current_state)
            return

        if should_override(user_id, intent_result["intent"], intent_result["confidence"]):
            # User switched context — exit old state, execute new intent
            clear_state(user_id)
            log_message_time(user_id)
            analyze_message(user_id, text)
            await _execute_intent(update, context, user_id, user_info, intent_result, text)
        else:
            # Stay in current state
            log_message_time(user_id)
            analyze_message(user_id, text)
            await _handle_active_state(update, context, user_id, user_info, text, current_state)
        return

    # 4. LLM Intent Router (replaces keyword matching)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    intent_result = await route_intent(text, user_info, current_state="IDLE")

    # 5. Execute the classified intent
    log_message_time(user_id)
    analyze_message(user_id, text)
    await _execute_intent(update, context, user_id, user_info, intent_result, text)

    if streak > 0 and streak % 7 == 0:
        await update.message.reply_text(f"🔥 {streak}-day streak! You're building your Korea survival skills!")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Feature 4: Transcribe voice notes via Groq Whisper, then process normally."""
    user_id = update.effective_user.id
    get_or_create_user(user_id)

    if not FEATURE_VOICE_NOTES:
        await update.message.reply_text("Voice notes not enabled. Type GROQ_API_KEY in .env to enable.")
        return

    placeholder = await update.message.reply_text("🎙️ Listening...")

    try:
        voice    = update.message.voice
        file_obj = await context.bot.get_file(voice.file_id)
        audio    = bytes(await file_obj.download_as_bytearray())

        text = await transcribe_audio_async(audio)

        if not text:
            await placeholder.edit_text("Couldn't transcribe. Please try again or type your message.")
            return

        await placeholder.edit_text(f"🗣️ You said: {text}")
        await process_message(update, context, text)

    except Exception as e:
        logger.error("Voice handling error: %s", e)
        await placeholder.edit_text("Voice note error. Please type your message instead.")


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze photos with Gemini Vision — food labels, contracts, Korean signs."""
    if not FEATURE_IMAGE_AI or not GEMINI_API_KEY:
        await update.message.reply_text(
            "Image analysis needs a Gemini API key.\n"
            "Get one free at aistudio.google.com and add GEMINI_API_KEY to .env"
        )
        return

    caption = clean_text(update.message.caption or "")
    await update.message.reply_text("📸 Analyzing your image...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        photo    = update.message.photo[-1]
        file_obj = await context.bot.get_file(photo.file_id)
        img      = bytes(await file_obj.download_as_bytearray())

        response = await analyze_image_async(
            img, caption or "Please analyze this image for an international student in Korea"
        )
        if response:
            await safe_send(update, response, reply_markup=nav_keyboard())
            user_id = update.effective_user.id
            save_message(user_id, "user", f"[Image]{(' - ' + caption) if caption else ''}")
            save_message(user_id, "assistant", response[:500])
        else:
            await update.message.reply_text(
                "Image analysis temporarily unavailable (Gemini free quota may be full — resets midnight Pacific).\n"
                "Describe what you see in text and I'll help!"
            )
    except Exception as e:
        logger.error("Image error: %s", e)
        await update.message.reply_text("Couldn't process the image. Describe it in text!")


# ── Navigation Callback Handler ───────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """V7: Callback handler — quiz, nav, and Soft-Routing auto-forward."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Quiz callbacks
    if data.startswith("quiz_"):
        await handle_quiz_answer(update, context)
        return

    # Simulator Option Callbacks
    if data.startswith("sim_choice_"):
        choice_letter = data.replace("sim_choice_", "")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        user_id = query.from_user.id
        user_info = get_or_create_user(user_id)
        state = get_state(user_id)
        if state == State.SIM_WAITING_CHOICE:
            ctx = get_context(user_id)
            scenario = ctx.get("scenario")
            if scenario:
                if isinstance(scenario, dict) and scenario.get("is_ai"):
                    await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
                    eval_res = await evaluate_ai_choice(scenario.get("text"), choice_letter, user_info)
                    clear_state(user_id)
                    if eval_res:
                        msg, score = eval_res
                        if score > 20:
                            add_xp(user_id, XP_REWARDS["simulate_perfect"], "simulate_perfect")
                        elif score > 0:
                            add_xp(user_id, XP_REWARDS["simulate_ok"], "simulate_ok")
                        await context.bot.send_message(chat_id=query.message.chat_id, text=msg, reply_markup=room_keyboard())
                    else:
                        await context.bot.send_message(chat_id=query.message.chat_id, text="Couldn't evaluate. Try /simulate again!", reply_markup=room_keyboard())
                else:
                    result = evaluate_choice(scenario, choice_letter)
                    clear_state(user_id)
                    if result:
                        msg, score = result
                        if score > 20:
                            add_xp(user_id, XP_REWARDS["simulate_perfect"], "simulate_perfect")
                        elif score > 0:
                            add_xp(user_id, XP_REWARDS["simulate_ok"], "simulate_ok")
                        await context.bot.send_message(chat_id=query.message.chat_id, text=msg, reply_markup=room_keyboard())
                    else:
                        await context.bot.send_message(chat_id=query.message.chat_id, text="Couldn't evaluate. Try /simulate again!", reply_markup=room_keyboard())
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Pick A, B, or C! 👆", reply_markup=simulate_keyboard())
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="No active simulation. Type /simulate to start!", reply_markup=room_keyboard())
        return

    user_id = query.from_user.id
    user_info = get_or_create_user(user_id)
    kb = main_keyboard()

    # ── Soft-Routing: Auto-forward last message into a module ─────────────
    if data == "soft_exit_room":
        clear_state(user_id)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏠 Back to main bot! Just type what you need.",
            reply_markup=kb
        )
        return

    if data.startswith("soft_"):
        # Get the user's last message from DB to auto-forward
        history = get_history(user_id)
        last_user_msg = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        # Remove suggestion button from the original message
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        module = data.replace("soft_", "")

        if module == "cook":
            if last_user_msg:
                diet = user_info.get("diet", "none")
                allergies = ", ".join(user_info.get("allergies", [])) or "none"
                await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
                result = await get_chef_recipe(last_user_msg, diet, allergies)
                add_xp(user_id, XP_REWARDS["cook_recipe"], "cook_recipe")
                set_state(user_id, State.COOK_WAITING_INGREDIENTS)
                await context.bot.send_message(chat_id=query.message.chat_id, text=result, reply_markup=room_keyboard())
            else:
                set_state(user_id, State.COOK_WAITING_INGREDIENTS)
                await context.bot.send_message(chat_id=query.message.chat_id, text="🧑‍🍳 What's in your fridge? Tell me your ingredients!", reply_markup=kb)

        elif module == "map":
            city = user_info.get("city", "")
            q = last_user_msg or "nearby"
            info, venue = format_place_info(q.lower().strip(), city)
            set_state(user_id, State.MAP_WAITING_QUERY)
            if info:
                await context.bot.send_message(chat_id=query.message.chat_id, text=info, reply_markup=room_keyboard())
            else:
                korean_q = translate_to_korean(q)
                korean_override = korean_q if korean_q.lower() != q.lower() else None
                await context.bot.send_message(chat_id=query.message.chat_id, text=format_map_response(q, city, korean_override), reply_markup=room_keyboard())

        elif module == "buddy":
            db_history = get_buddy_history(user_id, limit=6)
            set_state(user_id, State.BUDDY_ACTIVE, {"history": db_history})
            await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
            msg = last_user_msg or "hey! what's up?"
            response = await chat_with_buddy(msg, user_info, db_history)
            save_buddy_message(user_id, "user", msg)
            save_buddy_message(user_id, "assistant", response)
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"🧑 민수:\n{response}", reply_markup=room_keyboard())

        elif module == "interpret":
            if last_user_msg:
                await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.TYPING)
                result = await interpret_text(last_user_msg, user_info)
                set_state(user_id, State.INTERPRET_WAITING_TEXT)
                await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔮 Cultural Interpreter\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{result}", reply_markup=room_keyboard())
            else:
                set_state(user_id, State.INTERPRET_WAITING_TEXT)
                await context.bot.send_message(chat_id=query.message.chat_id, text="🔮 Send me any text to interpret!", reply_markup=room_keyboard())

        elif module == "simulate":
            scenario = get_random_scenario()
            set_state(user_id, State.SIM_WAITING_CHOICE, {"scenario": scenario})
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_scenario(scenario), reply_markup=simulate_keyboard())

        elif module == "practice":
            await context.bot.send_message(chat_id=query.message.chat_id, text=get_scenario_list(), reply_markup=kb)

        elif module == "news":
            news = get_news(max_items=5)
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_news(news), reply_markup=kb)

        elif module == "visa":
            arrival = user_info.get("arrival_date", "")
            data_v = get_visa_status(arrival) if arrival else None
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_visa_status(data_v), reply_markup=kb)

        elif module == "challenge":
            challenge = get_todays_challenge(user_id)
            progress = get_progress(user_id)
            streak = progress.get("streak", 0)
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_challenge(challenge, streak), reply_markup=kb)

        elif module == "quiz":
            # Can't call cmd_quiz without an update.message, so send instructions
            await context.bot.send_message(chat_id=query.message.chat_id, text="📝 Type /quiz to start a Korean quiz!", reply_markup=kb)

        elif module == "word":
            word = get_word_of_the_day()
            add_korean_word_learned(user_id)
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_word_of_day(word), reply_markup=kb)

        elif module == "phrase":
            topics = get_topic_list()
            msg = "📚 Phrase Topics:\n\n" + "\n".join(f"• /phrase {t}" for t in topics)
            await context.bot.send_message(chat_id=query.message.chat_id, text=msg, reply_markup=kb)

        elif module == "apps":
            await context.bot.send_message(chat_id=query.message.chat_id, text=get_apps_list(), reply_markup=kb)

        elif module == "hack":
            await context.bot.send_message(chat_id=query.message.chat_id, text=get_hacks(), reply_markup=kb)

        elif module == "schedule":
            await context.bot.send_message(chat_id=query.message.chat_id, text=get_first_week_checklist(user_info), reply_markup=kb)

        elif module == "rate":
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_exchange_rates(10000), reply_markup=kb)

        elif module == "culture":
            tip = get_cultural_tip()
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_cultural_tip(tip), reply_markup=kb)

        elif module == "scam":
            if last_user_msg:
                await context.bot.send_message(chat_id=query.message.chat_id, text=format_scam_scan(last_user_msg), reply_markup=kb)
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text="Describe the situation: /scam [description]", reply_markup=kb)

        elif module == "track":
            trackers = get_user_trackers(user_id)
            await context.bot.send_message(chat_id=query.message.chat_id, text=format_tracker_list(trackers), reply_markup=kb)

        elif module == "reminder":
            from datetime import timedelta
            from notifier import add_custom_reminder
            now = datetime.now(UTC)
            task = last_user_msg or "reminder"
            run_date = now + timedelta(minutes=60)
            add_custom_reminder(user_id, task, run_date)
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"⏰ Reminder set! I'll ping you about '{task}' in ~1 hour.", reply_markup=kb)

        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Feature coming soon!", reply_markup=kb)
        return

    # ── Navigation callbacks (unchanged) ──────────────────────────────────
    if data == "nav_home":
        clear_state(user_id)
        text = ("🏠 Home\n\nJust type what you need — I understand natural language!\n\n"
                "Or tap any button below 👇")
    elif data == "nav_schedule":
        text = get_first_week_checklist(user_info)
    elif data == "nav_maps":
        set_state(user_id, State.MAP_WAITING_QUERY)
        text = ("🗺️ Where do you want to go?\n\n"
                "Type a place name, directions, or nearby search.\n"
                "All results include Naver + Kakao + Google links!")
    elif data == "nav_korean":
        text = ("🇰🇷 Korean Learning\n\n"
                "/word — Word of the day\n/quiz — AI quiz\n"
                "/practice — Roleplay\n/phrase — Survival phrases\n"
                "/progress — Your stats")
    elif data == "nav_safety":
        text = format_sos_general()
    elif data == "nav_news":
        news = get_news(max_items=5)
        text = format_news(news)
    else:
        text = "Unknown action. Just type what you need!"

    try:
        await query.edit_message_text(text, reply_markup=nav_keyboard())
    except Exception:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=main_keyboard()
        )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error: %s", context.error, exc_info=True)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("Something went wrong. Try /new to reset, or try again.")



# ════════════════════════════════════════════════════════════
# V5 COMMAND HANDLERS — Killer Features
# ════════════════════════════════════════════════════════════

async def cmd_cook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=1)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""

    if not sub:
        await safe_send(update, get_recipe_categories(), reply_markup=nav_keyboard())
        return
    if sub == "equipment":
        await safe_send(update, get_equipment_guide(), reply_markup=nav_keyboard())
        return

    diet = user_info.get("diet", "none")
    allergies = ", ".join(user_info.get("allergies", [])) or "none"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    result = await get_chef_recipe(sub, diet, allergies)
    add_xp(user_id, XP_REWARDS["cook_recipe"], "cook_recipe")
    await safe_send(update, result, reply_markup=nav_keyboard())


async def cmd_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    parts = update.message.text.strip().split()
    sub = parts[1].lower() if len(parts) > 1 else ""

    challenge = get_todays_challenge(user_id)
    progress = get_progress(user_id)
    streak = progress.get("streak", 0)

    if sub == "done":
        xp_result = add_xp(user_id, XP_REWARDS["challenge_done"], "challenge_done")
        await safe_send(update, format_challenge(challenge, streak, completed=True), reply_markup=nav_keyboard())
        return
    if sub == "stats":
        total_xp = get_progress(user_id).get("quiz_correct", 0) * 15  # approx
        await safe_send(update, get_challenge_stats_text(streak, 0, total_xp), reply_markup=nav_keyboard())
        return

    await safe_send(update, format_challenge(challenge, streak), reply_markup=nav_keyboard())


async def cmd_practice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=1)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""

    if not sub:
        await safe_send(update, get_scenario_list(), reply_markup=nav_keyboard())
        return

    if sub not in KB_SCENARIOS:
        await safe_send(update, get_scenario_list(), reply_markup=nav_keyboard())
        return

    progress = get_progress(user_id)
    level = progress.get("quiz_level", 1)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    response = await start_practice(sub, level)
    set_state(user_id, State.PRACTICE_ACTIVE, {"scenario": sub, "history": [{"role": "assistant", "content": response}], "level": level})
    add_xp(user_id, XP_REWARDS["practice_session"], "practice_session")
    await safe_send(update, f"🧠 Korean Brain — Practice Mode\n\n{response}\n\n━━━━━━━━━━━━━━━━━━━━━━━━\nReply in Korean (or English!) to continue.\nType 'stop' to end practice.", reply_markup=main_keyboard())


async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=2)

    if len(parts) < 2:
        trackers = get_user_trackers(user_id)
        await safe_send(update, format_tracker_list(trackers), reply_markup=nav_keyboard())
        return

    sub = parts[1].lower()
    if sub == "new" and len(parts) > 2:
        name = parts[2].strip()
        emoji = guess_emoji(name)
        unit = guess_unit(name)
        tid = create_tracker(user_id, name, emoji, unit)
        await update.message.reply_text(f"✅ Tracker created!\n\n{emoji} {name}" + (f" ({unit})" if unit else "") + f"\n\nLog: /track {name.lower()} [value]\nStats: /track stats {name.lower()}")
        return
    if sub == "stats" and len(parts) > 2:
        tracker = get_tracker_by_name(user_id, parts[2].strip())
        if not tracker:
            await update.message.reply_text(f"Tracker '{parts[2]}' not found. /track to see your trackers.")
            return
        stats = get_tracker_stats(tracker["id"])
        recent = get_tracker_entries(tracker["id"], 5)
        await safe_send(update, format_tracker_stats(tracker, stats, recent), reply_markup=nav_keyboard())
        return

    # Try logging: /track [name] [value]
    if len(parts) > 2:
        name = sub
        try:
            value = float(parts[2].replace(",", "").replace("₩", "").replace("won", ""))
        except ValueError:
            await update.message.reply_text(f"Usage: /track {name} [number]\nExample: /track {name} 15000")
            return
        tracker = get_tracker_by_name(user_id, name)
        if not tracker:
            # Auto-create
            emoji = guess_emoji(name)
            unit = guess_unit(name)
            tid = create_tracker(user_id, name, emoji, unit)
            tracker = {"id": tid, "name": name, "emoji": emoji, "unit": unit}
        log_entry(user_id, tracker["id"], value)
        add_xp(user_id, XP_REWARDS["tracker_log"], "tracker_log")
        u = tracker.get("unit", "")
        await update.message.reply_text(f"{tracker.get('emoji', '📊')} Logged: {value:,.0f} {u} to {tracker['name']}")
        return

    trackers = get_user_trackers(user_id)
    await safe_send(update, format_tracker_list(trackers), reply_markup=nav_keyboard())


async def cmd_buddy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=1)
    msg_text = parts[1].strip() if len(parts) > 1 else ""

    if not msg_text:
        await update.message.reply_text(
            "💬 Buddy Mode — Chat with Minsu\n\n"
            "Minsu is your AI Korean friend (선배).\n"
            "He's NOT a bot — he talks like a real friend.\n\n"
            "/buddy [anything] — Talk to Minsu\n"
            "/buddy how are you\n"
            "/buddy I miss home\n"
            "/buddy what should I eat today\n\n"
            "He remembers your conversations! 🤝"
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(random.uniform(0.5, 1.5))
    # Use state_manager for buddy history
    ctx = get_context(user_id)
    history = ctx.get("history", []) if get_state(user_id) == State.BUDDY_ACTIVE else []
    response = await chat_with_buddy(msg_text, user_info, history)
    history.append({"role": "user", "content": msg_text})
    history.append({"role": "assistant", "content": response})
    set_state(user_id, State.BUDDY_ACTIVE, {"history": history[-20:]})
    await safe_send(update, f"🧑 민수:\n{response}", reply_markup=main_keyboard())


async def cmd_sos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split(maxsplit=1)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""

    if sub == "phrases":
        await safe_send(update, format_sos_phrases(), reply_markup=nav_keyboard())
    elif sub in ("lost", "sick", "scam", "accident", "harassment"):
        await safe_send(update, format_sos_guide(sub), reply_markup=nav_keyboard())
    else:
        await safe_send(update, format_sos_general(), reply_markup=nav_keyboard())


async def cmd_visa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts = update.message.text.strip().split()
    sub = parts[1].lower() if len(parts) > 1 else ""
    arrival = user_info.get("arrival_date", "")
    data = get_visa_status(arrival) if arrival else None

    if sub == "checklist":
        await safe_send(update, format_visa_checklist(data), reply_markup=nav_keyboard())
    else:
        await safe_send(update, format_visa_status(data), reply_markup=nav_keyboard())


async def cmd_simulate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=1)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""

    if sub == "topic" or sub == "topics":
        await safe_send(update, get_scenario_topics(), reply_markup=nav_keyboard())
        return

    # If sub is a topic, generate AI scenario
    if sub and sub not in ("a", "b", "c"):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        result = await generate_ai_scenario(sub, user_info)
        set_state(user_id, State.SIM_WAITING_CHOICE, {
            "scenario": {
                "is_ai": True,
                "text": result
            }
        })
        await safe_send(update, result, reply_markup=simulate_keyboard())
        return

    # Default: random pre-built scenario
    scenario = get_random_scenario()
    set_state(user_id, State.SIM_WAITING_CHOICE, {"scenario": scenario})
    await safe_send(update, format_scenario(scenario), reply_markup=simulate_keyboard())


async def cmd_interpret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=1)
    sub = parts[1].strip() if len(parts) > 1 else ""

    if not sub or sub.lower() == "menu":
        await safe_send(update, get_phrase_list(), reply_markup=nav_keyboard())
        return
    if sub.lower() == "formality":
        await safe_send(update, get_formality_guide(), reply_markup=nav_keyboard())
        return
    if sub.lower() in ("survive", "food", "social", "university", "emergency", "shopping"):
        await safe_send(update, get_phrase_list(sub.lower()), reply_markup=nav_keyboard())
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    result = await interpret_text(sub, user_info)
    await safe_send(update, f"🔮 Cultural Interpreter\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{result}", reply_markup=nav_keyboard())


async def cmd_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split(maxsplit=1)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""
    await safe_send(update, get_apps_list(sub if sub else None), reply_markup=nav_keyboard())


async def cmd_hack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=1)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""

    if not sub:
        await safe_send(update, get_hacks(), reply_markup=nav_keyboard())
        return
    # Check if it's a built-in category
    builtin = get_hacks(sub)
    if "Life Hacks" not in builtin:  # It matched a category
        await safe_send(update, builtin, reply_markup=nav_keyboard())
        return
    # AI-generated hack
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    result = await get_ai_hack(sub, user_info)
    await safe_send(update, result, reply_markup=nav_keyboard())


async def cmd_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    await safe_send(update, format_level_status(user_id), reply_markup=nav_keyboard())


# ════════════════════════════════════════════════════════════
# V4 COMMAND HANDLERS — Predictive System + Community
# ════════════════════════════════════════════════════════════

async def cmd_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    if not user_info.get("arrival_date"):
        await update.message.reply_text(
            "Set your arrival date first:\n/setarrival 2025-09-01"
        )
        return
    days  = days_since_arrival(user_info["arrival_date"])
    preds = get_todays_predictions(user_info)
    if days is not None:
        await update.message.reply_text(f"📅 {get_days_in_korea_summary(days)}")
    if not preds:
        await safe_send(update,
            "No specific predictions today — you're in a stable phase.\n\n"
            "I send proactive alerts automatically when milestones approach.\n"
            "Morning briefings: 8:30 AM KST daily.",
            reply_markup=nav_keyboard())
        return
    for pred in preds:
        await safe_send(update, format_prediction(pred))
        await asyncio.sleep(0.4)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    weather   = get_weather_score(user_id)
    score     = weather["score"]
    status    = weather["status"]
    icons  = {"healthy":"🟢","monitor":"🟡","concerning":"🟠","critical":"🔴","unknown":"⚪"}
    labels = {
        "healthy":    "Signals look good. Keep the habits that are working.",
        "monitor":    "Some signals suggest more stress than usual. Normal in Korea.",
        "concerning": "Patterns suggest a harder stretch. That's real — okay to say so.",
        "critical":   "Signs suggest you're really struggling. You don't have to carry this alone.",
        "unknown":    "Not enough data yet — talk to me more and I'll improve.",
    }
    msg = f"{icons.get(status,'⚪')} Emotional Weather: {score:.0f}/100\n\n"
    msg += labels.get(status, "") + "\n\n"
    if status in ("concerning", "critical"):
        msg += get_peer_support_message(user_info)
    elif status == "monitor":
        msg += "If anything's weighing on you — just say it here.\nOr: /community anon support [message]"
    else:
        msg += "This score updates passively as we talk. No surveys needed."
    await safe_send(update, msg, reply_markup=nav_keyboard())


async def cmd_bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_user(user_id)
    parts = update.message.text.strip().split(maxsplit=2)
    sub   = parts[1].lower() if len(parts) > 1 else ""
    if sub == "done" and len(parts) > 2:
        result = complete_milestone(user_id, parts[2].strip())
        if result:
            add_community_points(user_id, result["points"], f"milestone:{result['id']}")
            log_portfolio_event(user_id, "integration", f"Completed: {result['title']}")
            score = get_integration_score(user_id)
            await update.message.reply_text(
                f"🎉 {result['title']} unlocked!\n+{result['points']} pts\n"
                f"Integration: {score['percentage']}%\n\n💡 {result.get('prompt','Keep going!')}"
            )
        else:
            await update.message.reply_text("Milestone not found. Use /bridge list")
        return
    if sub == "list":
        await safe_send(update, format_milestone_list(), reply_markup=nav_keyboard())
        return
    await safe_send(update, format_integration_status(user_id), reply_markup=nav_keyboard())


async def cmd_career(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split(maxsplit=1)
    sub   = parts[1].lower().strip() if len(parts) > 1 else ""
    if sub in ("cv", "resume"):
        await safe_send(update, CAREER_CONTENT["cv_guide"], reply_markup=nav_keyboard())
    elif sub == "interview":
        await safe_send(update, CAREER_CONTENT["interview_guide"], reply_markup=nav_keyboard())
    elif sub in ("workplace", "work", "office"):
        await safe_send(update, CAREER_CONTENT["workplace_scenarios"], reply_markup=nav_keyboard())
    elif sub == "roleplay":
        await update.message.reply_text("🎙️ Starting Korean interview roleplay...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        prompt = (
            "Roleplay a Korean job interview. You are the Korean interviewer.\n"
            "Start with: 자기소개 해보세요 (Introduce yourself).\n"
            "Respond in Korean then add coaching in [brackets].\n"
            "Context: international GKS scholar applying for internship."
        )
        resp, _ = await ask_ai_async(prompt)
        if resp:
            await safe_send(update, resp, reply_markup=nav_keyboard())
        else:
            await update.message.reply_text("Roleplay unavailable. Try again shortly.")
    else:
        await safe_send(update,
            "🎯 Korean Career Compass\n\n"
            "/career cv — Korean CV guide\n"
            "/career interview — Interview preparation\n"
            "/career workplace — Office culture & 회식\n"
            "/career roleplay — AI interview practice\n\n"
            "💡 GKS scholarship on a Korean CV = selected from thousands globally.",
            reply_markup=nav_keyboard())


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    await update.message.reply_text("📊 Generating your Korea Competency Record...")
    portfolio = generate_portfolio(user_id, user_info)
    await safe_send(update, portfolio, reply_markup=nav_keyboard())


async def cmd_community(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_info = get_or_create_user(user_id)
    parts     = update.message.text.strip().split(maxsplit=3)
    sub       = parts[1].lower() if len(parts) > 1 else ""

    if sub == "anon":
        if len(parts) < 4:
            await update.message.reply_text(
                "Usage: /community anon [topic] [message]\n\n"
                "Topics: general | housing | food | visa | support | language | future_students | marketplace\n\n"
                "Example:\n/community anon support I've been feeling really isolated..."
            )
            return
        topic_key = parts[2].lower()
        anon_text = parts[3]
        if topic_key not in TOPICS:
            topic_key = route_message_to_topic(anon_text)
        from db import get_conn as _dbconn
        with _dbconn() as _c:
            group_row = _c.execute("SELECT group_id, topic_ids FROM community_groups LIMIT 1").fetchone()
        if not group_row:
            await update.message.reply_text(
                "Community group not set up yet.\n"
                "Ask an admin to run /setupgroup in the group."
            )
            return
        group_id  = group_row["group_id"]
        topic_ids = json.loads(group_row["topic_ids"] or "{}")
        topic_id  = topic_ids.get(topic_key)
        anon_num  = next_anon_number(group_id)
        anon_name = f"🎭 Anonymous Student #{anon_num}"
        topic_label = TOPICS.get(topic_key, {}).get("name", topic_key)
        post_text = f"{anon_name} — {topic_label}\n\n{anon_text}\n\n(Anonymous to all members)"
        try:
            kwargs = {"chat_id": group_id, "text": post_text}
            if topic_id:
                kwargs["message_thread_id"] = topic_id
            sent = await context.bot.send_message(**kwargs)
            log_anon_post(user_id, group_id, topic_id or 0, sent.message_id, anon_num)
            await update.message.reply_text(
                f"✅ Posted as {anon_name}\nTopic: {topic_label}\nYour identity is hidden."
            )
        except Exception as e:
            logger.error("Anon post failed: %s", e)
            await update.message.reply_text("Could not post right now. Is the bot in the group?")
        return

    if sub == "challenge":
        ch = get_this_weeks_challenge()
        await safe_send(update, format_weekly_challenge(ch, get_leaderboard(5)), reply_markup=nav_keyboard())
        return

    if sub == "done":
        ch = get_this_weeks_challenge()
        already, pts = complete_weekly_challenge(user_id, ch["id"])
        if already:
            await update.message.reply_text("Already completed this week! New challenge Monday.")
        else:
            await update.message.reply_text(
                f"🎉 {ch['title']}\n+{pts} pts!\n/community leaderboard to see rank."
            )
        return

    if sub == "leaderboard":
        board = get_leaderboard(10)
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        if not board:
            await update.message.reply_text("No points yet. /community challenge to start!")
            return
        msg = "🏆 Community Leaderboard\n\n"
        for i, e in enumerate(board):
            msg += f"{medals[i]} {e['display_name']} — {e['points']} pts\n"
        await safe_send(update, msg, reply_markup=nav_keyboard())
        return

    if sub == "topics":
        msg = "📋 Community Topics\n\n"
        for k, t in TOPICS.items():
            msg += f"{t['name']}\n  {t['description']}\n\n"
        msg += "Anonymous: /community anon [topic] [message]"
        await safe_send(update, msg, reply_markup=nav_keyboard())
        return

    if sub == "rules":
        await safe_send(update, get_group_rules(), reply_markup=nav_keyboard())
        return

    profile = get_or_create_community_profile(user_id, user_info.get("first_name","Student"))
    await safe_send(update,
        f"🌐 K-Transition Community\n\nYour points: {profile['points']} 🏆\n\n"
        "/community challenge    — This week's mission\n"
        "/community done         — Mark challenge complete\n"
        "/community leaderboard  — Top students\n"
        "/community topics       — Discussion topics\n"
        "/community rules        — Guidelines\n\n"
        "Anonymous posts:\n"
        "/community anon support [message]\n"
        "/community anon housing [message]\n"
        "/community anon future_students [question]",
        reply_markup=nav_keyboard())


async def cmd_setupgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("Run inside the community group.")
        return
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("Admins only.")
        return
    from db import get_conn as _dbconn
    with _dbconn() as _c:
        _c.execute(
            "INSERT OR REPLACE INTO community_groups (group_id, group_name, created_at) VALUES (?,?,?)",
            (chat.id, chat.title or "K-Transition", datetime.now(UTC).isoformat())
        )
    keys = "\n".join(f"/settopic {k} [thread_id]" for k in list(TOPICS.keys())[:5])
    await update.message.reply_text(
        f"✅ Group registered!\n\n"
        f"Enable Forum/Topics mode in group settings, then:\n{keys}\n..."
    )


async def cmd_settopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        await update.message.reply_text(f"Usage: /settopic [key] [thread_id]\nKeys: {' | '.join(TOPICS)}")
        return
    topic_key = parts[1].lower()
    try:
        topic_id = int(parts[2])
    except ValueError:
        await update.message.reply_text("Thread ID must be a number.")
        return
    from db import get_conn as _dbconn
    with _dbconn() as _c:
        row = _c.execute(
            "SELECT topic_ids FROM community_groups WHERE group_id = ?",
            (update.effective_chat.id,)
        ).fetchone()
        if not row:
            await update.message.reply_text("Group not registered. Run /setupgroup first.")
            return
        ids = json.loads(row["topic_ids"] or "{}")
        ids[topic_key] = topic_id
        _c.execute(
            "UPDATE community_groups SET topic_ids = ? WHERE group_id = ?",
            (json.dumps(ids), update.effective_chat.id)
        )
    await update.message.reply_text(
        f"✅ {TOPICS.get(topic_key,{}).get('name', topic_key)} → Thread #{topic_id}"
    )


async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in (update.message.new_chat_members or []):
        if member.is_bot:
            continue
        name = member.first_name or "friend"
        get_or_create_community_profile(member.id, name)
        add_community_points(member.id, 10, "joined_community")
        from memory import get_user as _gu
        personal  = _gu(member.id)
        is_future = not personal or not personal.get("university")
        await update.message.reply_text(get_welcome_message(name, is_future))


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    user_id = update.effective_user.id
    log_message_time(user_id)
    import random
    if random.random() < 0.08:
        add_community_points(user_id, 1, "group_participation")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN_HERE":
        print("\n" + "="*50)
        print("ERROR: Telegram token not set!")
        print("1. Copy .env.example to .env")
        print("2. Add TELEGRAM_TOKEN=your_token")
        print("3. Add GROQ_API_KEY=your_key (free at console.groq.com)")
        print("="*50 + "\n")
        return

    setup()
    # V4: setup additional tables
    setup_weather_tables()
    setup_bridge_tables()
    setup_community_tables()
    # V5: setup new feature tables
    setup_tracker_tables()
    setup_level_tables()
    logger.info("Starting K-Transition OS v%s", BOT_VERSION)

    async def post_init(application):
        from notifier import start_scheduler
        start_scheduler(application)

    # HF Servers can be slow to resolve DNS; increasing timeout to 20s
    t_request = HTTPXRequest(connection_pool_size=8, connect_timeout=20.0, read_timeout=20.0)
    app = Application.builder().token(TELEGRAM_TOKEN).request(t_request).post_init(post_init).build()

    # Commands
    for name, handler in [
        ("start", cmd_start), ("help", cmd_help), ("setup", cmd_setup),
        ("profile", cmd_profile), ("setdiet", cmd_setdiet), ("setallergy", cmd_setallergy),
        ("removeallergy", cmd_remove_allergy), ("setuni", cmd_setuni),
        ("setcity", cmd_setcity), ("setarrival", cmd_setarrival),
        ("word", cmd_word), ("quiz", cmd_quiz), ("phrase", cmd_phrase),
        ("alphabet", cmd_alphabet), ("numbers", cmd_numbers),
        ("pronunciation", cmd_pronunciation), ("progress", cmd_progress),
        ("schedule", cmd_schedule), ("month", cmd_month),
        ("task", cmd_task), ("news", cmd_news), ("map", cmd_map),
        ("emergency", cmd_emergency), ("history", cmd_history),
        ("new", cmd_new), ("rate", cmd_rate), ("name", cmd_name),
        ("culture", cmd_culture), ("scam", cmd_scam), ("tip", cmd_tip),
        ("area", cmd_area), ("places", cmd_places), ("resources", cmd_resources),
        # V4 commands
        ("predict", cmd_predict), ("weather", cmd_weather),
        ("bridge", cmd_bridge), ("career", cmd_career), ("portfolio", cmd_portfolio),
        ("community", cmd_community), ("setupgroup", cmd_setupgroup), ("settopic", cmd_settopic),
        # V5 commands
        ("cook", cmd_cook), ("challenge", cmd_challenge), ("practice", cmd_practice),
        ("track", cmd_track), ("buddy", cmd_buddy), ("sos", cmd_sos),
        ("visa", cmd_visa), ("simulate", cmd_simulate), ("interpret", cmd_interpret),
        ("apps", cmd_apps), ("hack", cmd_hack), ("level", cmd_level),
        ("speak", cmd_speak),
    ]:
        app.add_handler(CommandHandler(name, handler))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    # V4: group management
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, handle_group_message))

    # Callback handler (navigation + quiz)
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_error_handler(handle_error)

    # ── Negotiator Server (runs FastAPI on PORT for Render + MiniApp) ──────────
    # Serves the AI Korean Speaker MiniApp.
    # Also acts as keep-alive for Render (responds to HTTP health checks).
    def _start_negotiator_server():
        """Run negotiator FastAPI on PORT. Serves MiniApp + keeps Render alive."""
        import sys
        negotiator_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'negotiator2')
        if os.path.isdir(negotiator_dir):
            sys.path.insert(0, negotiator_dir)
            try:
                import uvicorn
                from main import app as negotiator_app
                port = int(os.getenv("PORT", 10000))
                logger.info("Starting Negotiator MiniApp on port %d", port)
                uvicorn.run(negotiator_app, host="0.0.0.0", port=port, log_level="warning")
            except Exception as e:
                logger.error("Negotiator server failed: %s — falling back to simple keep-alive", e)
                _simple_keepalive()
        else:
            logger.warning("negotiator2/ folder not found — using simple keep-alive")
            _simple_keepalive()

    def _simple_keepalive():
        """Fallback HTTP server if negotiator can't start."""
        class H(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"K-Transition OS v6.0 is running!")
            def log_message(self, *a): pass
        port = int(os.getenv("PORT", 10000))
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), H) as httpd:
            logger.info("Keep-alive server on port %d", port)
            httpd.serve_forever()

    # Monorepo Deployment Switch
    if os.getenv("RUN_NEGOTIATOR", "true").lower() == "true":
        threading.Thread(target=_start_negotiator_server, daemon=True).start()
    else:
        logger.info("RUN_NEGOTIATOR is false — starting lightweight keep-alive only.")
        threading.Thread(target=_simple_keepalive, daemon=True).start()

    logger.info("Bot running! Press CTRL+C to stop.")
    
    # Python 3.12+ / 3.14 requires an active event loop before run_polling
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

