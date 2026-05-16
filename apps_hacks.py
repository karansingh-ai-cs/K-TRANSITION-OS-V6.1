# apps_hacks.py — K-Transition OS v5.0
# Essential Korean apps + life hacks — AI-powered tips
# Not generic — specific to international students

import asyncio
import logging

logger = logging.getLogger(__name__)

ESSENTIAL_APPS = {
    "communication": {
        "title": "💬 Communication",
        "apps": [
            {"name": "KakaoTalk (카카오톡)", "why": "Korea's #1 messaging. Everyone uses it. No KakaoTalk = no social life.", "tip": "Add Korean friends by phone number. Enable 'Kakao Pay' for easy money transfers."},
            {"name": "Papago (파파고)", "why": "Naver's translator. WAY better than Google Translate for Korean.", "tip": "Use the camera mode to translate menus/signs in real-time!"},
        ]
    },
    "transport": {
        "title": "🚇 Transport",
        "apps": [
            {"name": "Kakao Map (카카오맵)", "why": "Best for navigation, bus times, subway routes. Google Maps doesn't work properly in Korea.", "tip": "Save your dorm as 'home' and university as 'work' for quick routing."},
            {"name": "Kakao T (카카오 T)", "why": "Uber doesn't exist in Korea. This is the taxi app. Also for bike/scooter rental.", "tip": "Set destination BEFORE the driver arrives. Shows fare estimate."},
            {"name": "Naver Map", "why": "Best for finding restaurants, stores, reviews. More detailed business info than Kakao.", "tip": "Check 블로그 reviews — Koreans write DETAILED food reviews."},
        ]
    },
    "food_delivery": {
        "title": "🍕 Food & Delivery",
        "apps": [
            {"name": "Coupang Eats (쿠팡이츠)", "why": "Food delivery. Often has new user discounts. Wide selection.", "tip": "Sign up for Coupang Rocket WOW (₩4,990/month) for free delivery on everything."},
            {"name": "배달의민족 (Baedal Minjok)", "why": "Korea's biggest delivery app. More restaurants than Coupang Eats.", "tip": "Use '1인분' filter to find places that deliver single portions (many require min 2)."},
            {"name": "Yogiyo (요기요)", "why": "Another delivery option. Sometimes has different restaurants/deals.", "tip": "Compare prices between all 3 delivery apps — same restaurant, different prices."},
        ]
    },
    "shopping": {
        "title": "🛍️ Shopping",
        "apps": [
            {"name": "Coupang (쿠팡)", "why": "Korea's Amazon. Next-day delivery, sometimes same-day. Everything is here.", "tip": "쿠팡 로켓배송 = arrives by 6AM next day if ordered before midnight. Life-changing."},
            {"name": "당근마켓 (Danggeun Market)", "why": "Like Facebook Marketplace but BETTER. Buy/sell used stuff locally.", "tip": "Get dorm furniture, kitchen stuff, textbooks for 50-80% off."},
        ]
    },
    "banking": {
        "title": "🏦 Banking & Payment",
        "apps": [
            {"name": "Kakao Bank (카카오뱅크)", "why": "Easiest bank to open. Fully mobile. No branch visit needed.", "tip": "Can open with just passport + Korean phone number. Transfer fees are lowest."},
            {"name": "Toss (토스)", "why": "Send/receive money instantly. Also shows all your bank accounts in one place.", "tip": "Free money transfers between any Korean bank. Also has investment features."},
        ]
    },
    "student_life": {
        "title": "🎓 Student Life",
        "apps": [
            {"name": "에브리타임 (Everytime)", "why": "University community app. Class reviews, timetable maker, anonymous forums.", "tip": "Check professor ratings before choosing classes. 'A+' is the Korean grading."},
            {"name": "ZZAN (짠)", "why": "Student discount app. Shows deals near your university.", "tip": "Show student ID at many cafes/restaurants for 10-20% off even without the app."},
        ]
    },
}

LIFE_HACKS = {
    "cheap_food": [
        "🍚 University cafeteria (학생식당) = ₩3,000-5,000 for a full meal. ALWAYS eat here.",
        "🏪 CU/GS25 1+1 deals change weekly — check the app for current BOGO offers",
        "🍜 Buy 2 삼각김밥 (triangle kimbap) + 1 cup noodle = filling meal under ₩4,000",
        "📱 Use 배민 coupons — first-time user gets ₩5,000-10,000 off",
        "🥡 쿠팡이츠 has 'mystery box' deals from restaurants closing — 50-70% off",
        "🕐 Convenience store 유통기한 (near-expiry) items get 30-50% off after 9 PM",
    ],
    "save_money": [
        "💳 Get a 체크카드 (debit card) instead of credit — helps control spending",
        "🚇 Buy 정기권 (monthly subway pass) if commuting daily — saves 30%+",
        "📱 알뜰폰 (budget phone plans) like 여유모바일 = same network, half the price",
        "🏪 Daiso (다이소) for ALL household items — ₩1,000-5,000 range",
        "📦 Coupang 로켓와우 membership = free shipping on everything for ₩4,990/month",
        "🎓 Flash your student ID EVERYWHERE — many places give 10-20% student discount",
    ],
    "transport": [
        "🚇 Subway Line 1 = cheapest way to travel between cities (e.g., Seoul↔Incheon)",
        "🚌 Express bus (고속버스) tickets on 코버스 app — book early for window seats",
        "✈️ Domestic flights on 제주항공/진에어 can be ₩30,000 if booked early",
        "🚲 따릉이 (Seoul public bike) = ₩1,000/hour. App: '서울자전거 따릉이'",
        "🚶 Korea is VERY walkable — most errands within 15 min walk in university areas",
        "📱 Kakao T taxi sharing (합승) between friends splits fare automatically",
    ],
    "laundry": [
        "👔 Most dorms have coin laundry (₩1,000-2,000 per load)",
        "🧴 Buy detergent pods (세탁 캡슐) from Daiso — ₩1,000 for a pack",
        "☔ Indoor drying racks (빨래건조대) from Daiso — essential for rainy season",
        "👕 Korean dry cleaning is CHEAP — ₩3,000-5,000 for a coat",
        "🌧️ Humidity in summer = clothes take 2-3 days to dry. Get a small dehumidifier.",
    ],
}

HACK_SYSTEM = """You are a Korea life hack expert for K-Transition OS. The user is asking about: {topic}
User is a student at {university} in {city}.

Give 5-7 SPECIFIC, non-obvious life hacks. Not generic advice — things only someone living in Korea would know.
Include Korean terms with translations. Be casual and fun.
Format each hack with an emoji and keep it concise."""


def get_apps_list(category=None):
    """Get formatted app list."""
    if category and category in ESSENTIAL_APPS:
        cat = ESSENTIAL_APPS[category]
        msg = f"{cat['title']}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for app in cat["apps"]:
            msg += f"📱 {app['name']}\n"
            msg += f"   Why: {app['why']}\n"
            msg += f"   💡 {app['tip']}\n\n"
        return msg

    msg = "📱 Must-Have Korean Apps\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for key, cat in ESSENTIAL_APPS.items():
        msg += f"{cat['title']}\n"
        for app in cat["apps"]:
            msg += f"  • {app['name']}\n"
        msg += f"  → /apps {key}\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📱 /apps [category] — Detailed app info\n"
    msg += "💡 /hack [topic] — Life hacks"
    return msg


def get_hacks(topic=None):
    """Get life hacks for a topic."""
    if topic and topic in LIFE_HACKS:
        hacks = LIFE_HACKS[topic]
        titles = {"cheap_food": "🍚 Cheap Food Hacks", "save_money": "💰 Save Money Hacks",
                  "transport": "🚇 Transport Hacks", "laundry": "👔 Laundry Hacks"}
        msg = f"{titles.get(topic, '💡 Life Hacks')}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for hack in hacks:
            msg += f"{hack}\n\n"
        return msg

    msg = "💡 Korea Life Hacks\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "/hack cheap_food — Eat well for less\n"
    msg += "/hack save_money — Budget survival tips\n"
    msg += "/hack transport — Getting around smart\n"
    msg += "/hack laundry — Laundry in Korea\n"
    msg += "/hack [anything] — AI generates custom hacks\n\n"
    msg += "Example: /hack dating in korea\n"
    msg += "Example: /hack surviving winter"
    return msg


async def get_ai_hack(topic, user_info=None):
    """AI-generated hacks for any topic."""
    from ai_brain import call_groq
    uni = (user_info or {}).get("university", "a Korean university")
    city = (user_info or {}).get("city", "Korea")
    system = HACK_SYSTEM.format(topic=topic, university=uni, city=city)
    messages = [{"role": "user", "content": f"Give me Korea life hacks about: {topic}"}]
    try:
        resp = await asyncio.to_thread(call_groq, messages, system)
        if resp:
            return f"💡 Korea Hacks: {topic.title()}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{resp}"
    except Exception as e:
        logger.error(f"Hack AI failed: {e}")
    return get_hacks()
