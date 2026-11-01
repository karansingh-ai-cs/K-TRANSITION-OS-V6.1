# sos_mode.py — K-Transition OS v5.0
# KILLER FEATURE: One-tap emergency system for international students
# Instant access to help for ANY emergency situation in Korea
# Provides location-aware phrases, emergency numbers, step-by-step guides

import logging

logger = logging.getLogger(__name__)

# ── Emergency Phrases (Korean + Romanization + English) ──────────────────────

EMERGENCY_PHRASES = {
    "general": [
        ("도와주세요!", "do-wa-ju-se-yo!", "Help me!"),
        ("영어 할 수 있는 사람 있어요?", "yeong-eo hal su it-neun sa-ram it-seo-yo?", "Is there anyone who speaks English?"),
        ("경찰 불러주세요", "gyeong-chal bul-leo-ju-se-yo", "Please call the police"),
        ("구급차 불러주세요", "gu-geup-cha bul-leo-ju-se-yo", "Please call an ambulance"),
        ("영어 통역사 불러주세요", "yeong-eo tong-yeok-sa bul-leo-ju-se-yo", "Please call an English interpreter"),
    ],
    "lost": [
        ("길을 잃었어요", "gi-reul ir-eot-seo-yo", "I'm lost"),
        ("여기가 어디예요?", "yeo-gi-ga eo-di-ye-yo?", "Where am I?"),
        ("이 주소로 가고 싶어요", "i ju-so-ro ga-go si-peo-yo", "I want to go to this address"),
        ("지하철역이 어디예요?", "ji-ha-cheol-yeo-gi eo-di-ye-yo?", "Where is the subway station?"),
        ("택시 불러주세요", "taek-si bul-leo-ju-se-yo", "Please call a taxi"),
        ("카카오맵을 보여주세요", "ka-ka-o-maep-eul bo-yeo-ju-se-yo", "Let me show you Kakao Map"),
    ],
    "sick": [
        ("아파요", "a-pa-yo", "I'm sick / It hurts"),
        ("열이 나요", "yeol-i na-yo", "I have a fever"),
        ("머리가 아파요", "meo-ri-ga a-pa-yo", "I have a headache"),
        ("배가 아파요", "bae-ga a-pa-yo", "I have a stomachache"),
        ("약국이 어디예요?", "yak-gu-gi eo-di-ye-yo?", "Where is the pharmacy?"),
        ("병원에 가야 해요", "byeong-wo-ne ga-ya hae-yo", "I need to go to the hospital"),
        ("알레르기가 있어요", "al-le-reu-gi-ga it-seo-yo", "I have allergies"),
        ("보험증 있어요", "bo-heom-jeung it-seo-yo", "I have insurance"),
    ],
    "scam": [
        ("사기 같아요", "sa-gi ga-ta-yo", "I think it's a scam"),
        ("돈을 돌려주세요", "do-neul dol-lyeo-ju-se-yo", "Give me my money back"),
        ("경찰에 신고할 거예요", "gyeong-cha-re sin-go-hal geo-ye-yo", "I will report to the police"),
        ("증거가 있어요", "jeung-geo-ga it-seo-yo", "I have evidence"),
        ("외국인 도움센터에 전화할 거예요", "oe-gu-gin do-um-sen-teo-e jeon-hwa-hal geo-ye-yo", "I will call the foreigner help center"),
    ],
    "accident": [
        ("교통사고가 났어요", "gyo-tong-sa-go-ga na-sseo-yo", "There was a traffic accident"),
        ("다쳤어요", "da-chyeo-sseo-yo", "I'm injured"),
        ("피가 나요", "pi-ga na-yo", "I'm bleeding"),
        ("움직일 수 없어요", "um-ji-gil su eop-seo-yo", "I can't move"),
        ("목격자가 필요해요", "mok-gyeok-ja-ga pil-yo-hae-yo", "I need witnesses"),
    ],
    "harassment": [
        ("그만하세요", "geu-man-ha-se-yo", "Stop it"),
        ("만지지 마세요", "man-ji-ji ma-se-yo", "Don't touch me"),
        ("경찰 부를 거예요", "gyeong-chal bu-reul geo-ye-yo", "I will call the police"),
        ("CCTV 있어요", "CCTV it-seo-yo", "There is CCTV here"),
        ("도와주세요! 이 사람이 괴롭혀요", "do-wa-ju-se-yo! i sa-ra-mi goe-ro-pyeo-yo", "Help! This person is harassing me"),
    ],
}

# ── Emergency Response Guides ────────────────────────────────────────────────

SOS_GUIDES = {
    "lost": {
        "title": "🗺️ I'm Lost — Survival Kit",
        "steps": [
            "📍 Open Kakao Map (카카오맵) or Naver Map to see your location",
            "📍 Look for subway station signs (지하철) — they're usually bilingual",
            "📍 Find any convenience store (CU/GS25/7-Eleven) — staff can help",
            "📍 Show your destination on your phone screen to anyone for directions",
            "📱 Call 1345 (Foreigner Helpline) — they speak your language 24/7",
            "🚖 Use Kakao T app to call a taxi with destination already set",
        ],
        "pro_tip": "💡 Take a photo of your dorm/university address in Korean. Show it to taxi drivers. Save your dorm address in Kakao Map as a favorite!",
    },
    "sick": {
        "title": "🏥 I'm Sick — What To Do",
        "steps": [
            "🏫 If mild: Go to your university health center (보건센터) — usually free!",
            "💊 For OTC medicine: Go to 약국 (pharmacy) — no prescription needed for basics",
            "🏥 For serious: Go to nearest 응급실 (emergency room) or call 119",
            "📞 Call 1345 for help communicating with medical staff in your language",
            "💳 Bring: passport, ARC, insurance card (if you have one)",
            "🧾 Keep ALL receipts — your NHIS or private insurance will reimburse",
        ],
        "pharmacy_items": {
            "Headache/Pain": "타이레놀 (Tylenol) or 이부프로펜 (Ibuprofen) — ₩3,000-5,000",
            "Cold/Flu": "판콜에이 (Pankol-A) — ₩5,000-8,000",
            "Stomach": "겔포스 (Gelfos) antacid or 정로환 (Jeongrowhan) — ₩3,000-6,000",
            "Fever": "타이레놀 ER (Tylenol ER) — ₩5,000",
            "Allergies": "지르텍 (Zyrtec) or 클라리틴 (Claritin) — ₩5,000-8,000",
            "Bandages": "밴드 (band-aid) — ₩1,000-2,000",
        },
        "pro_tip": "💡 University 보건센터 is almost always FREE and has English-speaking staff. GO THERE FIRST for non-emergencies!",
    },
    "scam": {
        "title": "🚨 Scam Response Protocol",
        "steps": [
            "🛑 STOP all communication with the scammer immediately",
            "📸 Screenshot EVERYTHING: messages, transfers, profiles, phone numbers",
            "📞 Call 182 (Cyber Crime Unit) — they handle online scams",
            "📞 Call 1345 (Foreigner Helpline) for guidance in your language",
            "🏦 Contact your bank IMMEDIATELY if money was sent — request freeze",
            "🚔 File a report at the nearest 경찰서 (police station) — bring all evidence",
            "📋 Report online at ecrm.police.go.kr (Korean Internet Crime Center)",
        ],
        "common_scams": [
            "🔴 Deposit before contract signed → ALWAYS refuse",
            "🔴 'Lucky' messages asking to click links → phishing",
            "🔴 Job offers that need upfront 'registration fee' → scam",
            "🔴 Online purchases with only bank transfer (no escrow) → risky",
            "🔴 Fake 'immigration officer' calls threatening deportation → hang up, call 1345",
            "🔴 KakaoTalk messages from 'friends' asking for money → verify by phone call first",
        ],
        "pro_tip": "💡 In Korea, 에스크로 (escrow) services exist on sites like 당근마켓. NEVER transfer money directly to strangers!",
    },
    "accident": {
        "title": "🚗 Accident Response",
        "steps": [
            "🆘 Call 119 (ambulance + fire) immediately if anyone is injured",
            "📸 Take photos of: the scene, license plates, your injuries, surroundings",
            "🚔 Call 112 (police) to file an official accident report",
            "📋 Get the other person's: name, phone, insurance company, license plate",
            "🏥 Go to hospital even if you feel fine — some injuries appear later",
            "📞 Call 1345 for help communicating with police/hospital",
            "🧾 Keep ALL hospital receipts for insurance claim",
        ],
        "pro_tip": "💡 Korea has dashcam culture — nearby cars/buildings may have footage. Ask police to check CCTV!",
    },
    "harassment": {
        "title": "🛡️ Harassment Response",
        "steps": [
            "🏃 Move to a crowded area or a store/restaurant immediately",
            "📸 If safe: take photo/video of the person",
            "📞 Call 112 (police) — say 'English please'",
            "📞 Or call 1366 (Women's Emergency Hotline) for gender-based harassment",
            "📍 Note the location, time, and any CCTV cameras nearby",
            "🚔 File a report at 경찰서 — bring your ARC/passport",
        ],
        "pro_tip": "💡 Sexual harassment is taken seriously in Korea (성범죄). Police WILL investigate. Don't hesitate to report!",
    },
}


def format_sos_general():
    """Format the main SOS quick reference card."""
    return (
        "🆘 SOS — Emergency Quick Access\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📞 119 — Ambulance + Fire\n"
        "📞 112 — Police (say 'English please')\n"
        "📞 1345 — Foreigner Help (24/7, your language)\n"
        "📞 109 — Crisis/Suicide Line (24/7, free)\n"
        "📞 182 — Cyber Crime\n"
        "📞 1366 — Women's Emergency\n\n"
        "🚨 What's your emergency?\n\n"
        "/sos lost — I'm lost\n"
        "/sos sick — I'm sick/hurt\n"
        "/sos scam — I got scammed\n"
        "/sos accident — Traffic accident\n"
        "/sos harassment — Being harassed\n"
        "/sos phrases — Emergency Korean phrases\n\n"
        "💡 Key phrase: 도와주세요! (do-wa-ju-se-yo) = HELP ME!"
    )


def format_sos_guide(situation):
    """Format a specific SOS guide."""
    guide = SOS_GUIDES.get(situation)
    if not guide:
        return format_sos_general()

    msg = f"{guide['title']}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    msg += "📋 Step by Step:\n\n"
    for step in guide["steps"]:
        msg += f"{step}\n\n"

    # Extra info for specific situations
    if situation == "sick" and "pharmacy_items" in guide:
        msg += "💊 Common Pharmacy Items:\n"
        for item, desc in guide["pharmacy_items"].items():
            msg += f"  • {item}: {desc}\n"
        msg += "\n"

    if situation == "scam" and "common_scams" in guide:
        msg += "⚠️ Common Scams in Korea:\n"
        for scam in guide["common_scams"]:
            msg += f"{scam}\n"
        msg += "\n"

    msg += f"\n{guide.get('pro_tip', '')}\n\n"

    # Add relevant phrases
    phrases = EMERGENCY_PHRASES.get(situation, EMERGENCY_PHRASES["general"])
    msg += "🗣️ Say This:\n"
    for kr, roman, eng in phrases[:5]:
        msg += f"  {kr}\n  ({roman})\n  = {eng}\n\n"

    return msg


def format_sos_phrases(situation=None):
    """Format emergency phrases for a situation or all."""
    if situation and situation in EMERGENCY_PHRASES:
        phrases = EMERGENCY_PHRASES[situation]
        msg = f"🗣️ Emergency Phrases — {situation.title()}\n\n"
    else:
        msg = "🗣️ Emergency Korean Phrases\n\n"
        phrases = EMERGENCY_PHRASES["general"]

    for kr, roman, eng in phrases:
        msg += f"🇰🇷 {kr}\n🔤 {roman}\n🇬🇧 {eng}\n\n"

    msg += "━━━━━━━━━━━━━\n"
    msg += "📞 Can't speak? Show your phone screen to someone!\n"
    msg += "📞 1345 = Foreigner helpline (they translate for you)"

    return msg
