#!/bin/bash

echo "🤖 AFK Arena Telegram Bot - Запуск"
echo "=================================="

# Проверяем наличие Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python3."
    exit 1
fi

# Проверяем наличие основных файлов
if [ ! -f "telegram_bot.py" ]; then
    echo "❌ Файл telegram_bot.py не найден"
    exit 1
fi

if [ ! -f "direct_lilith_api.py" ]; then
    echo "❌ Файл direct_lilith_api.py не найден"
    exit 1
fi

if [ ! -f "run_direct_api_fixed.py" ]; then
    echo "❌ Файл run_direct_api_fixed.py не найден"
    exit 1
fi

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "⚠️ Файл .env не найден. Создаю из примера..."
    cp .env.example .env
    echo "📝 Отредактируйте файл .env и добавьте TELEGRAM_BOT_TOKEN"
    echo "💡 Получите токен от @BotFather в Telegram"
    exit 1
fi

# Проверяем наличие токена
source .env
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your_bot_token_here" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN не настроен в .env файле"
    echo "💡 Получите токен от @BotFather в Telegram и добавьте в .env:"
    echo "TELEGRAM_BOT_TOKEN=your_actual_token_here"
    exit 1
fi

echo "🔍 Тестирую токен бота..."
python3 test_bot_token.py
if [ $? -ne 0 ]; then
    echo "❌ Токен не работает, исправьте проблему"
    exit 1
fi

# Проверяем зависимости
echo "📦 Проверяю зависимости..."
python3 -c "import telegram" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Модуль python-telegram-bot не найден"
    echo "💡 Установите: pip3 install -r requirements.txt"
    exit 1
fi

echo "✅ Все проверки пройдены"
echo "🚀 Запускаю Telegram бота..."
echo ""

# Запускаем бота
python3 telegram_bot.py