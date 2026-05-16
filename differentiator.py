# features/differentiator.py
# the features that make this bot different from ChatGPT / Claude / Gemini
# these are things a generic AI assistant cannot do as a dedicated Korea companion:
#
#  1. Korean Name Generator  — get your own Korean name with meaning
#  2. Live KRW Exchange Rate — free, no API key, always current
#  3. Cultural Shock Decoder — specific Korean social rules explained
#  4. Scam Scanner          — instant yes/no on any suspicious situation
#  5. Daily Tip             — proactive daily useful fact about Korea
#  6. Onboarding Flow       — guided setup for brand-new arrivals

import requests
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 1. LIVE KRW EXCHANGE RATE
# Uses open.er-api.com — completely free, no key needed
# ─────────────────────────────────────────────

# currencies common for GKS scholarship students
STUDENT_CURRENCIES = {
    "USD": ("🇺🇸", "US Dollar"),
    "EUR": ("🇪🇺", "Euro"),
    "GBP": ("🇬🇧", "British Pound"),
    "JPY": ("🇯🇵", "Japanese Yen"),
    "CNY": ("🇨🇳", "Chinese Yuan"),
    "INR": ("🇮🇳", "Indian Rupee"),
    "BDT": ("🇧🇩", "Bangladeshi Taka"),
    "NPR": ("🇳🇵", "Nepali Rupee"),
    "VND": ("🇻🇳", "Vietnamese Dong"),
    "IDR": ("🇮🇩", "Indonesian Rupiah"),
    "MYR": ("🇲🇾", "Malaysian Ringgit"),
    "PKR": ("🇵🇰", "Pakistani Rupee"),
    "EGP": ("🇪🇬", "Egyptian Pound"),
    "NGN": ("🇳🇬", "Nigerian Naira"),
    "MNT": ("🇲🇳", "Mongolian Tugrik"),
    "UZS": ("🇺🇿", "Uzbek Som"),
    "KZT": ("🇰🇿", "Kazakh Tenge"),
    "TRY": ("🇹🇷", "Turkish Lira"),
    "THB": ("🇹🇭", "Thai Baht"),
    "PHP": ("🇵🇭", "Philippine Peso"),
}

_rate_cache = {"data": None, "time": 0}
RATE_CACHE_SECS = 3600  # cache for 1 hour

def get_exchange_rates():
    """Fetch KRW rates from free API. Returns dict {currency: rate} where rate = 1 KRW = X currency"""
    import time
    now = time.time()
    if _rate_cache["data"] and (now - _rate_cache["time"]) < RATE_CACHE_SECS:
        return _rate_cache["data"]
    try:
        # this API is free and doesn't need a key
        r = requests.get("https://open.er-api.com/v6/latest/KRW", timeout=8)
        r.raise_for_status()
        data = r.json()
        if data.get("result") == "success":
            rates = data.get("rates", {})
            _rate_cache["data"] = rates
            _rate_cache["time"] = now
            return rates
    except Exception as e:
        logger.warning("Exchange rate fetch failed: %s", e)
    return None

def format_exchange_rates(amount_krw=10000):
    """Format a nicely readable exchange rate table"""
    rates = get_exchange_rates()
    if not rates:
        return (
            "Could not fetch live rates right now. Try later!\n\n"
            "Quick reference (approximate, always verify):\n"
            "10,000 KRW = ~$7.50 USD = ~7 EUR = ~600 INR\n"
            "Check current rate: https://finance.naver.com/marketindex/"
        )

    update_time = datetime.now().strftime("%H:%M, %b %d")

    msg  = f"Live KRW Exchange Rate\n"
    msg += f"({amount_krw:,} KRW = ... as of {update_time})\n\n"

    for code, (flag, name) in STUDENT_CURRENCIES.items():
        rate = rates.get(code)
        if rate and rate > 0:
            converted = amount_krw * rate
            # format based on magnitude
            if converted >= 1000:
                fmt = f"{converted:,.0f}"
            elif converted >= 10:
                fmt = f"{converted:,.1f}"
            else:
                fmt = f"{converted:,.4f}"
            msg += f"{flag} {fmt} {code}\n"

    msg += f"\n10,000 won = your daily meal budget\n"
    msg += "50,000 won = your weekly grocery budget\n"
    msg += "1,000,000 won = ~$750 USD (monthly scholarship reference)\n\n"
    msg += f"Full rates: https://finance.naver.com/marketindex/"

    return msg

def convert_krw(amount, currency="USD"):
    """Convert a specific KRW amount to a currency"""
    rates = get_exchange_rates()
    if not rates:
        return None
    rate = rates.get(currency.upper())
    if not rate:
        return None
    return amount * rate


# ─────────────────────────────────────────────
# 2. KOREAN NAME GENERATOR
# ─────────────────────────────────────────────

# Common Korean family names with meanings (for generation)
KOREAN_FAMILY_NAMES = [
    ("김", "Kim", "gold"),
    ("이", "Lee/Yi", "plum tree"),
    ("박", "Park", "gourd/bright"),
    ("최", "Choi", "highest mountain"),
    ("정", "Jung/Jeong", "upright/true"),
    ("강", "Kang", "river/strong"),
    ("조", "Jo/Cho", "dynasty/ancestor"),
    ("윤", "Yoon/Yun", "allow/ruling"),
    ("장", "Jang", "long/chapter"),
    ("임", "Lim/Im", "forest"),
    ("한", "Han", "Korea/one"),
    ("오", "Oh", "crow/crow"),
    ("서", "Seo", "the west/auspicious"),
    ("신", "Shin/Sin", "new"),
    ("권", "Kwon", "authority/power"),
    ("황", "Hwang", "yellow/emperor"),
    ("안", "An", "peace"),
    ("송", "Song", "pine tree"),
    ("전", "Jeon/Chun", "before/field"),
    ("홍", "Hong", "wide/great"),
]

# Common Korean given name syllables with meanings
NAME_SYLLABLES = {
    "positive_traits": [
        ("준", "talented/handsome"), ("민", "people/bright"), ("서", "auspicious"),
        ("지", "wisdom/will"), ("현", "wise/bright"), ("수", "longevity/excellence"),
        ("영", "bright/eternal"), ("진", "precious/true"), ("태", "great/peaceful"),
        ("하", "summer/great"), ("나", "me/fragrance"), ("아", "elegant/child"),
    ],
    "nature": [
        ("산", "mountain"), ("해", "sea/sun"), ("달", "moon"), ("별", "star"),
        ("강", "river"), ("숲", "forest"), ("봄", "spring"), ("빛", "light"),
    ],
    "virtues": [
        ("인", "benevolence"), ("의", "righteousness"), ("예", "courtesy"),
        ("지", "wisdom"), ("신", "faith/trust"), ("효", "filial piety"),
    ],
}

def generate_korean_name_suggestions(user_name, user_gender=""):
    """Generate Korean name suggestions for a given name"""
    # pick a surname based on first letter of name (fun phonetic match)
    name_lower = user_name.lower()
    surname_picks = {
        'a': ("안", "An", "peace"), 'b': ("박", "Park", "bright"),
        'c': ("최", "Choi", "highest"), 'd': ("동", "Dong", "east"),
        'e': ("이", "Lee", "plum tree"), 'f': ("하", "Ha", "great"),
        'g': ("강", "Kang", "strong"), 'h': ("한", "Han", "Korea"),
        'i': ("임", "Lim", "forest"), 'j': ("정", "Jung", "upright"),
        'k': ("김", "Kim", "gold"), 'l': ("이", "Lee", "plum tree"),
        'm': ("문", "Moon", "literature"), 'n': ("노", "Noh", "reed"),
        'o': ("오", "Oh", "crow"), 'p': ("박", "Park", "bright"),
        'q': ("권", "Kwon", "authority"), 'r': ("류", "Ryu", "willow"),
        's': ("서", "Seo", "auspicious"), 't': ("태", "Tae", "peaceful"),
        'u': ("유", "Yu", "similar"), 'v': ("변", "Byun", "capable"),
        'w': ("원", "Won", "original"), 'x': ("허", "Heo", "allow"),
        'y': ("윤", "Yoon", "allow"), 'z': ("장", "Jang", "long"),
    }
    first_char = name_lower[0] if name_lower else 'k'
    surname = surname_picks.get(first_char, ("김", "Kim", "gold"))

    # build 2-3 name options with different syllable combinations
    options = []

    # option 1: sound-inspired (try to phonetically match)
    positive = random.sample(NAME_SYLLABLES["positive_traits"], 2)
    option1_given = positive[0][0] + positive[1][0]
    option1_meaning = f"{positive[0][1]} and {positive[1][1]}"
    options.append({
        "korean": f"{surname[0]}{option1_given}",
        "romanized": f"{surname[1]} {option1_given}",
        "meaning": f"Family name {surname[0]}({surname[1]}) means '{surname[2]}'. Given name {option1_given} means '{option1_meaning}'.",
        "style": "Traditional"
    })

    # option 2: nature-inspired
    nature   = random.choice(NAME_SYLLABLES["nature"])
    virtue   = random.choice(NAME_SYLLABLES["virtues"])
    option2_given = virtue[0] + nature[0]
    options.append({
        "korean": f"{surname[0]}{option2_given}",
        "romanized": f"{surname[1]} {option2_given}",
        "meaning": f"Family name means '{surname[2]}'. Given name means '{virtue[1]} like {nature[1]}'.",
        "style": "Nature-inspired"
    })

    # option 3: simpler, single-syllable style with phonetic match
    phonetic_map = {
        'a':'아', 'e':'에', 'i':'이', 'o':'오', 'u':'우',
        'n':'나', 'm':'민', 'l':'리', 'r':'리', 'j':'지',
        'k':'기', 's':'수', 'h':'하', 'y':'유', 'w':'원',
    }
    # try to use first vowel of name as phonetic basis
    phonetic_syl = None
    for char in name_lower:
        if char in phonetic_map:
            phonetic_syl = phonetic_map[char]
            break
    if not phonetic_syl:
        phonetic_syl = "준"  # default

    options.append({
        "korean": f"{surname[0]}{phonetic_syl}",
        "romanized": f"{surname[1]} {phonetic_syl}",
        "meaning": f"Family name means '{surname[2]}'. Single-syllable given name phonetically inspired by your name.",
        "style": "Modern/Short"
    })

    return surname, options

def format_korean_name(user_name, user_gender=""):
    """Format the Korean name generation response"""
    surname, options = generate_korean_name_suggestions(user_name, user_gender)

    msg  = f"Your Korean Name Suggestions for {user_name}!\n\n"
    msg += "Korean names follow: Family Name + Given Name (opposite of Western order)\n\n"

    for i, opt in enumerate(options, 1):
        msg += f"Option {i} - {opt['style']}:\n"
        msg += f"Korean: {opt['korean']}\n"
        msg += f"Romanized: {opt['romanized']}\n"
        msg += f"Meaning: {opt['meaning']}\n\n"

    msg += "How Korean names work:\n"
    msg += "- 1 syllable family name + 2 syllable given name (most common)\n"
    msg += "- Korean name goes on official documents and school records\n"
    msg += "- Koreans will often ask your Korean name - having one helps a lot!\n"
    msg += "- You can choose any of these or mix and match syllables you like\n\n"
    msg += "Want AI to generate a more personalized name? Just tell me:\n"
    msg += "- What personality traits you want reflected\n"
    msg += "- Any Korean words you like\n"
    msg += "- Gender preference (male names tend to use different syllables)\n\n"
    msg += "Or ask me: 'generate my Korean name [your name] [trait you want]'"

    return msg


# ─────────────────────────────────────────────
# 3. CULTURAL SHOCK DECODER
# specific Korean social customs explained
# ─────────────────────────────────────────────

CULTURAL_TIPS = [
    {
        "title": "Age and honorifics matter a LOT",
        "situation": "Meeting Korean students for the first time",
        "explanation": "The first thing Koreans often ask: 'How old are you?' (나이가 어떻게 되세요?). This isn't rude - age determines how people speak to each other. If someone is older, Koreans use formal/respectful speech (존댓말). If same age or younger, casual speech (반말) is used between friends.",
        "do": "When meeting new Korean students, it's fine to ask age. If they're older: call them 선배 (sunbae = senior). Use 존댓말 until they say you can speak casually.",
        "dont": "Don't be offended by the age question. Don't speak casually to someone older right away without permission."
    },
    {
        "title": "Paying for meals: the senior pays",
        "situation": "Going out to eat with Korean friends",
        "explanation": "In Korea, it's very common for the oldest person or senior student (선배) to pay for everyone. This is called '선배가 산다' (senior treats). It's not splitting the bill Western-style. You'll often fight over who pays.",
        "do": "As a first-year/junior, try to pay sometimes to show respect. Say '제가 낼게요' (I'll pay). The back-and-forth is part of the culture.",
        "dont": "Don't always let others pay without trying to contribute sometimes. And if a senior pays, always say thank you properly: 잘 먹겠습니다 before eating and 잘 먹었습니다 after."
    },
    {
        "title": "Two hands when giving and receiving",
        "situation": "Receiving anything from someone older",
        "explanation": "When giving or receiving anything (business cards, food, drinks, documents, money) from someone older, use both hands or support one hand with the other. Using one hand is considered disrespectful.",
        "do": "Use both hands when receiving things from professors, landlords, officials, or anyone older.",
        "dont": "Don't grab something with one hand from an older person without at least supporting your wrist with the other hand."
    },
    {
        "title": "Pouring drinks for others first",
        "situation": "Group meals and social gatherings",
        "explanation": "In Korea, you pour drinks for others first, not for yourself. Watch others' glasses and refill when low. Never pour your own drink if someone else is present.",
        "do": "Keep an eye on other people's glasses and offer to refill them. Say '한 잔 더 드릴까요?' (Shall I pour you another?).",
        "dont": "Don't pour for yourself first. Don't start drinking before the eldest person takes the first drink."
    },
    {
        "title": "The bow: depth = respect level",
        "situation": "Greeting professors, officials, landlords",
        "explanation": "Bowing is the Korean greeting. The deeper the bow, the more respect. 15° bow for daily greetings. 30° bow for meeting someone for the first time, or to show thanks. 45° bow for deep apology or great respect.",
        "do": "A slight head nod is acceptable for casual greetings. 30° bow when meeting your professor for the first time.",
        "dont": "Don't stick out your hand for a handshake unless the other person initiates it."
    },
    {
        "title": "Silence is comfortable in Korea",
        "situation": "Sitting with Korean friends quietly",
        "explanation": "In many Western cultures, silence feels awkward and people try to fill it. In Korea, sitting quietly with someone you're comfortable with is totally normal and even shows closeness.",
        "do": "Don't feel pressured to fill silences with small talk. It's perfectly fine.",
        "dont": "Don't assume your Korean friends are bored or upset just because they're quiet."
    },
    {
        "title": "Public vs private self",
        "situation": "When Koreans seem cold at first",
        "explanation": "Korean social culture has a strong in-group (우리/uri) vs out-group distinction. Once you're in the friend group, Koreans are incredibly warm and generous. Getting in takes longer but is very rewarding.",
        "do": "Be patient. Join study groups, language exchange programs, club activities (동아리). Shared experiences build trust quickly.",
        "dont": "Don't interpret initial formality as unfriendliness. Koreans are actually very warm once comfortable with you."
    },
    {
        "title": "Shoes OFF at the entrance",
        "situation": "Visiting someone's home or apartment",
        "explanation": "ALWAYS remove shoes when entering a Korean home. There's always a clear step or tile area at the entrance (현관) where shoes stay. Wearing shoes inside is a serious faux-pas.",
        "do": "Remove shoes at the 현관 (entrance). Many homes have slippers for guests.",
        "dont": "Never walk into a Korean home with shoes on. Ever."
    },
    {
        "title": "WOW, you speak Korean!",
        "situation": "Using any Korean at all with locals",
        "explanation": "Even saying '안녕하세요' or '감사합니다' correctly will often get a very positive reaction from Koreans. They genuinely appreciate foreigners learning their language.",
        "do": "Use any Korean you know, even if it's just basic phrases. Koreans will be impressed and more helpful.",
        "dont": "Don't be shy about making mistakes. Koreans are very encouraging about language learning efforts."
    },
    {
        "title": "Speaking informally (반말) without permission",
        "situation": "With Korean friends your age or younger",
        "explanation": "반말 (banmal) is casual speech used between close friends of similar age. Using it too early with someone older is rude. But if you're the same age and they speak to you in 반말, it usually means they're comfortable with you.",
        "do": "Wait for the other person to suggest using 반말. They might say '반말로 해도 돼' (you can speak casually).",
        "dont": "Don't use casual speech with someone older without being invited to do so."
    },
]

def get_cultural_tip(index=None):
    """Get a cultural tip - random or by index"""
    if index is None:
        import datetime
        index = datetime.date.today().toordinal()
    return CULTURAL_TIPS[index % len(CULTURAL_TIPS)]

def format_cultural_tip(tip=None):
    """Format a cultural tip for display"""
    if tip is None:
        tip = get_cultural_tip()

    msg  = f"Korean Culture: {tip['title']}\n\n"
    msg += f"When: {tip['situation']}\n\n"
    msg += f"What's happening:\n{tip['explanation']}\n\n"
    msg += f"Do: {tip['do']}\n\n"
    msg += f"Avoid: {tip['dont']}"

    return msg

def get_all_cultural_topics():
    return [t["title"] for t in CULTURAL_TIPS]


# ─────────────────────────────────────────────
# 4. QUICK SCAM SCANNER
# fast rule-based scam check with yes/no verdict
# ─────────────────────────────────────────────

SCAM_RED_FLAGS = [
    ("deposit without contract", "HOUSING SCAM", "Never pay deposit before signing written contract (임대차계약서). This is illegal and you'll likely lose all your money."),
    ("contract later", "HOUSING SCAM", "A legitimate landlord will never ask you to pay now and sign the contract later."),
    ("advance fee", "JOB SCAM", "Legitimate employers NEVER ask for upfront payment. If they're asking for money to get a job, it's a scam."),
    ("easy money", "JOB SCAM", "Any job promising unusually high pay for simple tasks is almost certainly a scam."),
    ("investment opportunity", "INVESTMENT SCAM", "Korean police report many investment scams targeting foreign students. Never invest money through someone you just met."),
    ("government asked for money", "VOICE PHISHING", "Korean government NEVER asks for money by phone. This is 보이스피싱 (voice phishing). Hang up immediately."),
    ("you won a prize", "LOTTERY SCAM", "You didn't enter a lottery. Don't send any money or personal info."),
    ("send money first", "ADVANCE FEE SCAM", "Any situation where you must pay to receive money is a scam."),
    ("wire transfer", "MONEY MULE", "If someone asks you to receive money and forward it, you could become a money mule and face criminal charges."),
    ("too cheap rent", "RENTAL SCAM", "Rent much cheaper than market rate = almost always fake listing or scam property."),
    ("no contract needed", "HOUSING SCAM", "All legitimate housing requires a contract in Korea. No exceptions."),
]

def quick_scam_scan(text):
    """Fast scam detection - returns verdict dict"""
    text_lower = text.lower()
    found_flags = []

    for flag, scam_type, explanation in SCAM_RED_FLAGS:
        if flag.lower() in text_lower:
            found_flags.append({"flag": flag, "type": scam_type, "explanation": explanation})

    if found_flags:
        return {
            "verdict":     "LIKELY SCAM",
            "confidence":  "HIGH" if len(found_flags) >= 2 else "MEDIUM",
            "flags":       found_flags,
            "action":      "Do NOT proceed. Call 1345 (foreigner helpline) for free advice."
        }
    return {"verdict": "No obvious scam flags detected", "confidence": "LOW", "flags": [], "action": "Stay cautious. Always verify before paying anything."}

def format_scam_scan(text):
    """Format scam scan result"""
    result = quick_scam_scan(text)
    verdict = result["verdict"]

    if "LIKELY SCAM" in verdict:
        msg  = f"SCAM ALERT - {result['confidence']} confidence\n\n"
        msg += "RED FLAGS DETECTED:\n\n"
        for flag_info in result["flags"]:
            msg += f"- {flag_info['type']}\n"
            msg += f"  '{flag_info['flag']}' — {flag_info['explanation']}\n\n"
        msg += f"ACTION: {result['action']}\n\n"
        msg += "Evidence: Screenshot everything. Save all messages.\n"
        msg += "Report: ecrm.police.go.kr or call 182"
    else:
        msg  = "No obvious scam flags in your description.\n\n"
        msg += "Still be careful:\n"
        msg += "- Never pay money without a written contract\n"
        msg += "- Verify property ownership at iros.go.kr (700 won)\n"
        msg += "- If something feels wrong, call 1345 for free advice\n"
        msg += "- Don't let anyone pressure you to decide quickly"

    return msg


# ─────────────────────────────────────────────
# 5. DAILY TIP
# rotates through practical Korea survival tips
# ─────────────────────────────────────────────

DAILY_TIPS = [
    "Convenience stores (CU, GS25, 7-Eleven) are your best friend. Open 24/7, you can pay bills, charge T-Money, use ATM, print documents, heat up food, and eat at the tables inside.",
    "당근마켓 (Danggeun Market) is Korea's Craigslist. Buy second-hand furniture, appliances, and electronics cheaply when setting up your room. Search your neighborhood.",
    "University cafeteria (학생식당) serves the cheapest meals near campus - usually 3,000-5,000 won for a full meal. Best bang for your money.",
    "Coupang (쿠팡) is Korea's Amazon but better. Rocket delivery means most items arrive next day or same day. Great for setting up your room without going to many shops.",
    "Kakao Talk (카카오톡) is how EVERYONE communicates in Korea. Your professor, landlord, and classmates will all use it. Set it up with your Korean number on day 1.",
    "Papago translator app by Naver is better than Google Translate for Korean. Has a camera mode where you point at Korean text and it translates live - lifesaver for menus and labels.",
    "Learn to read Hangeul (Korean alphabet) in 1-2 hours. You won't understand the words but you can read menus, station names, and signs. YouTube: 'Learn Korean alphabet in 1 hour'",
    "The T-Money transit card works on ALL buses and subways in Korea, not just Seoul. Load at least 30,000 won on it so you don't run out at bad times.",
    "Korean medicine at pharmacies (약국) is strong and effective. Show your symptoms using Papago camera. For common things like cold/stomach/headache you don't need a prescription.",
    "Daiso (다이소) is where you furnish your room for almost nothing. Everything is 1,000-5,000 won. Bedding, cookware, cleaning supplies, stationery - all here.",
    "The student discount is real in Korea. Always carry your student ID (학생증). Many restaurants, attractions, and transport have 학생 할인 (student discount).",
    "Korean banks close at 4pm and many are closed Saturday. For anything urgent with your bank, go on weekday mornings. Kakao Bank is the exception - fully digital, 24/7.",
    "When someone gives you their business card in Korea, look at it with both hands, read it, and don't put it directly in your pocket. It's a sign of respect.",
    "Trash bags (종량제 봉투) MUST be official ones sold at convenience stores. Putting normal trash in regular bags = fine up to 100,000 won. Buy the right bags immediately.",
    "Naver is more useful than Google in Korea. Use Naver Maps, Naver Translate, and Naver Search for Korean content. Google Maps is often outdated for Korean transit.",
    "The concept of 눈치 (nunchi) is important: reading the mood and situation without being told. Koreans are very attuned to this. If something seems off, it probably is.",
    "Korean hospitals are very affordable compared to Western countries. With NHIS insurance you pay only 20-30%. Even without insurance, basic treatment is cheaper than many countries.",
    "Korean summers (July-August) are extremely hot and humid. Buy a portable fan early. Korean winters (December-February) are very dry and cold. Get a humidifier for your room.",
    "You can send packages home cheaply via EMS at the post office (우체국). Much cheaper than DHL or FedEx for non-urgent items.",
    "When in doubt about anything official in Korea, call 1345. It's the foreigner helpline, free, 24/7, and has English, Chinese, Vietnamese and more. Use it more than you think you need to.",
    "Study cafes (스터디카페) are amazing for getting work done. Better than regular cafes - very quiet, 24/7 access, individual booths, air conditioned. Usually 1,000-2,000 won per hour.",
    "SIM card renewal: if you're on a prepaid plan, set a reminder to recharge before it expires. Korean prepaid plans usually expire in 30 days and you'll suddenly have no service.",
    "Korean apartments have ondol (floor heating). In winter your floor heats up - it's wonderful but adjust the thermostat carefully or your electricity bill will shock you.",
    "Language exchange (언어교환) is the fastest way to improve Korean AND make Korean friends. Your university likely has a program. If not, HelloTalk app connects you with native speakers.",
    "Print your enrollment certificate (재학증명서) at your university admin office or online. You'll need it for: bank accounts, phone plans, government offices, and the ARC application.",
    "The 24-hour 찜질방 (jjimjilbang / Korean sauna) is a uniquely Korean experience AND a cheap option if you arrive before your housing is ready. From 10,000 won for all-night access.",
    "GS25, CU, and 7-Eleven convenience stores let you pay with T-Money or card - no cash needed. They also have actual hot meals, not just snacks.",
    "Korean work-study culture: if you're working a part-time job (알바), be on time or early. Being late is a serious issue in Korean work culture, much more so than in many other cultures.",
]

def get_daily_tip(day_offset=0):
    """Get today's tip (or offset by days)"""
    day_num = datetime.now().toordinal() + day_offset
    return DAILY_TIPS[day_num % len(DAILY_TIPS)]

def format_daily_tip():
    tip = get_daily_tip()
    day_str = datetime.now().strftime("%A, %b %d")
    msg  = f"Korea Tip of the Day - {day_str}\n\n"
    msg += tip
    msg += "\n\nType /tip to get another tip anytime!"
    return msg


# ─────────────────────────────────────────────
# 6. ONBOARDING FLOW STATE MACHINE
# guides new users through setup step by step
# ─────────────────────────────────────────────

# stored per user: which step they're on
_onboarding_state = {}  # user_id -> {"step": int, "data": dict}

ONBOARDING_STEPS = [
    {
        "id": "arrival",
        "question": "When did you arrive in Korea (or when are you arriving)?\n\nType something like:\n- 'Already here'\n- 'September 2025'\n- '2025-09-01'\n- 'Next month'",
        "field": "arrival_date",
        "skip_if": None,
    },
    {
        "id": "university",
        "question": "Which university are you attending?\n\n(e.g., KAIST, SNU, Yonsei, POSTECH, Hanyang, Konkuk...)",
        "field": "university",
        "skip_if": None,
    },
    {
        "id": "city",
        "question": "Which city is your university in?\n\n(e.g., Seoul, Daejeon, Busan, Daegu, Incheon...)",
        "field": "city",
        "skip_if": None,
    },
    {
        "id": "diet",
        "question": "Do you have any diet restrictions?\n\nOptions:\n- halal\n- vegetarian\n- vegan\n- none\n- kosher\n\n(This helps me check food safety for you automatically)",
        "field": "diet",
        "skip_if": None,
    },
    {
        "id": "allergies",
        "question": "Do you have any food allergies?\n\nCommon ones: nuts, dairy, gluten, eggs, fish, shellfish, soy\n\nType them separated by commas, or 'none'",
        "field": "allergies",
        "skip_if": None,
    },
]

def start_onboarding(user_id):
    """Start the onboarding flow for a new user"""
    _onboarding_state[user_id] = {"step": 0, "data": {}}
    step = ONBOARDING_STEPS[0]
    msg  = "Welcome! Let me set up your profile so I can give you personalized help.\n\n"
    msg += "This takes about 1 minute. You can skip any question by typing 'skip'.\n\n"
    msg += f"Question 1 of {len(ONBOARDING_STEPS)}:\n{step['question']}"
    return msg

def is_in_onboarding(user_id):
    return user_id in _onboarding_state

def process_onboarding_answer(user_id, answer):
    """
    Process one onboarding answer, return (next_message, is_complete, collected_data)
    """
    if user_id not in _onboarding_state:
        return None, True, {}

    state = _onboarding_state[user_id]
    step_idx = state["step"]
    current_step = ONBOARDING_STEPS[step_idx]

    # save the answer
    field = current_step["field"]
    if answer.lower().strip() not in ("skip", "s", "-"):
        state["data"][field] = answer.strip()

    # move to next step
    state["step"] += 1

    if state["step"] >= len(ONBOARDING_STEPS):
        # complete!
        collected = state["data"]
        del _onboarding_state[user_id]
        return _format_onboarding_complete(collected), True, collected

    # show next question
    next_step = ONBOARDING_STEPS[state["step"]]
    progress  = state["step"] + 1
    msg = f"Got it!\n\nQuestion {progress} of {len(ONBOARDING_STEPS)}:\n{next_step['question']}"
    return msg, False, {}

def _format_onboarding_complete(data):
    university = data.get("university", "your university")
    city       = data.get("city", "your city")
    diet       = data.get("diet", "none")
    msg  = "Profile saved! Here's your setup:\n\n"
    if data.get("arrival_date"):   msg += f"Arrival: {data['arrival_date']}\n"
    if data.get("university"):     msg += f"University: {university}\n"
    if data.get("city"):           msg += f"City: {city}\n"
    if data.get("diet"):           msg += f"Diet: {diet}\n"
    if data.get("allergies") and data["allergies"].lower() != "none":
        msg += f"Allergies: {data['allergies']}\n"
    msg += "\nYou're all set! Now just describe any situation you're facing and I'll help.\n\n"
    msg += "Try:\n"
    msg += "- 'What should I do in my first week?'\n"
    msg += "- 'Is this food halal?'\n"
    msg += "- 'My landlord wants deposit before contract'\n"
    msg += "- /word for today's Korean word\n"
    msg += "- /schedule for your first week plan"
    return msg
