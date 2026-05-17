# maps_helper.py — K-Transition OS v6.0
# Korean-first map engine: ALL Naver/Kakao links use Korean search strings
# Always provides 3 links: Naver + Kakao + Google
# Handles: search, nearby (with city context), directions, transport
# "nearby" queries use [city + Korean place type] NOT "nearby" keyword

import urllib.parse
import re
import logging
import asyncio

logger = logging.getLogger(__name__)

# ── URL Builders ──────────────────────────────────────────────────────────────

def naver_search(query):
    return f"https://m.map.naver.com/search2/search.naver?query={urllib.parse.quote(query)}"

def kakao_search(query):
    return f"https://map.kakao.com/link/search/{urllib.parse.quote(query)}"

def google_search(query):
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query + ' South Korea')}"

def kakao_directions(origin, destination):
    s = urllib.parse.quote(origin)
    e = urllib.parse.quote(destination)
    return f"https://map.kakao.com/?sName={s}&eName={e}"

def google_directions(origin, destination):
    o = urllib.parse.quote(origin + " Korea")
    d = urllib.parse.quote(destination + " Korea")
    return f"https://www.google.com/maps/dir/?api=1&origin={o}&destination={d}"

def naver_directions(origin, destination):
    """Naver directions — search destination, user taps 길찾기."""
    # Naver v5 directions with text names don't work reliably without coordinates
    # Best UX: search destination, instruct user to tap route button
    return naver_search(destination)


# ── Korean Translation Map (expanded) ─────────────────────────────────────────

KOREAN_TERMS = {
    # Food
    "halal": "할랄 식당", "halal restaurant": "할랄 식당", "halal food": "할랄 음식점",
    "restaurant": "음식점", "korean restaurant": "한식당", "chinese restaurant": "중국집",
    "japanese restaurant": "일식집", "indian restaurant": "인도 음식점",
    "vegetarian": "채식 식당", "vegan": "비건 식당",
    "chicken": "치킨집", "pizza": "피자집", "burger": "버거집",
    "cafe": "카페", "coffee": "카페", "bakery": "베이커리",
    # Medical
    "hospital": "병원", "emergency room": "응급실", "pharmacy": "약국",
    "dentist": "치과", "clinic": "의원", "eye doctor": "안과",
    # Finance
    "bank": "은행", "atm": "ATM 현금인출기", "shinhan bank": "신한은행",
    "kb bank": "국민은행", "woori bank": "우리은행",
    "money exchange": "환전소", "currency exchange": "환전소",
    # Shopping
    "convenience store": "편의점", "supermarket": "마트", "emart": "이마트",
    "daiso": "다이소", "grocery": "마트", "market": "시장",
    "shopping mall": "쇼핑몰", "department store": "백화점",
    "olive young": "올리브영",
    # Daily life
    "laundry": "세탁소", "laundromat": "코인 세탁소", "gym": "헬스장",
    "hair salon": "미용실", "barber": "이발소",
    "post office": "우체국", "police station": "경찰서",
    # Education
    "library": "도서관", "study cafe": "스터디카페", "bookstore": "서점",
    # Transport
    "subway station": "지하철역", "bus stop": "버스 정류장",
    "train station": "기차역", "ktx station": "KTX역",
    # Government
    "immigration": "출입국관리소", "community center": "주민센터",
    "city hall": "시청", "district office": "구청",
    # Student life
    "dormitory": "기숙사", "student cafeteria": "학생식당",
    "international office": "국제교류처",
}

IMPORTANT_PLACES = {
    "immigration":       {"name": "Immigration Office (출입국관리소)", "search_kr": "출입국관리소", "description": "Apply for ARC here. Book appointment first at HiKorea.go.kr", "tip": "Bring: passport + enrollment cert + 2 photos + 30,000 won", "lat": 37.5244, "lng": 126.8727},
    "community_center":  {"name": "Community Center (주민센터)", "search_kr": "주민센터", "description": "Register your address within 14 days of moving in", "tip": "Get 전입신고 (free) + 확정일자 (600 won) to protect your deposit", "lat": 0, "lng": 0},
    "shinhan_bank":      {"name": "Shinhan Bank (신한은행)", "search_kr": "신한은행", "description": "Most foreigner-friendly bank with English staff near universities", "tip": "Need ARC + passport. Some branches accept passport + enrollment cert.", "lat": 0, "lng": 0},
    "kb_bank":           {"name": "KB Kookmin Bank (국민은행)", "search_kr": "국민은행", "description": "Most ATM locations in Korea", "tip": "KB App has partial English support", "lat": 0, "lng": 0},
    "hospital":          {"name": "Emergency Room (응급실)", "search_kr": "응급실", "description": "24/7 emergency medical care", "tip": "Say: 영어 통역사 불러주세요 (please call English interpreter)", "lat": 0, "lng": 0},
    "pharmacy":          {"name": "Pharmacy (약국)", "search_kr": "약국", "description": "No prescription needed for basic medicine. Open ~9am-10pm", "tip": "Show symptoms with Papago camera if needed", "lat": 0, "lng": 0},
    "halal_restaurant":  {"name": "Halal Restaurant (할랄 레스토랑)", "search_kr": "할랄 식당", "description": "Certified halal food near you", "tip": "Itaewon (Seoul Line 6) has the most options. Also check HalalKorea.com", "lat": 0, "lng": 0},
    "daiso":             {"name": "Daiso (다이소)", "search_kr": "다이소", "description": "Korean dollar store. Everything 1,000-5,000 won", "tip": "Get bedding, kitchen supplies, hangers, storage boxes here first week", "lat": 0, "lng": 0},
    "emart":             {"name": "Emart Supermarket (이마트)", "search_kr": "이마트", "description": "Large supermarket with best grocery prices", "tip": "Check basement floor for discounted items near closing time", "lat": 0, "lng": 0},
    "police":            {"name": "Police Station (경찰서)", "search_kr": "경찰서", "description": "For non-emergency police matters", "tip": "Emergency: call 112 (faster than going to station)", "lat": 0, "lng": 0},
    "post_office":       {"name": "Post Office (우체국)", "search_kr": "우체국", "description": "Send packages home or within Korea. Also offers banking.", "tip": "우체국 통장 (post office bank account) - foreigners can open without ARC in some locations", "lat": 0, "lng": 0},
}


# ── Direction Pattern Detection ───────────────────────────────────────────────

DIRECTION_PATTERNS = [
    r"from\s+(.+?)\s+to\s+(.+?)(?:\s+(?:by|via|directions?|route|transit|bus|subway))?$",
    r"directions?\s+from\s+(.+?)\s+to\s+(.+?)$",
    r"how\s+(?:do\s+i\s+)?(?:get|go)\s+from\s+(.+?)\s+to\s+(.+?)$",
    r"route\s+from\s+(.+?)\s+to\s+(.+?)$",
    r"(.+?)에서\s+(.+?)까지",
    r"(.+?)\s*→\s*(.+)",
]


def parse_direction_query(text):
    for pattern in DIRECTION_PATTERNS:
        m = re.search(pattern, text.strip(), re.IGNORECASE)
        if m:
            origin = m.group(1).strip()
            dest = m.group(2).strip()
            if len(origin) >= 2 and len(dest) >= 2:
                return origin, dest
    return None, None


def is_nearby_query(text):
    return any(w in text.lower() for w in ["nearby", "near me", "around here", "close to me", "closest", "nearest", "근처", "가까운"])


# ── Korean Query Translation ──────────────────────────────────────────────────

def translate_to_korean(query: str) -> str:
    """Translate a map query to Korean using the lookup table.
    Falls back to original query if no match found.
    """
    q = query.lower().strip()
    # Exact match
    if q in KOREAN_TERMS:
        return KOREAN_TERMS[q]
    # Partial match — find longest matching key
    best_match = None
    best_len = 0
    for eng, kor in KOREAN_TERMS.items():
        if eng in q and len(eng) > best_len:
            best_match = kor
            best_len = len(eng)
    if best_match:
        return best_match
    return query


async def translate_to_korean_ai(query: str) -> str:
    """Use LLM to translate map query to Korean when lookup fails."""
    from ai_brain import call_groq
    prompt = (
        f"Translate this map search query to Korean for Naver Maps. "
        f"Return ONLY the Korean text, nothing else: {query}"
    )
    try:
        result = await asyncio.to_thread(call_groq, [{"role": "user", "content": prompt}])
        if result and len(result.strip()) < 100:
            return result.strip()
    except Exception as e:
        logger.warning("AI map translation failed: %s", e)
    return translate_to_korean(query)


# ── Response Formatters ───────────────────────────────────────────────────────

def _three_links_search(korean_query: str, english_query: str, city: str = "") -> str:
    """Generate all 3 map links for a search query."""
    kr_with_city = f"{city} {korean_query}".strip() if city else korean_query
    en_with_city = f"{english_query} {city}".strip() if city else english_query

    naver = naver_search(kr_with_city)
    kakao = kakao_search(kr_with_city)
    google = google_search(en_with_city)

    return (
        f"🗺️ Naver Maps: {naver}\n"
        f"   (Best for Korea — most accurate results)\n\n"
        f"🗺️ Kakao Maps: {kakao}\n"
        f"   (Best transit info — real-time bus/subway)\n\n"
        f"🗺️ Google Maps: {google}\n"
        f"   (English-friendly — good for walking navigation)\n"
    )


def _three_links_directions(origin: str, destination: str, origin_kr: str = "", dest_kr: str = "") -> str:
    """Generate all 3 map links for directions."""
    # Kakao supports text-based directions
    kakao = kakao_directions(origin_kr or origin, dest_kr or destination)
    google = google_directions(origin, destination)
    # Naver: search destination, user taps 길찾기
    naver = naver_search(dest_kr or destination)

    return (
        f"🗺️ Kakao Maps: {kakao}\n"
        f"   (Tap 🚌 transit icon for real-time bus/subway routes)\n\n"
        f"🗺️ Google Maps: {google}\n"
        f"   (Works well for walking + English directions)\n\n"
        f"🗺️ Naver Maps: {naver}\n"
        f"   (Search result → tap '길찾기' button for route)\n\n"
        f"🚇 Smarter Subway Apps (Best for transit):\n"
        f"   • Subway Korea: Android / iOS\n"
        f"   • KakaoMetro: Android / iOS\n"
    )


def format_map_response(query: str, user_city: str = "", korean_override: str = None):
    """Main entry: generates map response with all 3 links.
    korean_override comes from the LLM intent router.
    """
    # 1. Check directions
    origin, dest = parse_direction_query(query)
    if origin and dest:
        origin_kr = translate_to_korean(origin)
        dest_kr = translate_to_korean(dest)
        links = _three_links_directions(origin, dest, origin_kr, dest_kr)
        msg = f"📍 Directions: {origin} → {dest}\n\n"
        msg += links
        msg += "\n💡 Tip: Kakao Maps shows real-time subway/bus arrival times"
        return msg

    # 2. Check nearby
    if is_nearby_query(query):
        clean = re.sub(r"\b(nearby|near me|around here|close to me|closest|nearest|근처|가까운)\b", "", query, flags=re.IGNORECASE).strip()
        korean_q = korean_override or translate_to_korean(clean)
        # For nearby: MUST use [city + place type], NOT "nearby" keyword
        links = _three_links_search(korean_q, clean, user_city)
        location = f" in {user_city}" if user_city else ""
        msg = f"📍 Finding: {clean}{location}\n\n"
        msg += links
        if "halal" in query.lower():
            msg += "\n🕌 Also check: https://halalkorea.com for verified halal spots"
        msg += "\n💡 Naver/Kakao show results closest to the city center. Open the app for GPS-based results."
        return msg

    # 3. General search
    korean_q = korean_override or translate_to_korean(query)
    links = _three_links_search(korean_q, query, user_city)
    msg = f"📍 Searching: {query}"
    if user_city:
        msg += f" in {user_city}"
    msg += f"\n\n{links}"
    msg += "\n💡 Korean search terms give much more accurate results on Naver/Kakao"
    return msg


def format_place_info(place_key: str, user_city: str = ""):
    """Format a known important place with all 3 links. Returns a tuple of (text, venue_dict)."""
    if place_key not in IMPORTANT_PLACES:
        return None, None
    place = IMPORTANT_PLACES[place_key]
    kr_query = place["search_kr"]
    if user_city:
        kr_query = f"{user_city} {kr_query}"

    naver = naver_search(kr_query)
    kakao = kakao_search(kr_query)
    google = google_search(f"{place['name']} {user_city}".strip())

    msg = f"📍 {place['name']}\n\n"
    msg += f"{place['description']}\n\n"
    msg += f"🗺️ Naver Maps: {naver}\n"
    msg += f"🗺️ Kakao Maps: {kakao}\n"
    msg += f"🗺️ Google Maps: {google}\n\n"
    msg += f"💡 {place['tip']}"
    
    venue = None
    if place.get("lat") and place.get("lng") and place["lat"] != 0:
        venue = {
            "lat": place["lat"],
            "lng": place["lng"],
            "title": place["name"],
            "address": place["description"]
        }
        
    return msg, venue


def get_area_guide(city):
    guides = {
        "seoul":    "Seoul student areas:\nHongdae (홍대): Line 2. International food, cafes, nightlife.\nItaewon (이태원): Line 6. Most halal options, diverse international community.\nSinchon (신촌): Near Yonsei/Ewha unis. Cheap food everywhere.\nSillim (신림): Very affordable, many study cafes.\n\nTip: 학교 앞 (in front of school) always has cheapest food.",
        "busan":    "Busan student areas:\nSeomyeon (서면): Main commercial area. Food, banks, shopping.\nHaeundae (해운대): Beautiful beach area, slightly expensive.\nPNU area (부산대): Classic student district, cheap food. Line 1.\n\nTip: Amazing seafood at affordable prices near Jagalchi market.",
        "daejeon":  "Daejeon student areas:\nDunsan (둔산): Main commercial district. Banks, hospitals, malls.\nDaedeok (대덕): Near KAIST. Science/student focused.\nAffordable rent: avg 300-400K/month vs Seoul 500-700K.\n\nTip: KAIST international office is very helpful with all paperwork.",
        "daegu":    "Daegu student areas:\nDongseongno (동성로): Main shopping and food street.\nKyungpook Uni area (경북대): Student hotspot, very affordable.\nKeimyung Uni area: Another student district with cheap food.\n\nTip: Daegu gets very hot in summer - buy a portable fan early!",
        "incheon":  "Incheon student areas:\nSongdo (송도): Modern international area. Near INU. Many foreigners.\nBupyeong (부평): Affordable, many students. Lines 1 and 7.\nIncheon → Seoul: 50-70 min by subway (Line 1 or AREX).\n\nTip: Incheon Airport is your area - know which terminal for your airline.",
        "gwangju":  "Gwangju student areas:\nChungjang-ro (충장로): Main commercial and food area.\nJeonnam University area: Student district, cheap food.\nFamous for great food culture and lower prices than Seoul.",
        "jeonju":   "Jeonju student areas:\nHanok Village area: Tourist area, amazing food nearby.\nJeonbuk University area: Main student district.\nFamous for 비빔밥! Best value food city in Korea. 백반 from 5,000 won.",
        "suwon":    "Suwon student areas:\nNear Suwon Station: Shopping, food, banks. Line 1.\nIngye-dong: Near Ajou University, student-friendly.\nSeoul access: 45-60 min by subway. Good balance of cost and access.",
        "cheonan":  "Cheonan student areas:\nSangmun-dong: Near Dankook/Namseoul unis. Affordable student area.\nSinbugwang area: Commercial center with food and shopping.\nSeoul access: 50 min by KTX, 80 min by subway.\n\nTip: Cheonan is one of the most affordable cities for students in central Korea.",
        "ulsan":    "Ulsan student areas:\nSeongnam area: Near UOU. Student-focused district.\nSamsan area: Main commercial center.\nTip: Ulsan is an industrial city but very safe and affordable.",
    }
    city_lower = city.lower().strip()
    for key, guide in guides.items():
        if key in city_lower or city_lower in key:
            return guide
    return f"I don't have a guide for {city} yet. Search '[{city}] 맛집' on YouTube for local food recommendations! Also try: {naver_search(city + ' 자취방')}"


# ── Zero-Click Map Dispatcher — App Guide & Transport Links ───────────────────

APP_GUIDE_MESSAGE = """📱 ESSENTIAL MAP APPS FOR KOREA — Download Guide

Google Maps does NOT work well in Korea! You NEED these Korean map apps.
All apps support ENGLISH — just change language in settings.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗺️ 1. NAVER MAP (네이버 지도) — MUST HAVE
The #1 map app in Korea. Most accurate data.
✅ Walking navigation (better than Google in Korea)
✅ Indoor maps for subway stations & malls
✅ Real-time bus/subway arrival times
✅ English UI available (Settings → Language → English)

📥 Download:
• Android: https://play.google.com/store/apps/details?id=com.nhn.android.nmap
• iPhone: https://apps.apple.com/app/id311867728

💡 How to use in English:
1. Open app → tap ≡ menu → Settings → Language → English
2. Search in English (e.g. "hospital") OR Korean (e.g. "병원")
3. Tap any result → tap "Directions" → choose walk/bus/subway
4. Korean searches give MORE results (use this bot for Korean terms!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗺️ 2. KAKAO MAP (카카오맵) — BEST FOR TRANSIT
Best real-time bus & subway info. Used by all Koreans.
✅ Real-time bus tracking (see exactly where your bus is)
✅ Best subway route calculator
✅ Taxi fare estimates
✅ Partial English support

📥 Download:
• Android: https://play.google.com/store/apps/details?id=net.daum.android.map
• iPhone: https://apps.apple.com/app/id304608425

💡 How to use:
1. Search any place in English or Korean
2. Tap result → "길찾기" (Directions) button
3. Choose 🚌 bus, 🚇 subway, 🚕 taxi, or 🚶 walk
4. Shows real-time arrival + exact cost

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚇 3. SUBWAY KOREA — BEST SUBWAY APP
Dedicated subway-only app. Simplest to use.
✅ Full English support
✅ Route planner with transfer info
✅ Real-time schedule
✅ Fare calculator
✅ Works OFFLINE (no internet needed!)

📥 Download:
• Android: https://play.google.com/store/apps/details?id=com.gameberry.subwayKorea
• iPhone: https://apps.apple.com/app/id325924444

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 GOOGLE MAPS — Use as BACKUP Only
⚠️ Google Maps has LIMITED data in Korea due to government restrictions.
✅ Good for: Walking directions, finding your GPS location
❌ Bad for: Bus routes, subway transfers, Korean businesses
Use Naver or Kakao for anything transit-related.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 BONUS: T-MONEY CARD
Buy a T-money card at ANY convenience store (₩2,500).
Charge it there too. Works on ALL buses, subways, and even some taxis.
Saves ₩100 per transfer vs paying cash!

Type /map [place] to search any location with all 3 map apps!"""


def format_transport_links(origin: str, destination: str, mode: str = "transit") -> str:
    """Generate transit-specific links with app deep links and recommendations."""
    origin_kr = translate_to_korean(origin)
    dest_kr = translate_to_korean(destination)

    # Web fallback links (always work)
    kakao = kakao_directions(origin_kr or origin, dest_kr or destination)
    google = google_directions(origin, destination)
    naver = naver_search(dest_kr or destination)

    msg = f"🚌 Transit: {origin} → {destination}\n\n"

    if mode in ("subway", "metro", "지하철"):
        msg += "🚇 SUBWAY RECOMMENDED\n\n"
        msg += "Best apps for subway:\n"
        msg += "• Subway Korea — tap route, see transfers + time\n"
        msg += "• Kakao Map — real-time subway schedule\n\n"
    elif mode in ("bus", "버스"):
        msg += "🚌 BUS RECOMMENDED\n\n"
        msg += "Best apps for bus:\n"
        msg += "• Kakao Map — see EXACTLY where your bus is in real-time\n"
        msg += "• Naver Map — bus stop locations + walking route to stop\n\n"
    elif mode in ("ktx", "train", "기차", "고속버스"):
        msg += "🚄 TRAIN/KTX RECOMMENDED\n\n"
        msg += "Book KTX tickets:\n"
        msg += "• Let's Korail: https://www.letskorail.com/ebizbf/EbizbfForeign_pr16100.do\n"
        msg += "• SRT: https://etk.srail.kr/main.do\n"
        msg += "• Tip: Book 2+ weeks early for ~40% discount!\n\n"
    else:
        msg += "🗺️ TRANSIT OPTIONS\n\n"

    msg += f"🗺️ Kakao Map (best transit): {kakao}\n"
    msg += f"   → Tap 🚌 icon for real-time bus/subway routes\n\n"
    msg += f"🗺️ Google Maps: {google}\n"
    msg += f"   → Good for walking directions\n\n"
    msg += f"🗺️ Naver Map: {naver}\n"
    msg += f"   → Search → tap '길찾기' for route\n\n"
    msg += "💡 Don't have the apps yet? Type /map guide to download them!"

    return msg


def format_map_guide():
    """Return the full app download + usage guide."""
    return APP_GUIDE_MESSAGE

