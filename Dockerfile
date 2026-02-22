# Co-founder Bot — Telegram бот для знакомств и поиска партнёров
# Сборка: docker build -t co-founder-bot .
# Запуск: docker run -d --name co-founder -e BOT_TOKEN=... -e ADMIN_ID=... co-founder-bot

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY . .

# По умолчанию — SQLite в /app/data (монтировать volume для сохранения БД)
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/cofounder.db

# Каталог для БД (при использовании volume данные сохраняются между перезапусками)
RUN mkdir -p /app/data

CMD ["python", "-m", "main"]
