# schedule_maker.py — K-Transition OS v3.0
# Personalised arrival schedules. Tasks are ordered by dependency (ARC before bank, etc.)
# Weeks 2-4 added (Bug 8 fix).

import logging
logger = logging.getLogger(__name__)

FIRST_WEEK_TASKS = [
    {
        "id": "task_sim", "day": 1,
        "title": "Get a SIM Card 📱",
        "description": "Get a Korean phone number FIRST — you need it for almost everything else.",
        "steps": [
            "Go to airport convenience store (CU/GS25) or carrier booth (SK Telecom/KT/LG U+)",
            "Show your passport",
            "Buy a prepaid SIM (~30,000-50,000 won/month) or sign up for a plan",
            "Write down your new Korean number somewhere safe",
        ],
        "cost": "~30,000-50,000 won/month", "time_needed": "30 minutes",
        "why_first": "Korean number needed for: government apps, bank SMS, ARC appointment booking",
    },
    {
        "id": "task_tmoney", "day": 1,
        "title": "Get a T-Money Card 🚇",
        "description": "Use buses and subways cheaply — no T-Money = higher fares, no free transfers.",
        "steps": [
            "Any CU, GS25, or 7-Eleven — ask for 티머니 카드 (4,000 won)",
            "Charge at least 20,000 won at the counter or subway machine",
        ],
        "cost": "4,000 won + charge", "time_needed": "10 minutes",
        "why_first": "Without T-Money you pay cash fares (more expensive) and lose free transfers",
    },
    {
        "id": "task_apps", "day": 1,
        "title": "Download Essential Apps 📲",
        "description": "These replace Google Maps, Google Translate, WhatsApp, and Amazon in Korea.",
        "steps": [
            "Naver Maps (네이버 지도) — best navigation in Korea",
            "Kakao Map — better real-time bus info",
            "Naver Papago — best Korean translator, has camera mode",
            "KakaoTalk — everyone uses this for messaging",
            "Coupang — online shopping (next-day delivery)",
            "Baemin or Coupang Eats — food delivery",
        ],
        "cost": "Free", "time_needed": "20 minutes",
        "why_first": "You'll use these 20+ times a day starting from Day 1",
    },
    {
        "id": "task_arc_appt", "day": 2,
        "title": "Book ARC Appointment 🪪",
        "description": "URGENT: Immigration slots fill up weeks in advance. Book today.",
        "steps": [
            "Go to HiKorea.go.kr and register with your passport",
            "Book appointment at your nearest 출입국관리소 (immigration office)",
            "Select: 외국인등록 (Foreigner Registration)",
            "Prepare: passport + enrollment cert + 2 passport photos + 30,000 won",
        ],
        "cost": "30,000 won at appointment", "time_needed": "30 mins online; 1-3 hrs at office",
        "why_first": "Must register within 90 days. ARC unlocks: bank, proper phone plan, rent, NHIS",
    },
    {
        "id": "task_campus", "day": 2,
        "title": "Explore Campus 🏫",
        "description": "Find the key buildings before classes start — saves so much confusion.",
        "steps": [
            "International student office (국제처) — register here FIRST, get your student ID",
            "Student counseling center (학생상담센터) — free mental health support",
            "University library — study spaces, printing, lockers",
            "Campus cafeteria (학생식당) — cheapest food near campus (3,000-5,000 won/meal)",
            "Campus bank branch — most foreigner-friendly for opening accounts",
        ],
        "cost": "Free", "time_needed": "2-3 hours",
        "why_first": "International office can help with housing, visa questions, and cultural adjustment",
    },
    {
        "id": "task_bank", "day": 3,
        "title": "Open a Bank Account 🏦",
        "description": "You need a Korean bank account for scholarship money and daily expenses.",
        "steps": [
            "Option A (easiest): Kakao Bank — 100% mobile, no branch needed. Korean number + passport.",
            "Option B: Shinhan Bank — good English, branches near most universities",
            "Option C: KB Kookmin — most ATMs in Korea",
            "Some banks need ARC; some accept passport + enrollment cert for new arrivals — call ahead",
        ],
        "cost": "Free to open", "time_needed": "30 mins – 2 hours",
        "why_first": "You need this to receive scholarship, pay rent, and use Korean payment apps",
    },
    {
        "id": "task_jumin", "day": 7,
        "title": "Register at 주민센터 📋",
        "description": "Required by law within 14 days of moving in. Protects your deposit legally.",
        "steps": [
            "Find nearest 주민센터 on Naver Maps",
            "Bring: passport, ARC, signed lease contract",
            "Request 전입신고 (free) AND 확정일자 (600 won)",
            "Can also be done online at government24.go.kr",
        ],
        "cost": "600 won", "time_needed": "1 hour",
        "why_first": "Without 확정일자 you have ZERO legal protection for your housing deposit",
    },
    {
        "id": "task_grocery", "day": 2,
        "title": "Find Affordable Food Sources 🛒",
        "description": "Know your cheapest options within walking distance.",
        "steps": [
            "Large supermarkets: Emart / Homeplus / Lotte Mart — best prices",
            "Convenience stores: CU/GS25/7-Eleven — expensive but 24/7",
            "다이소 (Daiso) — household items 1,000-5,000 won",
            "Coupang (online) — same day or next day delivery",
            "분식집 near uni — meals from 3,500-5,000 won",
        ],
        "cost": "Varies", "time_needed": "1 hour to explore",
        "why_first": "Finding cheap food sources in week 1 saves you thousands of won per month",
    },
    {
        "id": "task_friends", "day": 3,
        "title": "Build Your Community 👥",
        "description": "Loneliness is the #1 issue for new international students. Start early.",
        "steps": [
            "Check for international student orientation at your university",
            "Search Facebook: '[your university] international students'",
            "Find the Kakao open chat group for your uni",
            "Language exchange: university board or HelloTalk app",
            "Knock on your dormitory neighbours' doors and introduce yourself",
        ],
        "cost": "Free", "time_needed": "Ongoing",
        "why_first": "Studies show social connection is the biggest predictor of adjustment success",
    },
]

WEEK2_TASKS = [
    {"id": "w2_arc_collect", "day": "~Day 14", "title": "Collect Your ARC Card 🪪",
     "steps": ["Check HiKorea.go.kr for processing status",
               "Return to immigration office with passport when notified",
               "Keep ARC with you at all times — it's your main ID in Korea"],
     "cost": "Free (already paid)", "time_needed": "1 hour"},
    {"id": "w2_phone_plan", "day": "Day 14+", "title": "Upgrade Phone Plan (with ARC) 📱",
     "steps": ["With ARC you can get a proper monthly plan instead of prepaid",
               "Student plans: 20,000-30,000 won/month for unlimited calls + 10GB+",
               "알뜰폰 (MVNO) options: HelloMobile, LycaMobile — cheapest rates"],
     "cost": "20,000-50,000 won/month", "time_needed": "30 minutes"},
    {"id": "w2_neighborhood", "day": "Day 8-10", "title": "Map Your Neighborhood 🗺️",
     "steps": ["Find nearest pharmacy (약국) — you'll need it",
               "Find nearest 주민센터 (if you haven't gone yet)",
               "Find laundromat (세탁소) or check if your building has machines",
               "Find closest GS25/CU for late-night needs"],
     "cost": "Free", "time_needed": "1-2 hours"},
    {"id": "w2_orientation", "day": "Day 8-14", "title": "Attend University Orientation 🎓",
     "steps": ["International student orientation — meet fellow foreign students",
               "Campus tour from student services",
               "Academic registration help session",
               "Mental health and counselling introduction"],
     "cost": "Free", "time_needed": "Half day"},
]

WEEK3_TASKS = [
    {"id": "w3_classes", "day": "Week 3", "title": "Start Classes — Navigate Campus 📚",
     "steps": ["Find all classroom buildings before first day",
               "Add professors' KakaoTalk or email to contacts",
               "Join the class group chat (카카오톡 오픈채팅)"],
     "cost": "Free", "time_needed": "Ongoing"},
    {"id": "w3_clubs", "day": "Week 3", "title": "Join a Club or Language Exchange 🎭",
     "steps": ["Korean universities have 동아리 (clubs) for almost everything",
               "Language exchange (언어교환): meet Korean students who want to practice English",
               "International student club — social events, trips",
               "Search your uni website for 동아리 가입 (club registration)"],
     "cost": "Free or small membership", "time_needed": "2-3 hours"},
    {"id": "w3_insurance", "day": "Week 3", "title": "Check Health Insurance Status 🏥",
     "steps": ["NHIS (국민건강보험): auto-enrolls after 6 months of continuous stay",
               "Ask your university if they offer supplemental insurance for the first 6 months",
               "Without NHIS: use university clinic (cheapest) for minor illness",
               "Emergency: 응급실 accepts anyone — settle payment later"],
     "cost": "~30,000-40,000 won/month once enrolled", "time_needed": "1 hour"},
    {"id": "w3_korean", "day": "Week 3", "title": "Establish a Korean Learning Routine 🇰🇷",
     "steps": ["/word every morning for word of the day",
               "/quiz every evening — AI-generated, adapts to your level",
               "Talk To Me In Korean (TTMIK) YouTube for 15 mins/day",
               "Try ordering food in Korean at least once this week"],
     "cost": "Free", "time_needed": "15-30 min/day"},
]

WEEK4_TASKS = [
    {"id": "w4_explore", "day": "Week 4", "title": "Explore Beyond Campus 🏙️",
     "steps": ["Visit main commercial area of your city",
               "Try a Korean market (시장) — amazing food and cheap prices",
               "찜질방 (jjimjilbang / Korean sauna) — unique cultural experience, ~10,000 won",
               "Try ordering from Baemin/Coupang Eats for food delivery practice"],
     "cost": "Varies", "time_needed": "Weekend"},
    {"id": "w4_friends", "day": "Week 4", "title": "Make Your First Korean Friend 🤝",
     "steps": ["Language exchange is the easiest way — you help them with English, they help with Korean",
               "Study café (스터디카페) — people are open to talking",
               "Find a church/mosque/temple community near you if relevant",
               "말 걸기 (starting conversation): just say 안녕하세요, 저 [country]에서 왔어요"],
     "cost": "Free", "time_needed": "Ongoing"},
    {"id": "w4_checkin", "day": "Day 28", "title": "One-Month Check-In ✅",
     "steps": ["Review what tasks from weeks 1-3 are still undone",
               "Visit international student office — any issues or questions to raise?",
               "How are you feeling? If still very lonely or struggling: counseling center",
               "Celebrate — surviving your first month in a new country is genuinely hard work"],
     "cost": "Free", "time_needed": "2 hours"},
]


def get_first_week_checklist(user_info: dict = None) -> str:
    user_info = user_info or {}
    diet = user_info.get("diet", "none")

    msg  = "📅 First Week in Korea — Checklist\n\n"
    msg += "Complete these IN ORDER — some depend on earlier ones!\n\n"

    for task in FIRST_WEEK_TASKS:
        msg += f"Day {task['day']}: {task['title']}\n"
        msg += f"  ⏱ {task['time_needed']}  |  💰 {task['cost']}\n"
        msg += f"  {task['description']}\n\n"

    if diet == "halal":
        msg += "\n🕌 Halal note: Add to Day 1-2 — find nearest halal restaurant on HalalKorea.com\n"

    msg += "\n/schedule week2  /schedule week3  /schedule week4  for later weeks\n"
    msg += "/schedule ai  for AI-personalised schedule\n"
    msg += "/month  for full first-month overview"
    return msg


def get_week_tasks(week: int) -> str:
    mapping = {2: WEEK2_TASKS, 3: WEEK3_TASKS, 4: WEEK4_TASKS}
    tasks = mapping.get(week)
    if not tasks:
        return "Use /schedule week2, week3, or week4"

    msg = f"📅 Week {week} Tasks\n\n"
    for task in tasks:
        msg += f"{task['day']}: {task['title']}\n"
        for step in task["steps"]:
            msg += f"  • {step}\n"
        msg += f"  ⏱ {task['time_needed']}  |  💰 {task['cost']}\n\n"
    return msg.strip()


def get_task_detail(task_id: str) -> str | None:
    all_tasks = FIRST_WEEK_TASKS + WEEK2_TASKS + WEEK3_TASKS + WEEK4_TASKS
    for task in all_tasks:
        if task["id"] == task_id or task["title"].lower().startswith(task_id.lower()):
            msg  = f"{task['title']}\n\n"
            msg += f"{task.get('description', '')}\n\nSteps:\n"
            for i, step in enumerate(task.get("steps", []), 1):
                msg += f"{i}. {step}\n"
            msg += f"\n⏱ {task['time_needed']}\n💰 {task['cost']}"
            if task.get("why_first"):
                msg += f"\n\nWhy now: {task['why_first']}"
            return msg
    return None


async def generate_ai_schedule(user_info: dict) -> str:
    uni     = user_info.get("university", "your university")
    city    = user_info.get("city", "Seoul")
    diet    = user_info.get("diet", "none")
    arrival = user_info.get("arrival_date", "recently")

    prompt = f"""Create a practical day-by-day schedule for my FIRST WEEK in South Korea.

My details:
- University: {uni}
- City: {city}
- Diet: {diet}
- Arrived: {arrival}

Give me:
1. What to do each day (Day 1-7) in morning/afternoon/evening
2. Specific places with how to find them
3. Estimated costs
4. Korean phrases I'll need each day
5. What to prioritise if short on time

Be practical and specific to {city}."""

    from ai_brain import ask_ai_async
    response, _ = await ask_ai_async(prompt)
    return response or "Could not generate schedule right now. Use /schedule for the standard checklist."


def get_month_overview() -> str:
    return """📆 First Month — Overview

━━ WEEK 1: Survival Mode ━━
✅ SIM card, T-Money, essential apps
✅ Book ARC appointment (ASAP!)
✅ Open bank account
✅ Register at 주민센터
✅ Find campus basics, meet other students

━━ WEEK 2: Settle In ━━
✅ Collect ARC card
✅ Upgrade phone plan (needs ARC)
✅ Map your neighborhood (pharmacy, laundromat)
✅ Attend university orientation

━━ WEEK 3: Build Routine ━━
✅ Start classes — find all buildings
✅ Join a club or language exchange
✅ Check health insurance status
✅ Daily Korean practice routine

━━ WEEK 4: Explore ━━
✅ Explore beyond campus
✅ Make your first Korean friend
✅ One-month check-in

💡 Weeks 2-3 are the hardest for most students. It gets better.
Type /help or just describe what you're struggling with — I'm here 24/7."""
