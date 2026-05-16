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
    return f"https://map.naver.com/v5/search/{urllib.parse.quote(query)}"

def kakao_search(query):
    return f"https://map.kakao.com/?q={urllib.parse.quote(query)}"

def google_search(query):
    return f"https://www.google.com/maps/search/{urllib.parse.quote(query + ' South Korea')}"

def kakao_directions(origin, destination):
    s = urllib.parse.quote(origin)
    e = urllib.parse.quote(destination)
    return f"https://map.kakao.com/?sName={s}&eName={e}"

def google_directions(origin, destination):
    o = urllib.parse.quote(origin + " Korea")
    d = urllib.parse.quote(destination + " Korea")
    return f"https://www.google.com/maps/dir/{o}/{d}"

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
    "immigration":       {"name": "Immigration Office (출입국관리소)", "search_kr": "출입국관리소", "description": "Apply for ARC here. Book appointment first at HiKorea.go.kr", "tip": "Bring: passport + enrollment cert + 2 photos + 30,000 won"},
    "community_center":  {"name": "Community Center (주민센터)", "search_kr": "주민센터", "description": "Register your address within 14 days of moving in", "tip": "Get 전입신고 (free) + 확정일자 (600 won) to protect your deposit"},
    "shinhan_bank":      {"name": "Shinhan Bank (신한은행)", "search_kr": "신한은행", "description": "Most foreigner-friendly bank with English staff near universities", "tip": "Need ARC + passport. Some branches accept passport + enrollment cert."},
    "kb_bank":           {"name": "KB Kookmin Bank (국민은행)", "search_kr": "국민은행", "description": "Most ATM locations in Korea", "tip": "KB App has partial English support"},
    "hospital":          {"name": "Emergency Room (응급실)", "search_kr": "응급실", "description": "24/7 emergency medical care", "tip": "Say: 영어 통역사 불러주세요 (please call English interpreter)"},
    "pharmacy":          {"name": "Pharmacy (약국)", "search_kr": "약국", "description": "No prescription needed for basic medicine. Open ~9am-10pm", "tip": "Show symptoms with Papago camera if needed"},
    "halal_restaurant":  {"name": "Halal Restaurant (할랄 레스토랑)", "search_kr": "할랄 식당", "description": "Certified halal food near you", "tip": "Itaewon (Seoul Line 6) has the most options. Also check HalalKorea.com"},
    "daiso":             {"name": "Daiso (다이소)", "search_kr": "다이소", "description": "Korean dollar store. Everything 1,000-5,000 won", "tip": "Get bedding, kitchen supplies, hangers, storage boxes here first week"},
    "emart":             {"name": "Emart Supermarket (이마트)", "search_kr": "이마트", "description": "Large supermarket with best grocery prices", "tip": "Check basement floor for discounted items near closing time"},
    "police":            {"name": "Police Station (경찰서)", "search_kr": "경찰서", "description": "For non-emergency police matters", "tip": "Emergency: call 112 (faster than going to station)"},
    "post_office":       {"name": "Post Office (우체국)", "search_kr": "우체국", "description": "Send packages home or within Korea. Also offers banking.", "tip": "우체국 통장 (post office bank account) - foreigners can open without ARC in some locations"},
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
        f"   (Search result → tap '길찾기' button for route)\n"
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
    """Format a known important place with all 3 links."""
    if place_key not in IMPORTANT_PLACES:
        return None
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
    return msg


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
