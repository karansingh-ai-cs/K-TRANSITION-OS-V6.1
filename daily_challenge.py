# daily_challenge.py — K-Transition OS v5.0
# Gamified daily challenges that make users come back every day
# Streak system + XP rewards + adaptive difficulty

import random
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

# Challenges organized by category — rotates daily
DAILY_CHALLENGES = [
    # Korean Language Challenges
    {"id": "kr_order", "title": "🇰🇷 Order in Korean", "task": "Order your next meal entirely in Korean. Even just '이거 주세요' (this one please) counts!", "xp": 30, "category": "korean", "difficulty": 1},
    {"id": "kr_greet", "title": "🇰🇷 Greet 3 People", "task": "Say 안녕하세요 to 3 different people today — security guard, convenience store staff, anyone!", "xp": 20, "category": "korean", "difficulty": 1},
    {"id": "kr_read", "title": "🇰🇷 Read 5 Signs", "task": "Read 5 Korean signs around you using Hangeul. Take a screenshot of one and send it to me!", "xp": 25, "category": "korean", "difficulty": 1},
    {"id": "kr_count", "title": "🇰🇷 Count to 10", "task": "Practice counting 1-10 in both Korean number systems: 하나둘셋 AND 일이삼. Say them out loud!", "xp": 20, "category": "korean", "difficulty": 1},
    {"id": "kr_convo", "title": "🇰🇷 5-Minute Korean Chat", "task": "Have a 5-minute conversation with a Korean person. Use Papago if stuck. The attempt is what matters!", "xp": 50, "category": "korean", "difficulty": 2},

    # Survival Challenges
    {"id": "sv_cu", "title": "🏪 CU Explorer", "task": "Go to CU/GS25 and find 3 items you've never tried before. Try the cheapest one!", "xp": 25, "category": "survival", "difficulty": 1},
    {"id": "sv_daiso", "title": "🛍️ Daiso Hunt", "task": "Visit Daiso and find something useful under ₩2,000 that you didn't know existed!", "xp": 20, "category": "survival", "difficulty": 1},
    {"id": "sv_subway", "title": "🚇 Subway Master", "task": "Take a subway ride to a station you've never been to. Explore for 15 minutes!", "xp": 35, "category": "survival", "difficulty": 1},
    {"id": "sv_cafeteria", "title": "🍽️ Cafeteria Challenge", "task": "Eat at your university cafeteria (학생식당) today. Report what you got and how much it cost!", "xp": 20, "category": "survival", "difficulty": 1},
    {"id": "sv_cook", "title": "🧑‍🍳 Dorm Chef Challenge", "task": "Make a meal in your dorm using only convenience store ingredients. Use /cook for ideas!", "xp": 40, "category": "survival", "difficulty": 2},

    # Cultural Challenges
    {"id": "cu_bow", "title": "🙇 Master the Bow", "task": "Practice 3 types of Korean bows: 15° (casual), 30° (respectful), 45° (deep respect). Use them today!", "xp": 25, "category": "culture", "difficulty": 1},
    {"id": "cu_photo", "title": "📸 Korea Snapshot", "task": "Take a photo of something uniquely Korean that surprised you. Describe it!", "xp": 20, "category": "culture", "difficulty": 1},
    {"id": "cu_cafe", "title": "☕ Café Culture", "task": "Visit a Korean study café (스터디카페) for 1 hour. Report how it compares to regular cafés!", "xp": 30, "category": "culture", "difficulty": 1},
    {"id": "cu_trash", "title": "🗑️ Trash Master", "task": "Sort your trash correctly today using the Korean recycling system. 분리수거 = sorted recycling!", "xp": 25, "category": "culture", "difficulty": 1},
    {"id": "cu_friend", "title": "🤝 Make a Connection", "task": "Join one university club/동아리 meeting OR attend a language exchange event. Just showing up counts!", "xp": 50, "category": "culture", "difficulty": 2},

    # Budget Challenges
    {"id": "bu_5000", "title": "💰 ₩5,000 Day", "task": "Survive today spending only ₩5,000 total on food. Track every won!", "xp": 40, "category": "budget", "difficulty": 2},
    {"id": "bu_free", "title": "🆓 Free Day", "task": "Find 3 free things to do in your city today. Parks, campus events, free museum days...", "xp": 30, "category": "budget", "difficulty": 1},
    {"id": "bu_compare", "title": "📊 Price Detective", "task": "Compare prices of the same item at CU, GS25, and Emart24. Report which is cheapest!", "xp": 25, "category": "budget", "difficulty": 1},

    # Social Challenges
    {"id": "so_thank", "title": "🙏 Thank You Chain", "task": "Say 감사합니다 (thank you) to 5 different people today with a genuine bow. Watch their reaction!", "xp": 25, "category": "social", "difficulty": 1},
    {"id": "so_help", "title": "🤗 Help Someone", "task": "Help a fellow student with something today. Directions, carrying bags, explaining something.", "xp": 35, "category": "social", "difficulty": 1},
]


def get_todays_challenge(user_id=None):
    """Get today's challenge — deterministic per day so all users get the same one."""
    day_num = date.today().toordinal()
    idx = day_num % len(DAILY_CHALLENGES)
    return DAILY_CHALLENGES[idx]


def format_challenge(challenge, streak=0, completed=False):
    """Format challenge for display."""
    if completed:
        return (
            f"✅ Today's Challenge — COMPLETED!\n\n"
            f"{challenge['title']}\n"
            f"+{challenge['xp']} XP earned! 🎉\n\n"
            f"🔥 Streak: {streak} day{'s' if streak != 1 else ''}\n\n"
            f"Come back tomorrow for a new challenge!"
        )

    msg = f"🎯 Today's Challenge\n\n"
    msg += f"{challenge['title']}\n\n"
    msg += f"📋 {challenge['task']}\n\n"
    msg += f"🏆 Reward: +{challenge['xp']} XP\n"
    msg += f"⭐ Difficulty: {'⭐' * challenge['difficulty']}\n"
    if streak > 0:
        msg += f"🔥 Current streak: {streak} day{'s' if streak != 1 else ''}\n"
    msg += f"\nComplete it and type /challenge done!"
    return msg


def get_challenge_stats_text(streak, total_completed, total_xp):
    """Format challenge statistics."""
    msg = f"📊 Your Challenge Stats\n\n"
    msg += f"🔥 Current Streak: {streak} days\n"
    msg += f"✅ Total Completed: {total_completed}\n"
    msg += f"⭐ Total XP from Challenges: {total_xp}\n\n"

    # Motivational messages based on streak
    if streak == 0:
        msg += "Start your first challenge today! /challenge"
    elif streak < 3:
        msg += "Great start! Keep going to build momentum!"
    elif streak < 7:
        msg += "You're on fire! 🔥 One week streak incoming!"
    elif streak < 14:
        msg += "Incredible dedication! You're truly adapting to Korea! 🇰🇷"
    elif streak < 30:
        msg += "선배 level! You're becoming a Korea survival master! 🏆"
    else:
        msg += "한국 마스터! 🎌 You ARE Korea now. Absolute legend."

    return msg
