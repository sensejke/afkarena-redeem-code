#!/usr/bin/env python3
"""
Простой тест токена Telegram бота
"""

import os
import sys
import asyncio
from telegram import Bot

async def test_token():
    """Тестирует токен бота"""
    
    # Загружаем .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Файл .env загружен")
    except ImportError:
        print("⚠️ python-dotenv не установлен")
    
    # Получаем токен
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден")
        return False
    
    if token == 'your_bot_token_here':
        print("❌ Токен не заменен на реальный")
        return False
    
    print(f"🔍 Тестирую токен: {token[:10]}...")
    
    try:
        # Создаем бота
        bot = Bot(token=token)
        
        # Получаем информацию о боте
        me = await bot.get_me()
        
        print(f"✅ Бот работает!")
        print(f"📛 Имя: {me.first_name}")
        print(f"🆔 Username: @{me.username}")
        print(f"🔢 ID: {me.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        
        error_msg = str(e).lower()
        if "unauthorized" in error_msg:
            print("💡 Токен неверный или бот удален")
        elif "timeout" in error_msg:
            print("💡 Проблемы с сетью или Telegram заблокирован")
        
        return False

def main():
    """Главная функция"""
    print("🤖 Тест токена Telegram бота")
    print("=" * 30)
    
    # Запускаем тест
    try:
        result = asyncio.run(test_token())
        
        if result:
            print("\n🎉 Токен работает! Можно запускать основного бота.")
        else:
            print("\n❌ Токен не работает. Исправьте проблему.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()