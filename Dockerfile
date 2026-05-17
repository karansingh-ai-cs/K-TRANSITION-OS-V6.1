# Dockerfile — K-Transition OS v6.0 (Render)
# Single service: Telegram bot + Negotiator MiniApp (FastAPI)
# Bot runs polling in main thread, FastAPI runs in background thread on PORT

FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements first (Docker cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Render default port
EXPOSE 10000

# Single command runs both bot + negotiator
CMD ["python3", "bot.py"]
