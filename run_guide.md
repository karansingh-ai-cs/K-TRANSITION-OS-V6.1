# K-Transition OS — How to Run

## 1. First Time Setup

### Install dependencies
```bash
pip install -r requirements.txt
```

### Setup Turso (free cloud database)
1. Go to turso.tech → Sign up (use GitHub)
2. Install Turso CLI: `curl -sSfL https://get.tur.so/install.sh | bash`
3. Login: `turso auth login`
4. Create DB: `turso db create k-transition-os`
5. Get URL: `turso db show k-transition-os --url`
6. Get token: `turso db tokens create k-transition-os`
7. Add to `.env`:
   ```
   TURSO_URL=libsql://k-transition-os-xxxx.turso.io
   TURSO_TOKEN=your-token-here
   ```

### OR: Skip Turso (use local SQLite for testing)
Just leave `TURSO_URL` and `TURSO_TOKEN` blank in `.env`
Bot will use `ktransition.db` locally.

### Setup .env
```
TELEGRAM_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
TURSO_URL=libsql://...
TURSO_TOKEN=...
```

## 2. Test Everything First
```bash
python test_bot.py
```
All 26 tests should pass. Fix any failures before running the bot.

## 3. Run the Telegram Bot
```bash
python bot.py
```

## 4. Run the Voice Assistant (separate process)
```bash
cd negotiator
pip install -r ../requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```
Open: http://localhost:7860

## 5. Run Both Together (production)
Terminal 1: `python bot.py`
Terminal 2: `cd negotiator && uvicorn main:app --port 7860`

## 6. Common Issues

### "libsql_experimental not found"
```bash
pip install libsql-experimental
```

### "GROQ_API_KEY is empty"
Get free key at: console.groq.com

### "data/food_rules.json not found"
Make sure `data/` folder exists with all 4 JSON files.
If files are in root, either move them to `data/` or update `config.py`:
```python
DATA_DIR = BASE_DIR  # if JSON files are in root
```

### Bot not responding
Check TELEGRAM_TOKEN is correct and uncommented in .env

### Turso connection fails
Check URL format: must start with `libsql://` not `https://`
