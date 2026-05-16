# core/risk_detector.py
# this checks messages for specific risks using rules
# runs BEFORE the AI so dangerous situations get flagged immediately
# the AI then uses these flags to give better responses
# 
# why not just use AI for everything?
# because rule-based is instant and reliable
# AI can be slow or sometimes miss things
# for dangerous situations (deposit scams, haram food, crisis) we need certainty

import json
import os
import re
import logging

logger = logging.getLogger(__name__)


def load_data(filename):
    # DATA_DIR is computed from config.py location (project root)
    # this works no matter where the file is in the folder structure
    from config import DATA_DIR
    filepath = DATA_DIR / filename
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Could not load %s: %s", filename, e)
        return {}


# load rule data once when module starts
FOOD_DATA    = load_data("food_rules.json")
HOUSING_DATA = load_data("housing_rules.json")
GENERAL_DATA = load_data("general_rules.json")

FOOD_RULES    = FOOD_DATA.get("rules", [])
HOUSING_RULES = HOUSING_DATA.get("rules", [])
GENERAL_RULES = GENERAL_DATA.get("rules", [])
HARAM_LIST    = FOOD_DATA.get("haram_ingredients", [])


# crisis keywords - highest priority
CRISIS_WORDS = [
    "kill myself", "want to die", "end my life", "suicide",
    "no reason to live", "hurt myself", "can't go on",
    "자살", "죽고싶다", "죽고 싶다"
]

# deposit scam pattern words
DEPOSIT_WORDS = ["deposit", "보증금", "pay", "transfer", "million won", "만원"]
SCAM_WORDS    = ["no contract", "contract later", "contract next week", "without contract",
                 "계약서 없", "나중에 계약", "sign later", "trust me", "verbal agreement",
                 "cash only", "after moving", "sign after", "계약서 안"]


def keyword_match(text, keywords):
    """count how many keywords appear in text"""
    text_lower = text.lower()
    count = 0
    matched = []
    for kw in keywords:
        if kw.lower() in text_lower:
            count += 1
            matched.append(kw)
    return count, matched


def detect_crisis(text):
    """returns True if mental health crisis detected"""
    text_lower = text.lower()
    for word in CRISIS_WORDS:
        if word.lower() in text_lower:
            return True
    return False


def detect_deposit_scam(text):
    """detects the classic 'pay deposit before contract' scam"""
    text_lower = text.lower()
    has_deposit = any(w.lower() in text_lower for w in DEPOSIT_WORDS)
    has_scam    = any(w.lower() in text_lower for w in SCAM_WORDS)
    return has_deposit and has_scam


def detect_haram(text, user_diet="none"):
    """check if message mentions haram ingredients"""
    if not HARAM_LIST:
        return False, []
    text_lower = text.lower()
    found = [item for item in HARAM_LIST if item.lower() in text_lower]
    # flag if user is halal or if they mentioned halal/muslim
    is_halal_user = user_diet == "halal" or any(w in text_lower for w in ["halal", "haram", "muslim", "islam"])
    return len(found) > 0 and is_halal_user, found


def detect_allergens(text, user_allergies):
    """check for allergens the user registered"""
    if not user_allergies:
        return False, []

    allergen_keywords = {
        "nuts":      ["peanut", "땅콩", "walnut", "호두", "almond", "아몬드", "nut", "견과"],
        "peanut":    ["peanut", "땅콩"],
        "dairy":     ["milk", "우유", "cheese", "치즈", "butter", "버터", "cream", "크림", "lactose"],
        "gluten":    ["wheat", "밀가루", "flour", "barley", "보리", "gluten"],
        "eggs":      ["egg", "달걀", "계란"],
        "fish":      ["fish", "생선", "anchovy", "멸치", "tuna", "참치", "mackerel", "고등어"],
        "shellfish": ["shrimp", "새우", "crab", "게", "lobster", "clam", "조개", "oyster", "굴"],
        "soy":       ["soy", "콩", "tofu", "두부", "soybean", "된장", "간장"]
    }

    text_lower = text.lower()
    found_allergens = []
    for allergy in user_allergies:
        keywords = allergen_keywords.get(allergy, [allergy])
        if any(kw.lower() in text_lower for kw in keywords):
            found_allergens.append(allergy)

    return len(found_allergens) > 0, found_allergens


def classify_message(text):
    """figure out what category the message is about"""
    text_lower = text.lower()

    scores = {
        "food":          0,
        "housing":       0,
        "mental":        0,
        "daily_life":    0,
        "communication": 0,
        "visa":          0,
        "korean":        0,  # korean language learning
        "news":          0,
        "schedule":      0,
    }

    food_words = ["food", "eat", "halal", "haram", "pork", "vegetarian", "vegan", "allergy",
                  "restaurant", "menu", "ingredient", "cook", "meal", "snack", "drink",
                  "김치", "삼겹살", "비빔밥", "라면", "떡볶이", "불고기", "음식", "먹다",
                  "expired", "유통기한", "souvlaki", "spicy", "매운"]

    housing_words = ["house", "housing", "room", "rent", "deposit", "landlord", "contract",
                     "lease", "apartment", "jeonse", "wolse", "gosiwon", "전세", "월세",
                     "보증금", "집주인", "계약", "고시원", "이사", "move in", "mold", "repair"]

    mental_words = ["lonely", "depressed", "anxious", "stressed", "homesick", "sad",
                    "struggling", "overwhelmed", "mental health", "외롭다", "우울", "불안",
                    "힘들다", "힘들어", "지쳐", "도움", "cry", "hopeless", "친구 없"]

    daily_words = ["garbage", "trash", "bus", "subway", "transport", "t-money", "bank",
                   "hospital", "doctor", "medicine", "pharmacy", "arc", "alien registration",
                   "visa", "emergency", "noise", "neighbor", "convenience store", "쓰레기",
                   "지하철", "버스", "병원", "약국", "외국인등록"]

    visa_words = ["visa", "arc", "immigration", "d-2", "d-4", "work permit", "extension",
                  "overstay", "출입국", "비자", "체류", "취업", "work hour", "part time"]

    korean_learn_words = ["learn korean", "korean word", "how to say", "translate",
                          "korean lesson", "topik", "vocabulary", "speak korean",
                          "pronunciation", "한국어 배우", "word of the day", "quiz"]

    news_words = ["news", "latest", "recent", "happening", "event", "today in korea",
                  "what's going on", "update", "뉴스", "최근"]

    schedule_words = ["schedule", "plan", "first week", "what should i do", "first day",
                      "to do list", "checklist", "when should i", "help me plan",
                      "first month", "routine", "agenda"]

    for w in food_words:
        if w in text_lower:
            scores["food"] += 1
    for w in housing_words:
        if w in text_lower:
            scores["housing"] += 1
    for w in mental_words:
        if w in text_lower:
            scores["mental"] += 2  # mental health gets higher weight
    for w in daily_words:
        if w in text_lower:
            scores["daily_life"] += 1
    for w in visa_words:
        if w in text_lower:
            scores["visa"] += 1
    for w in korean_learn_words:
        if w in text_lower:
            scores["korean"] += 2
    for w in news_words:
        if w in text_lower:
            scores["news"] += 2
    for w in schedule_words:
        if w in text_lower:
            scores["schedule"] += 2

    # find best category
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "general"
    return best


def scan_message(text, user_info=None):
    """
    main function - scans a message and returns detected risks
    call this before asking the AI so the AI knows what risks were detected
    returns a dict with all findings
    """
    if user_info is None:
        user_info = {}

    user_diet      = user_info.get("diet", "none")
    user_allergies = user_info.get("allergies", [])

    result = {
        "category":      classify_message(text),
        "is_crisis":     detect_crisis(text),
        "is_scam":       detect_deposit_scam(text),
        "is_haram":      False,
        "haram_items":   [],
        "has_allergen":  False,
        "allergens":     [],
        "risk_level":    "LOW",
        "flags":         []
    }

    # check haram
    haram, haram_items = detect_haram(text, user_diet)
    if haram:
        result["is_haram"]    = True
        result["haram_items"] = haram_items
        result["flags"].append("HARAM_DETECTED")

    # check allergens
    allergen, allergens = detect_allergens(text, user_allergies)
    if allergen:
        result["has_allergen"] = True
        result["allergens"]    = allergens
        result["flags"].append("ALLERGEN_ALERT")

    # set overall risk level
    if result["is_crisis"] or result["is_scam"]:
        result["risk_level"] = "HIGH"
        result["flags"].append("HIGH_RISK")
    elif result["is_haram"] or result["has_allergen"]:
        result["risk_level"] = "HIGH"
    elif result["category"] in ("housing", "visa"):
        result["risk_level"] = "MEDIUM"
    else:
        result["risk_level"] = "LOW"

    return result


def build_context_for_ai(scan_result, user_info):
    """
    build a context string to inject into the AI prompt
    so the AI knows what risks were already detected
    """
    context_parts = []

    user_diet = user_info.get("diet", "none")
    user_allergies = user_info.get("allergies", [])
    university = user_info.get("university", "")
    city = user_info.get("city", "")

    # user profile context
    if user_diet and user_diet != "none":
        context_parts.append(f"User diet preference: {user_diet}")
    if user_allergies:
        context_parts.append(f"User allergies: {', '.join(user_allergies)}")
    if university:
        context_parts.append(f"User's university: {university}")
    if city:
        context_parts.append(f"User's city in Korea: {city}")

    # risk flags
    if scan_result.get("is_crisis"):
        context_parts.append("⚠️ CRISIS DETECTED: User may be experiencing mental health crisis. Prioritize crisis resources (1393, 1345) in your response.")

    if scan_result.get("is_scam"):
        context_parts.append("🔴 SCAM PATTERN DETECTED: User may be describing a deposit-without-contract situation. Warn them strongly and give specific steps to protect themselves.")

    if scan_result.get("is_haram") and scan_result.get("haram_items"):
        items = ", ".join(scan_result["haram_items"][:3])
        context_parts.append(f"🔴 HARAM/PORK DETECTED: The following haram ingredients were found: {items}. User follows halal diet. Warn clearly and give alternatives.")

    if scan_result.get("has_allergen") and scan_result.get("allergens"):
        allergens = ", ".join(scan_result["allergens"])
        context_parts.append(f"🔴 ALLERGEN ALERT: User is allergic to {allergens} and this food may contain it. Warn clearly.")

    if not context_parts:
        return ""

    return "Context for this response: " + " | ".join(context_parts)
