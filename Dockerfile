# Dockerfile — K-Transition OS (Hugging Face Spaces)
# Bot khud port 7860 par keep-alive server chalata hai
# Bahar se koi extra server ki zaroorat nahi

FROM python:3.10-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements pehle copy karo (Docker cache ke liye)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Saara code copy karo
COPY . .

# Port 7860 — Hugging Face yahi expect karta hai
EXPOSE 7860

# Sirf bot chalao — keep-alive server bot.py ke andar hai
CMD ["python3", "bot.py"]
