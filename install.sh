#!/bin/bash
# Скрипт для установки зависимостей проекта Co-founder Bot

set -e  # Остановка при ошибке

echo "🚀 Установка зависимостей для Co-founder Bot"
echo ""

# Проверка виртуального окружения
if [ ! -d ".venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаю..."
    python3.12 -m venv .venv
    echo "✅ Виртуальное окружение создано"
fi

# Активация виртуального окружения
echo "📦 Активирую виртуальное окружение..."
source .venv/bin/activate

# Проверка версии Python
PYTHON_VERSION=$(python --version)
echo "🐍 Используется: $PYTHON_VERSION"
echo ""

# Обновление pip
echo "⬆️  Обновляю pip, setuptools и wheel..."
pip install --upgrade pip setuptools wheel

# Установка зависимостей
echo ""
echo "📚 Устанавливаю зависимости из requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Все зависимости установлены успешно!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Создайте файл .env на основе .env.example"
echo "   2. Заполните BOT_TOKEN и ADMIN_ID"
echo "   3. Инициализируйте базу данных: python init_db.py"
echo "   4. Запустите бота: python main.py"
echo ""
