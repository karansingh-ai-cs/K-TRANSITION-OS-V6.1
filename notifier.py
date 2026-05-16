# notifier.py — K-Transition OS v4.0
# ═══════════════════════════════════════════════════════════
# ALL PROACTIVE NOTIFICATIONS
# ═══════════════════════════════════════════════════════════
#
# Schedule (KST = UTC+9):
#   08:30 KST  — Morning briefing (word + pending tasks + prediction)
#   09:00 KST  — Arrival milestones check
#   21:00 KST  — Evening check-in (first 14 days only)
#   Monday 09:00 — Weekly challenge post to community groups
#   Daily      — Emotional weather check (silent, triggers only if needed)
#   Every 6h   — Silence detection check

import logging
import asyncio
from datetime import datetime, UTC
from telegram import Bot
from telegram.error import TelegramError

from config import TELEGRAM_TOKEN
from memory import get_user, get_tasks, update_user
from korean_teacher import get_word_of_the_day, format_word_of_day
from predictor import get_todays_predictions, format_prediction
from emotional_weather import (
    should_checkin, record_checkin_sent, get_checkin_message,
    get_peer_support_message, check_silence
)
from community_bot import (
    get_this_weeks_challenge, format_weekly_challenge, get_leaderboard
)

logger = logging.getLogger(__name__)


async def _send_safe(bot: Bot, chat_id: int, text: str):
    """Send with 4096-char limit handling."""
    try:
        for i in range(0, len(text), 4000):
            await bot.send_message(chat_id=chat_id, text=text[i:i+4000])
            if i + 4000 < len(text):
                await asyncio.sleep(0.3)
    except TelegramError as e:
        logger.warning("Could not send to %d: %s", chat_id, e)


async def morning_briefing(bot: Bot, user_id: int):
    """08:30 KST — word of day + pending tasks + prediction if any."""
    user = get_user(user_id)
    if not user:
        return

    name   = user.get("first_name", "friend")
    tasks  = get_tasks(user_id)
    word   = get_word_of_the_day()
    preds  = get_todays_predictions(user)

    lines = [f"☀️ Good morning {name}!"]

    # Word of the day teaser
    if word:
        lines.append(f"\n🇰🇷 Today's word: {word.get('korean','')} — {word.get('meaning','')}")
        lines.append("(/word for full lesson)")

    # Pending tasks
    if tasks:
        count = len(tasks)
        lines.append(f"\n📋 You have {count} pending task{'s' if count>1 else ''}. /task list to see them.")

    # Proactive prediction
    if preds:
        pred = preds[0]
        lines.append(f"\n🔮 {pred['title']}")
        lines.append(pred["message"][:200] + "..." if len(pred["message"]) > 200 else pred["message"])
        lines.append(f"✅ Today: {pred['micro_action']}")
        lines.append("(/predict for full details)")

    await _send_safe(bot, user_id, "\n".join(lines))


async def arrival_milestone_check(bot: Bot, user_id: int):
    """09:00 KST — check predictions and send if relevant today."""
    user  = get_user(user_id)
    if not user:
        return
    preds = get_todays_predictions(user)
    for pred in preds:
        msg = format_prediction(pred)
        await _send_safe(bot, user_id, msg)
        await asyncio.sleep(1)


async def evening_checkin(bot: Bot, user_id: int):
    """21:00 KST — first 14 days only. Gentle daily check."""
    from predictor import days_since_arrival
    user = get_user(user_id)
    if not user:
        return

    days = None
    if user.get("arrival_date"):
        days = days_since_arrival(user["arrival_date"])

    if days is None or days > 14:
        return

    name = user.get("first_name", "friend")
    messages = [
        f"How was Day {days} in Korea, {name}? One word is fine. 🙂",
        f"Evening check-in! One small win from today? Anything counts.",
        f"Day {days}! What's one thing that surprised you today?",
        f"Hey {name} — how are you holding up? No right answer needed.",
        f"Quick evening check: what did you eat today? 🍜 (genuinely curious)",
    ]

    import random
    msg = random.choice(messages)
    await _send_safe(bot, user_id, msg)


async def emotional_weather_check(bot: Bot, user_id: int):
    """Daily silent check — only sends if signals suggest support needed."""
    user = get_user(user_id)
    if not user:
        return

    trigger, reason = should_checkin(user_id)
    if not trigger:
        return

    logger.info("Emotional weather check-in triggered for user %d (reason: %s)", user_id, reason)

    checkin_id = record_checkin_sent(user_id)
    msg = get_checkin_message(user)
    await _send_safe(bot, user_id, msg)

    # 2 hours later if no response → peer support suggestion (handled in bot.py on response)


async def silence_check(bot: Bot, user_id: int):
    """Check if user has been completely silent for 5+ days."""
    user = get_user(user_id)
    if not user:
        return

    if check_silence(user_id, days=5):
        name = user.get("first_name", "friend")
        msg = (
            f"Hey {name} — haven't heard from you in a few days. "
            f"Just checking in to make sure you're okay. "
            f"Even a quick 'all good' helps! 💙"
        )
        await _send_safe(bot, user_id, msg)


async def post_weekly_challenge_to_group(bot: Bot, group_id: int):
    """Monday 09:00 KST — post weekly challenge to community group."""
    challenge   = get_this_weeks_challenge()
    leaderboard = get_leaderboard(5)
    msg         = format_weekly_challenge(challenge, leaderboard)
    try:
        await bot.send_message(chat_id=group_id, text=msg)
        logger.info("Weekly challenge posted to group %d", group_id)
    except TelegramError as e:
        logger.warning("Could not post to group %d: %s", group_id, e)


async def post_word_to_group(bot: Bot, group_id: int, topic_id: int = None):
    """Daily morning — post word of day to language exchange topic."""
    word = get_word_of_the_day()
    msg  = format_word_of_day(word)
    msg += "\n\nReply with an example sentence using this word! Best one gets 10 community points 🏆"
    try:
        kwargs = {"chat_id": group_id, "text": msg}
        if topic_id:
            kwargs["message_thread_id"] = topic_id
        await bot.send_message(**kwargs)
    except TelegramError as e:
        logger.warning("Could not post word to group: %s", e)


def start_scheduler(application):
    """
    Start APScheduler. Call this in bot.py main() after app is built.
    
    Usage in bot.py:
        from notifier import start_scheduler
        start_scheduler(app)
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz
    except ImportError:
        logger.warning("APScheduler not installed — proactive notifications disabled. pip install apscheduler pytz")
        return

    KST = pytz.timezone("Asia/Seoul")
    scheduler = AsyncIOScheduler(timezone=KST)
    bot = application.bot

    async def run_for_all_users(coro_fn, *args):
        """
        FIX: 0.3s stagger between users prevents Supabase connection pool
        exhaustion. 60-connection free tier limit. Without stagger, 500 users
        firing simultaneously = pool exhausted = silent notification failures.
        """
        from db import get_conn
        try:
            with get_conn() as conn:
                rows = conn.execute("SELECT user_id FROM users").fetchall()
            for row in rows:
                try:
                    await coro_fn(bot, row["user_id"], *args)
                    await asyncio.sleep(0.3)  # stagger: ~3 users/sec max
                except Exception as e:
                    logger.warning("Notification error for user %s: %s", row["user_id"], e)
        except Exception as e:
            logger.error("run_for_all_users error: %s", e)

    async def flush_notification_queue():
        """
        ARCHITECTURAL FIX: Decouple FastAPI writes from bot sends.
        FastAPI writes to pending_notifications. This job (bot process) sends.
        Solves 3-event-loop conflict: FastAPI uvicorn / PTB / APScheduler.
        """
        from db import get_conn
        try:
            with get_conn() as conn:
                pending = conn.execute(
                    "SELECT id, user_id, message FROM pending_notifications "
                    "WHERE sent = 0 ORDER BY created_at ASC LIMIT 20"
                ).fetchall()
                for row in pending:
                    try:
                        await bot.send_message(chat_id=row["user_id"], text=row["message"])
                        conn.execute(
                            "UPDATE pending_notifications SET sent = 1 WHERE id = ?",
                            (row["id"],)
                        )
                        conn.commit()
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.warning("Queue flush error for user %d: %s", row["user_id"], e)
        except Exception as e:
            logger.error("Notification queue flush error: %s", e)

    async def supabase_keepalive():
        """
        CRITICAL FIX: Supabase free tier pauses DB after 7 days of inactivity.
        Paused DB = 10-30 second timeout for first user after quiet period.
        Ping every 3 days keeps it warm. Cost: 1 query per 3 days.
        """
        from db import get_conn
        try:
            with get_conn() as conn:
                conn.execute("SELECT 1")
            logger.info("Keep-alive ping OK — DB is awake")
        except Exception as e:
            logger.error("Keep-alive ping failed: %s", e)

    # Morning briefing 08:30 KST
    scheduler.add_job(
        run_for_all_users,
        CronTrigger(hour=8, minute=30, timezone=KST),
        args=[morning_briefing],
        id="morning_briefing",
        max_instances=1,
        misfire_grace_time=600,
    )

    # Arrival milestones 09:00 KST
    scheduler.add_job(
        run_for_all_users,
        CronTrigger(hour=9, minute=0, timezone=KST),
        args=[arrival_milestone_check],
        id="arrival_milestones",
        max_instances=1,
        misfire_grace_time=600,
    )

    # Evening check-in 21:00 KST (first 14 days only — filtered inside function)
    scheduler.add_job(
        run_for_all_users,
        CronTrigger(hour=21, minute=0, timezone=KST),
        args=[evening_checkin],
        id="evening_checkin"
    )

    # Emotional weather — daily 14:00 KST (5pm Korea but not intrusive hour)
    scheduler.add_job(
        run_for_all_users,
        CronTrigger(hour=14, minute=0, timezone=KST),
        args=[emotional_weather_check],
        id="emotional_weather"
    )

    # Silence check — every 6 hours
    scheduler.add_job(
        run_for_all_users,
        CronTrigger(hour="*/6", timezone=KST),
        args=[silence_check],
        id="silence_check"
    )

    # Notification queue flush — every 10 seconds (decoupled send loop)
    scheduler.add_job(
        flush_notification_queue,
        "interval",
        seconds=10,
        id="queue_flush",
        max_instances=1,
    )

    # Supabase / DB keep-alive — every 3 days at 6am KST
    scheduler.add_job(
        supabase_keepalive,
        CronTrigger(day="*/3", hour=6, minute=0, timezone=KST),
        id="db_keepalive",
    )

    scheduler.start()
    logger.info("Scheduler started — queue flush 10s, keep-alive 3d, stagger 0.3s/user")
    return scheduler
