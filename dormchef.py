# dormchef.py — K-Transition OS v5.0
# AI-powered cooking assistant for dorm students
# Uses only CU/GS25/7-Eleven ingredients + microwave/kettle
# Automatically respects user's diet/allergy profile

import asyncio
import logging

logger = logging.getLogger(__name__)

DORM_CHEF_PROMPT = """You are 'Dorm-Chef 🧑‍🍳', a legendary Korean university student who survived 4 years 
making 5-star meals using ONLY a microwave, a kettle, and cheap convenience store ingredients.

USER'S HEALTH & DIET PROFILE:
- Diet: {user_diet}
- Allergies: {user_allergies}
- Budget level: Student (under 10,000 won per meal ideally)

CRITICAL DIETARY RULES — NEVER VIOLATE:
- If diet is halal: NEVER suggest pork (돼지고기), alcohol-based sauces (mirin/미림/청주), or lard. 
  Warn about hidden pork broth in ramyeon (many Korean ramyeon use pork-based soup base).
  Suggest 쇠고기 (beef) or 닭고기 (chicken) alternatives.
  Detailed halal rules: {haram_rules}
- If vegetarian/vegan: No meat, no fish sauce (액젓), no dairy, no eggs, warn about anchovy stock (멸치 육수) in Korean soups.
  Suggest 콩 (bean) and 두부 (tofu) based items from convenience stores.
  Detailed vegan rules: {vegan_rules}
- If allergies listed: Warn EXPLICITLY if any ingredient could contain that allergen.
  Korean labels: 견과류(nuts), 유제품(dairy), 글루텐(gluten), 계란(eggs), 생선(fish), 갑각류(shellfish), 대두(soy)

YOUR COOKING RULES:
1. DORM ROOM ONLY — microwave, electric kettle, chopsticks, bowl, cup. NO stove, NO oven, NO pan.
2. Ingredients MUST be buyable at CU (씨유), GS25, 7-Eleven, or Emart24 convenience stores.
3. Keep total cost under ₩5,000 ideally. Mention estimated cost.
4. Fun, energetic Chef personality. Start with "🧑‍🍳 BAM! Let's cook!"
5. Give numbered step-by-step recipe. Max 6 steps. Simple language.
6. Include the Korean name of each ingredient (so user can find it in the store).
7. End with estimated total cost in ₩ won.
8. If user mentions a specific ingredient, build the recipe around THAT.
9. Suggest a "Chef's Upgrade" — one extra item that makes it 10x better.

CONVENIENCE STORE INVENTORY YOU KNOW EXISTS:
- 즉석밥 (instant rice packs) ~₩1,500
- 참치캔 (canned tuna) ~₩2,000  
- 스팸 (spam) ~₩3,000 [NOT HALAL — contains pork]
- 라면/컵라면 (ramen/cup noodle) ~₩1,000-1,500
- 계란 (eggs, usually sold in 2-pack) ~₩1,500
- 김 (roasted seaweed) ~₩1,000
- 치즈 (processed cheese slices) ~₩2,000
- 삼각김밥 (triangle kimbap) ~₩1,200
- 떡볶이 컵 (cup tteokbokki) ~₩1,800
- 카레 레토르트 (instant curry pouch) ~₩2,000
- 마요네즈 (mayonnaise) ~₩1,500
- 식빵 (white bread) ~₩1,500
- 우유 (milk) ~₩1,500
- 바나나 (banana) ~₩1,500
- 요거트 (yogurt) ~₩1,000
- 두유 (soy milk) ~₩1,000
"""

QUICK_RECIPES = {
    "ramen":     "I have shin ramen (신라면) and want to make it restaurant-quality. What can I add from a Korean convenience store?",
    "midnight":  "It's 2AM, I'm starving, the nearest CU is 2 min walk. What's the cheapest filling combo I can buy and eat?",
    "healthy":   "I want something somewhat healthy and filling that I can make in my dorm with convenience store stuff.",
    "egg":       "I have eggs and whatever basic stuff is in my dorm. What can I make with just a microwave?",
    "nocook":    "I'm too exhausted to cook anything. What's the best ready-to-eat combo meal from a Korean convenience store under ₩5,000?",
    "breakfast": "Quick Korean-style breakfast I can make in 5 minutes in my dorm room?",
    "fancy":     "I want to impress my Korean friend with something that looks fancy but is actually made from convenience store food.",
    "protein":   "I need high protein meals from convenience store ingredients for gym/working out.",
    "sweet":     "I'm craving something sweet. What dessert can I make in a microwave with convenience store ingredients?",
    "budget":    "What's the absolute cheapest filling meal I can make? Under ₩2,000 total.",
}

EQUIPMENT_GUIDE = """🛒 Dorm Kitchen Starter Kit (All from Daiso/다이소 — each ₩1,000-₃,000)

Essential (₩8,000 total):
1. 전자레인지용 그릇 — Microwave-safe bowl (₩2,000)
2. 젓가락 + 숟가락 — Chopsticks + spoon set (₩1,000)
3. 컵 — Large mug for cup noodles (₩1,000)
4. 가위 — Kitchen scissors (₩2,000) — Koreans use these instead of knives!
5. 랩 — Plastic wrap for microwave (₩1,000)
6. 밀폐용기 — Storage container (₩1,000)

Nice to have (₩5,000 more):
7. 전기포트 — Electric kettle if dorm doesn't have one (₩5,000 at Daiso/Coupang)

Pro tip: Check your dorm's common kitchen first — many have shared microwave, kettle, and basic utensils!
Buy on Coupang for even cheaper delivery: search '자취 필수템'
"""


async def get_chef_recipe(ingredients_text, diet="none", allergies="none"):
    """Gets a dorm recipe from Groq with diet-aware system prompt."""
    from ai_brain import call_groq

    import json
    import os
    from config import DATA_DIR

    with open(os.path.join(DATA_DIR, "food_rules.json"), "r", encoding="utf-8") as f:
        food_rules = json.load(f)["rules"]

    haram_rules = "\n  - ".join([rule["problem"] + " -> " + " ".join(rule["action"]) for rule in food_rules if "halal" in " ".join(rule["action"]).lower() or "halal" in rule["problem"].lower()])
    vegan_rules = "\n  - ".join([rule["problem"] + " -> " + " ".join(rule["action"]) for rule in food_rules if "vegetarian" in rule["problem"].lower() or "vegan" in rule["problem"].lower()])

    formatted_system = DORM_CHEF_PROMPT.format(
        user_diet=diet if diet else "none",
        user_allergies=allergies if allergies else "none",
        haram_rules=haram_rules,
        vegan_rules=vegan_rules
    )

    messages = [
        {"role": "user", "content": f"Hey Chef! I have these ingredients/cravings: {ingredients_text}. What can I make in my Korean dorm room?"}
    ]

    try:
        response = await asyncio.to_thread(call_groq, messages, formatted_system)
        if response:
            return response
    except Exception as e:
        logger.error(f"Dorm-Chef failed: {e}")

    return (
        "🧑‍🍳 Oops! My microwave just short-circuited. Try again in a sec!\n\n"
        "While I fix it, here's a quick one:\n"
        "즉석밥 + 참치캔 + 김 + 마요 = instant rice + tuna + seaweed + mayo\n"
        "Microwave rice 2 min → mix tuna + mayo → top with 김\n"
        "Total: ~₩3,500. Trust me, it slaps. 🔥"
    )


async def get_quick_recipe(recipe_key, diet="none", allergies="none"):
    """Get a specific quick recipe by key."""
    prompt = QUICK_RECIPES.get(recipe_key)
    if not prompt:
        prompt = f"Suggest a quick dorm recipe for: {recipe_key}"
    return await get_chef_recipe(prompt, diet, allergies)


def get_equipment_guide():
    """Return the Daiso equipment guide."""
    return EQUIPMENT_GUIDE


def get_recipe_categories():
    """Return available quick recipe categories."""
    categories = {
        "🍜 ramen": "Ramen upgrade hacks",
        "🌙 midnight": "Late night emergency meals",
        "🥗 healthy": "Healthy-ish options",
        "🥚 egg": "Egg-based recipes",
        "😴 nocook": "Zero-effort combos",
        "☀️ breakfast": "Quick morning meals",
        "✨ fancy": "Impress your friends",
        "💪 protein": "High protein meals",
        "🍰 sweet": "Sweet treats",
        "💰 budget": "Under ₩2,000 meals",
    }
    msg = "🧑‍🍳 DormChef — Quick Recipe Menu\n\n"
    for key, desc in categories.items():
        cmd_key = key.split(" ")[1]
        msg += f"{key}: /cook {cmd_key}\n"
    msg += "\n🛒 /cook equipment — What to buy from Daiso\n"
    msg += "🍳 /cook [anything] — Tell me what you have!\n"
    msg += "\nExample: /cook I have eggs and cheese"
    return msg
