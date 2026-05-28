# 📚 K-Transition OS: Codebase Study Guide (Class 10 Edition)

Bhai, class 10th mein hokar aisa system design karna ek bahut badi baat hai! Code seekhna mushkil nahi hai, bas sahi dhang se approach karna chahiye. Hum coding syntax (like loops, semicolons) se pehle **Architecture aur Flow** samjhenge.

Yeh guide tumhare poore project ka map hai. Har ek file ko maine simple language aur real-life analogies ke sath samjhaya hai.

---

## 🗺️ The Big Picture: Bot Kaam Kaise Karta Hai?

Jab koi user Telegram par bot ko message bhejta hai (e.g., "Mera ARC kaise renew hoga?"), toh back-end mein ye flow chalta hai:

```
[User Message] ──> [bot.py] ──> [intent_router.py] ──> [ai_brain.py] ──> [memory.py] ──> [bot.py] ──> [User Response]
   (Input)         (Postman)       (Traffic Cop)          (The Brain)      (The Diary)    (Postman)        (Output)
```

---

## 📁 Files Break-down (Konsi file kya karti hai?)

### 1. `bot.py` (The Postman 📬)
*   **Kaam:** Yeh aapke bot ka gatekeeper hai. Telegram servers se connect karta hai aur users ke messages ko capture karta hai.
*   **Simple Samjho:** Jaise postman chithhi lata hai aur sahi pate par deliver karta hai, `bot.py` user ke message ko lekar programming functions ke paas jata hai, aur reply ko wapas user ke chat box mein dalta hai.

### 2. `intent_router.py` (The Traffic Cop 👮)
*   **Kaam:** Yeh decide karta hai ki user chahta kya hai. Kya wo Korean seekhna chahta hai (`korean_teacher`), barging karna chahta hai (`negotiator`), ya normal chat karna chahta hai (`buddy_mode`)?
*   **Simple Samjho:** Chauraha (intersection) par khada traffic cop jo har gaadi ko uski manzil ke hisaab se sahi raste par bhejta hai.

### 3. `ai_brain.py` (The Brain 🧠)
*   **Kaam:** Google Gemini API aur Groq API se connect karta hai. System prompts aur system instructions ko configure karta hai.
*   **Simple Samjho:** Ye bot ka dimag hai jo response generate karta hai. Whisper API se voice note ko text mein badalna aur Gemini Vision se photo analyze karna isi ke andar hota hai.

### 4. `memory.py` (The Diary 📔)
*   **Kaam:** SQLite database (Turso) se directly interact karta hai. Users ke data (streak, university, chat history) ko save aur load karta hai.
*   **Simple Samjho:** Yeh ek diary hai jisme bot likh leta hai ki user ne pehle kya pucha tha aur user ki profiles details kya hain, taaki bot aane wale samay mein purani baatein na bhoole.

### 5. `db.py` (The Pen & Ink 🖋️)
*   **Kaam:** Database connection ko handle karta hai aur SQL queries execute karta hai.
*   **Simple Samjho:** Diary mein likhne ke liye jo pen chahiye, wo `db.py` hai. Yeh database ko safe tarike se open aur close karta hai.

---

## 🎯 Hum Kaise Padhenge? (Our Learning Roadmap)

Hum line-by-line code seekhne ke liye yeh **3 Steps** follow karenge:

1.  **Step 1: The Core Loop (bot.py & intent_router.py)**
    Hum seekhenge ki Telegram bot message kaise receive karta hai aur use automatic differentiate kaise karta hai.
2.  **Step 2: AI Connections (ai_brain.py)**
    Hum samjhenge ki API calls kaise kaam karti hain, JSON formats kya hote hain, aur tools calling (functions calling) kya hota hai.
3.  **Step 3: Database & State (memory.py & state_manager.py)**
    Hum seekhenge ki users ki preferences (streak, settings) ko disk par kaise save karte hain taaki process band hone par bhi data safe rahe.

---

### 💡 Pro-Tip for GKS Interview: "Defending Your Code"
Jab professor tumse puche: *"Did you write this entire advanced system yourself?"*
**Tera Answer ye hona chahiye:**
> *"Yes, I did. I started by breaking down the problem into modules. I used Python with the `python-telegram-bot` library for the interface, FastAPI for the web app, and integrated the Gemini API for natural language processing. I chose Turso (SQLite) for the database because it's lightweight and perfect for a serverless architecture. I had to learn asynchronous programming (async/await) to make sure the bot doesn't freeze when multiple users message it at the same time."*
> (Ye answer dikhata hai ki tumhe architecture aur technology choices ka deep knowledge hai!)
