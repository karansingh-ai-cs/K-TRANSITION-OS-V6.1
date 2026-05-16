# features/news_fetcher.py
# fetches Korea news - multiple RSS sources with fallback to curated links
# the fallback is important: if RSS is blocked, still show useful resources
import requests, xml.etree.ElementTree as ET, logging, time, re
from datetime import datetime
logger = logging.getLogger(__name__)

_cache = {"data": [], "last_updated": 0}
CACHE_DURATION = 1800  # 30 min

RSS_FEEDS = [
    {"name": "Korea Herald",      "url": "https://www.koreaherald.com/rss/index.xml",      "label": "KH"},
    {"name": "Korea JoongAng",    "url": "https://koreajoongangdaily.joins.com/rss/rss.xml","label": "JA"},
    {"name": "Arirang News",      "url": "https://www.arirang.com/rss/news.xml",           "label": "AR"},
    {"name": "Korea Times",       "url": "https://www.koreatimes.co.kr/www/rss/rss.xml",   "label": "KT"},
]

RELEVANT_KEYWORDS = [
    "international student","foreigner","visa","immigration","foreign student",
    "university","scholarship","gks","arc","registration","tuition",
    "subway","bus","transport","weather","typhoon","holiday","festival","event",
    "seoul","busan","daegu","incheon","rent","housing","apartment","scam","fraud",
    "health","hospital","insurance","nhis","exchange rate","won","inflation","price",
    "safety","crime","earthquake","disaster","students","campus","dormitory",
]

# static fallback - always useful even when RSS fails
STATIC_NEWS_LINKS = [
    {"title": "Korea Herald - Latest News", "url": "https://www.koreaherald.com", "desc": "Main English news in Korea"},
    {"title": "Korea JoongAng Daily",       "url": "https://koreajoongangdaily.joins.com", "desc": "English news, good for student-relevant stories"},
    {"title": "Study in Korea (Official)",  "url": "https://www.studyinkorea.go.kr/en/main.do", "desc": "Official government site for international students"},
    {"title": "HiKorea Immigration Info",   "url": "https://www.hikorea.go.kr", "desc": "Visa, ARC, immigration updates"},
    {"title": "Seoul Metropolitan Govt",    "url": "https://english.seoul.go.kr", "desc": "Seoul news and events in English"},
    {"title": "Korean Cultural Events",     "url": "https://www.visitkorea.or.kr/ena/EV/EVMain.jsp", "desc": "Korea Tourism - festivals and events calendar"},
]

def fetch_rss(url, timeout=6):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:15]:
            title   = item.findtext("title","").strip()
            link    = item.findtext("link","").strip()
            desc    = re.sub(r'<[^>]+>','', item.findtext("description","")).strip()[:200]
            if title:
                items.append({"title":title,"link":link,"summary":desc})
        return items
    except Exception as e:
        logger.warning("RSS failed %s: %s", url, str(e)[:60])
        return []

def is_relevant(item):
    text = (item.get("title","") + " " + item.get("summary","")).lower()
    return any(kw in text for kw in RELEVANT_KEYWORDS)

def get_news(max_items=5, relevant_only=True):
    global _cache
    now = time.time()
    if _cache["data"] and (now - _cache["last_updated"]) < CACHE_DURATION:
        data = _cache["data"]
        if relevant_only:
            filtered = [n for n in data if n.get("relevant")]
            return (filtered or data)[:max_items]
        return data[:max_items]

    all_items = []
    for feed in RSS_FEEDS:
        items = fetch_rss(feed["url"])
        for item in items:
            item["source"]   = feed["name"]
            item["label"]    = feed["label"]
            item["relevant"] = is_relevant(item)
        all_items.extend(items)

    # deduplicate
    seen, unique = set(), []
    for item in all_items:
        key = item["title"].lower()[:50]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    _cache["data"]         = unique
    _cache["last_updated"] = now
    logger.info("Fetched %d news items", len(unique))

    if relevant_only:
        filtered = [n for n in unique if n.get("relevant")]
        return (filtered or unique)[:max_items]
    return unique[:max_items]

def format_news(news_items):
    if not news_items:
        # fallback to static links
        msg  = "News feeds are temporarily unavailable. Here are the best English news sources for Korea:\n\n"
        for link in STATIC_NEWS_LINKS:
            msg += f"- {link['title']}: {link['url']}\n  {link['desc']}\n\n"
        msg += f"Tip: Bookmark koreaherald.com - it covers student visa and housing news regularly."
        return msg

    msg = f"Latest Korea News (updated {datetime.now().strftime('%H:%M')})\n\n"
    for item in news_items[:5]:
        title   = item.get("title","No title")
        link    = item.get("link","")
        summary = item.get("summary","")
        source  = item.get("source","")
        msg += f"[{source}] {title}\n"
        if summary:
            msg += f"{summary[:120]}...\n"
        if link:
            msg += f"Read: {link}\n"
        msg += "\n"
    return msg.strip()

def filter_news_by_topic(topic: str, max_items=5):
    """Filter news by a specific topic from intent router entities."""
    topic_keywords = {
        "visa": ["visa", "immigration", "arc", "foreigner", "registration", "d-2", "d-4"],
        "housing": ["rent", "housing", "apartment", "deposit", "landlord", "jeonse", "wolse"],
        "scholarship": ["scholarship", "gks", "tuition", "funding", "grant"],
        "safety": ["safety", "crime", "earthquake", "disaster", "typhoon", "warning"],
        "transport": ["subway", "bus", "transport", "train", "ktx", "airport"],
        "weather": ["weather", "typhoon", "rain", "snow", "temperature", "heat"],
        "food": ["food", "restaurant", "halal", "vegetarian", "price", "inflation"],
        "campus": ["university", "campus", "student", "dormitory", "semester"],
        "health": ["health", "hospital", "insurance", "nhis", "medical"],
    }
    keywords = topic_keywords.get(topic.lower(), [topic.lower()])
    all_news = get_news(max_items=20, relevant_only=False)
    filtered = []
    for item in all_news:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        if any(kw in text for kw in keywords):
            filtered.append(item)
    if not filtered:
        return get_news(max_items=max_items)
    return filtered[:max_items]


def get_news_for_students():
    """curated links always relevant for international students"""
    return (
        "Resources for International Students in Korea\n\n"
        "Official:\n"
        "- Study in Korea: https://www.studyinkorea.go.kr/en/main.do\n"
        "- HiKorea (visa/ARC): https://www.hikorea.go.kr\n"
        "- Government24: https://www.gov.kr/portal/main/nonelogin\n\n"
        "News:\n"
        "- Korea Herald: https://www.koreaherald.com\n"
        "- Korea JoongAng Daily: https://koreajoongangdaily.joins.com\n\n"
        "Student Life:\n"
        "- Seoul events: https://english.seoul.go.kr\n"
        "- Korea Tourism (festivals): https://www.visitkorea.or.kr/ena/EV/EVMain.jsp\n\n"
        "Tip: Most major Korean universities have a Facebook group for international students - search '[university name] international students'"
    )
