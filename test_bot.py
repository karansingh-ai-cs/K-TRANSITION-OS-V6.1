#!/usr/bin/env python3
"""
test_bot.py — K-Transition OS Full Test Suite
Run: python test_bot.py
Tests ALL major systems without needing Telegram connection.
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime

# Fix Windows console encoding (cp1252 can't handle emoji)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("\n" + "="*60)
print("  K-Transition OS — System Test")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60 + "\n")

results = []

def test(name):
    def decorator(fn):
        async def wrapper():
            try:
                if asyncio.iscoroutinefunction(fn):
                    await fn()
                else:
                    fn()
                results.append((name, "PASS", ""))
                print(f"  [OK] {name}")
            except Exception as e:
                results.append((name, "FAIL", str(e)))
                print(f"  [FAIL] {name}")
                print(f"     -> {e}")
        return wrapper
    return decorator


# ── DB Tests ──────────────────────────────────────────────────

@test("DB: Connection (Turso or SQLite)")
def test_db_connection():
    from db import get_conn, get_backend
    backend = get_backend()
    print(f"\n     Backend: {backend}")
    with get_conn() as conn:
        conn.execute("SELECT 1")

@test("DB: Write and Read")
def test_db_write_read():
    from db import get_conn
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS _test_ktrans
                        (id INTEGER PRIMARY KEY, val TEXT)""")
        conn.execute("INSERT OR REPLACE INTO _test_ktrans (id, val) VALUES (?, ?)",
                     (999, "hello_turso"))
    with get_conn() as conn:
        row = conn.execute("SELECT val FROM _test_ktrans WHERE id = ?", (999,)).fetchone()
        assert row is not None, "Row not found after insert"
        assert row["val"] == "hello_turso", f"Wrong value: {row['val']}"
        conn.execute("DELETE FROM _test_ktrans WHERE id = ?", (999,))


# ── Config Tests ───────────────────────────────────────────────

@test("Config: Load")
def test_config():
    from config import GROQ_API_KEY, GEMINI_API_KEY
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is empty — set it in .env")

@test("Config: DATA_DIR and JSON files")
def test_data_files():
    from config import DATA_DIR
    required = ["food_rules.json", "housing_rules.json",
                "general_rules.json", "korean_lessons.json"]
    for f in required:
        path = DATA_DIR / f
        assert path.exists(), f"Missing: {path}"


# ── Memory Tests ───────────────────────────────────────────────

@test("Memory: Setup DB tables")
def test_memory_setup():
    from memory import setup
    setup()  # should not raise

@test("Memory: Create and get user")
def test_memory_user():
    from memory import get_or_create_user, get_user
    user = get_or_create_user(99999999, "testuser", "TestBot")
    assert user is not None
    assert user["user_id"] == 99999999

@test("Memory: Save and retrieve chat history")
def test_memory_history():
    from memory import save_message, get_history, clear_history
    uid = 99999999
    clear_history(uid)
    save_message(uid, "user", "test message 1")
    save_message(uid, "assistant", "test reply 1")
    hist = get_history(uid)
    assert len(hist) == 2
    assert hist[0]["content"] == "test message 1"
    clear_history(uid)

@test("Memory: XP and progress")
def test_memory_progress():
    from level_system import setup_level_tables, add_xp, get_user_level
    setup_level_tables()  # Ensure table exists before test
    result = add_xp(99999999, 50, "test")
    assert result["new_xp"] >= 50


# ── State Manager Tests ────────────────────────────────────────

@test("State: Set and get state")
def test_state_basic():
    from state_manager import set_state, get_state, clear_state, State
    uid = 88888888
    set_state(uid, State.BUDDY_ACTIVE, {"history": []})
    assert get_state(uid) == State.BUDDY_ACTIVE
    clear_state(uid)
    assert get_state(uid) == State.IDLE

@test("State: Context update persists")
def test_state_context():
    from state_manager import set_state, get_state, get_context, update_context, clear_state, State
    uid = 77777777
    set_state(uid, State.PRACTICE_ACTIVE, {"scenario": "food", "level": 2})
    update_context(uid, level=3)
    ctx = get_context(uid)
    assert ctx["level"] == 3
    assert ctx["scenario"] == "food"
    clear_state(uid)


# ── AI Tests ───────────────────────────────────────────────────

@test("AI: Groq connection")
async def test_groq():
    from ai_brain import call_groq
    resp = call_groq(
        [{"role": "user", "content": "Say exactly: CONNECTED"}],
        system_prompt="You are a test bot. Reply with one word only."
    )
    assert resp is not None, "Groq returned None — check GROQ_API_KEY"
    print(f"\n     Groq reply: {resp[:50]}")

@test("AI: Full ask_ai pipeline")
async def test_ask_ai():
    from ai_brain import ask_ai
    resp, provider = ask_ai("What is T-Money card in Korea?")
    assert resp is not None, "ask_ai returned None"
    assert provider in ("groq", "gemini"), f"Unknown provider: {provider}"
    print(f"\n     Provider: {provider} | Reply: {resp[:60]}...")

@test("AI: Quiz generation")
async def test_quiz_gen():
    from ai_brain import generate_quiz_question
    q = generate_quiz_question(level=1, category="daily life")
    if q is None:
        print("\n     (Quiz gen returned None — Groq may be rate limited, OK)")
        return
    assert "korean" in q
    assert "correct_meaning" in q
    assert len(q.get("wrong_answers", [])) >= 3


# ── Buddy Mode Tests ───────────────────────────────────────────

@test("Buddy: Human-like response (no AI/bot language)")
async def test_buddy_human():
    from buddy_mode import chat_with_buddy
    user_info = {
        "user_id": 99999999,
        "first_name": "Test",
        "university": "KAIST",
        "city": "Daejeon",
        "arrival_date": "2024-09-01"
    }
    resp = await chat_with_buddy("hey what's up", user_info, [])
    assert resp is not None
    # Check it doesn't sound like an AI
    robot_phrases = ["as an ai", "i'd be happy to help",
                     "certainly!", "of course!", "i am an ai"]
    for phrase in robot_phrases:
        assert phrase not in resp.lower(), f"AI-sounding phrase detected: '{phrase}'"
    print(f"\n     Minsu says: {resp[:80]}")


# ── Risk Detector Tests ────────────────────────────────────────

@test("Risk: Crisis detection")
def test_crisis_detect():
    from risk_detector import scan_message
    result = scan_message("I want to kill myself", {})
    assert result["is_crisis"] == True

@test("Risk: Scam detection")
def test_scam_detect():
    from risk_detector import scan_message
    result = scan_message("landlord wants deposit without contract", {})
    assert result["is_scam"] == True

@test("Risk: Halal detection")
def test_halal_detect():
    from risk_detector import scan_message
    result = scan_message("Is this 삼겹살 okay to eat?", {"diet": "halal"})
    assert result["is_haram"] == True


# ── Korean Teacher Tests ───────────────────────────────────────

@test("Korean: Word of the day")
def test_word_of_day():
    from korean_teacher import get_word_of_the_day, format_word_of_day
    word = get_word_of_the_day()
    assert word is not None
    assert "korean" in word
    formatted = format_word_of_day(word)
    assert len(formatted) > 20

@test("Korean: Static quiz question")
def test_static_quiz():
    from korean_teacher import get_static_quiz_question, build_quiz_options
    q = get_static_quiz_question()
    if q is None:
        return  # empty pool — OK
    opts, correct_idx = build_quiz_options(q)
    assert len(opts) == 4
    assert 0 <= correct_idx <= 3


@test("Korean: Dictionary search")
def test_korean_search():
    from korean_teacher import search_vocab_and_phrases
    res = search_vocab_and_phrases("hospital")
    assert "병원" in res or "hospital" in res.lower()
    res2 = search_vocab_and_phrases("hello")
    assert "안녕" in res2 or "hello" in res2.lower()


@test("Tracker: Advanced notes and deletion")
def test_tracker_advanced():
    from smart_tracker import create_tracker, log_entry, get_tracker_stats, delete_tracker, get_user_trackers
    user_id = 11223344
    tid = create_tracker(user_id, "test_exp", "💸", "₩")
    log_entry(user_id, tid, 5000, "bought snack")
    stats = get_tracker_stats(tid)
    assert stats["count"] == 1
    assert stats["total"] == 5000
    delete_tracker(user_id, tid)
    active = get_user_trackers(user_id)
    assert not any(t["id"] == tid for t in active)


# ── Other Module Tests ─────────────────────────────────────────

@test("Schedule: First week checklist")
def test_schedule():
    from schedule_maker import get_first_week_checklist
    result = get_first_week_checklist({"diet": "halal", "city": "Seoul"})
    assert "Week" in result or "Day" in result

@test("Visa: Status calculation")
def test_visa():
    from visa_radar import get_visa_status, format_visa_status
    data = get_visa_status("2024-09-01")
    assert data is not None
    assert "days_in" in data
    formatted = format_visa_status(data)
    assert "Radar" in formatted

@test("Maps: Korean translation")
def test_maps():
    from maps_helper import translate_to_korean, format_map_response
    kr = translate_to_korean("pharmacy")
    assert kr == "약국", f"Expected 약국, got {kr}"
    response = format_map_response("halal restaurant", "Seoul")
    assert "naver" in response.lower() or "Naver" in response

@test("Exchange: Rate fetch")
def test_exchange():
    from differentiator import get_exchange_rates
    rates = get_exchange_rates()
    if rates is None:
        print("\n     (Rate API unavailable — network issue, OK)")
        return
    assert "USD" in rates or "INR" in rates

@test("SOS: Emergency format")
def test_sos():
    from sos_mode import format_sos_general, format_sos_guide
    general = format_sos_general()
    assert "112" in general
    assert "119" in general
    guide = format_sos_guide("sick")
    assert "119" in guide or "emergency" in guide.lower()

@test("DormChef: Recipe generation")
async def test_dormchef():
    from dormchef import get_chef_recipe
    resp = await get_chef_recipe("I have eggs and instant noodles", "none", "none")
    assert resp is not None
    assert len(resp) > 50

@test("Intent Router: Basic routing")
async def test_intent():
    from intent_router import route_intent
    result = await route_intent("find nearest pharmacy", {"city": "Seoul"})
    assert result["intent"] in ("map", "general_question"), f"Got: {result['intent']}"
    result2 = await route_intent("I have eggs and cheese what can I cook", {})
    assert result2["intent"] == "cook", f"Got: {result2['intent']}"


# ── Run All Tests ──────────────────────────────────────────────

async def main():
    tests = [
        test_db_connection,
        test_db_write_read,
        test_config,
        test_data_files,
        test_memory_setup,
        test_memory_user,
        test_memory_history,
        test_memory_progress,
        test_state_basic,
        test_state_context,
        test_groq,
        test_ask_ai,
        test_quiz_gen,
        test_buddy_human,
        test_crisis_detect,
        test_scam_detect,
        test_halal_detect,
        test_word_of_day,
        test_static_quiz,
        test_korean_search,
        test_tracker_advanced,
        test_schedule,
        test_visa,
        test_maps,
        test_exchange,
        test_sos,
        test_dormchef,
        test_intent,
    ]

    print("Running tests...\n")
    for t in tests:
        await t()

    print("\n" + "="*60)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"  Results: {passed} passed, {failed} failed out of {len(results)} tests")

    if failed > 0:
        print("\n  Failed tests:")
        for name, status, err in results:
            if status == "FAIL":
                print(f"    * {name}: {err}")

    print("="*60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n  All tests passed! Bot is ready to run.\n")
        print("  Start bot:  python bot.py")
        print("  Start voice assistant:  cd negotiator2 && uvicorn main:app --reload\n")


if __name__ == "__main__":
    asyncio.run(main())
