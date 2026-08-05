# life_manager.py — K-Transition OS v6.0
# Centralized Life Manager Dashboard & Proactive Assistant
# Handles morning task agendas, evening reviews, deadlines, and staggered alerts

import logging
from datetime import datetime, UTC, timedelta
from memory import get_user, get_tasks, add_task, update_user
from smart_tracker import get_user_trackers, get_yesterday_total, get_month_total

logger = logging.getLogger(__name__)

def generate_morning_agenda(user_id: int) -> list[str]:
    """Generates a smart morning daily agenda and task suggestions."""
    lines = []
    tasks = get_tasks(user_id)
    pending = [t for t in tasks if not t.get("done")]

    # 1. Suggest routine / recurring tasks
    trackers = get_user_trackers(user_id)
    if trackers:
        lines.append("\n💡 **Suggested Routine Habits Today:**")
        for t in trackers:
            emoji = t.get("emoji", "📊")
            name = t["name"].capitalize()
            lines.append(f"• Try logging {name} today: just reply 'track {t['name']} [value]'!")

    # 2. Checklist items left
    if pending:
        lines.append(f"\n📋 **Your Pending Checklist ({len(pending)} items):**")
        for t in pending[:5]:
            lines.append(f"• {t['title']}")
    else:
        lines.append("\n✅ Your checklist is empty! Say 'I need to [task]' to add a task anytime.")

    return lines


def get_upcoming_bureaucratic_deadlines(user_id: int) -> list[str]:
    """Retrieves upcoming administrative or visa-related milestones based on arrival date."""
    user = get_user(user_id)
    if not user or not user.get("arrival_date"):
        return ["⚠️ Staged: Set your arrival date via '/setarrival YYYY-MM-DD' to unlock visa/milestone trackers."]

    arrival_str = user["arrival_date"]
    from predictor import days_since_arrival
    days = days_since_arrival(arrival_str)
    if days is None:
        return []

    deadlines = []
    # Major milestone windows (ARC at Day 30-90, Health insurance at Day 180, Visa extension at Day 330)
    if days < 90:
        remaining = 90 - days
        deadlines.append(f"🏛️ **Alien Registration Card (ARC):** Due in {remaining} days (Must be completed within 90 days of arrival!).")
    if days < 180:
        remaining = 180 - days
        deadlines.append(f"🏥 **National Health Insurance (NHIS):** Due in {remaining} days (Automatic enrollment at 6-month mark).")
    if days < 365:
        remaining = 365 - days
        deadlines.append(f"📡 **Visa Extension window:** In {remaining} days.")

    return deadlines


def conduct_evening_review(user_id: int) -> str:
    """Conducts a smart evening check-in reviewing completed/incomplete tasks."""
    tasks = get_tasks(user_id)
    completed = [t for t in tasks if t.get("done")]
    pending = [t for t in tasks if not t.get("done")]

    msg = "🌙 **Your Evening Life Review & Audit**\n\n"
    if completed:
        msg += "🎉 **Completed Today:**\n" + "\n".join(f"  ✓ {t['title']}" for t in completed) + "\n\n"
    if pending:
        msg += "📋 **Remaining for Tomorrow:**\n" + "\n".join(f"  • {t['title']}" for t in pending) + "\n\n"
        msg += "💡 Reply 'done with [task_name]' to cross off completed items before sleeping!"
    else:
        msg += "🌟 Amazing job! Every single checklist item has been crossed off! Perfect day. 👏"

    return msg


def schedule_staggered_reminder(user_id: int, task_title: str, target_time: datetime):
    """Schedules staggered reminders: 1 hour before, 15 minutes before, and on-time."""
    from notifier import add_custom_reminder
    now = datetime.now(UTC)

    # 1. On-Time Reminder
    if target_time > now:
        add_custom_reminder(user_id, task_title, target_time)

    # 2. 15-Minute Pre-alert
    pre15 = target_time - timedelta(minutes=15)
    if pre15 > now:
        add_custom_reminder(user_id, f"⚠️ '{task_title}' starts in 15 minutes!", pre15)

    # 3. 1-Hour Pre-alert
    pre60 = target_time - timedelta(hours=1)
    if pre60 > now:
        add_custom_reminder(user_id, f"⏰ Upcoming in 1 hour: '{task_title}'", pre60)

    logger.info(f"Scheduled staggered pre-reminders for user {user_id}: '{task_title}' at {target_time}")


def build_life_dashboard_card(user_id: int) -> str:
    """Consolidates today's agenda, tracker summaries, and deadlines into a stunning dashboard."""
    user = get_user(user_id)
    name = user.get("first_name", "friend") if user else "friend"

    dash = f"🧠 **Life Manager Dashboard — {name}** 🚀\n"
    dash += "═" * 32 + "\n"

    # 1. Agenda and Checklist
    tasks = get_tasks(user_id)
    pending = [t for t in tasks if not t.get("done")]
    if pending:
        dash += f"\n📋 **Checklist Progress ({len(pending)} left):**\n"
        for t in pending[:4]:
            dash += f"  • {t['title']}\n"
    else:
        dash += "\n✅ **Checklist is clear!** Say 'I need to...' to add items.\n"

    # 2. Habit Trackers & Financials
    trackers = get_user_trackers(user_id)
    if trackers:
        dash += "\n📊 **Your Active Trackers:**\n"
        for t in trackers[:4]:
            val = get_yesterday_total(user_id, t["id"])
            m_val = get_month_total(user_id, t["id"])
            unit = t.get("unit", "")
            dash += f"  {t.get('emoji', '📊')} {t['name'].capitalize()}: yesterday {val:,.0f} {unit} | month {m_val:,.0f} {unit}\n"

    # 3. Bureaucratic Deadlines
    deadlines = get_upcoming_bureaucratic_deadlines(user_id)
    if deadlines:
        dash += "\n🏛️ **Administrative Countdown:**\n"
        for d in deadlines[:2]:
            dash += f"  {d}\n"

    dash += "\n💡 *Control naturally! Try say 'I need to study' or 'track sleep 8 hours' to manage your life.*"
    return dash
