#!/usr/bin/env python3
"""
AFK Arena Code Redeemer - Telegram Bot
Полное управление активацией промокодов через Telegram
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Импортируем нашу логику
try:
    from direct_lilith_api import LilithAPI
    from run_direct_api_fixed import get_all_codes_fixed, parse_afk_guide_fixed, parse_lolvvv_fixed
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("📁 Убедитесь что файлы direct_lilith_api.py и run_direct_api_fixed.py существуют")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('telegram_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
WAITING_UID, WAITING_VERIFICATION_CODE, WAITING_BOT_TOKEN = range(3)

# Хранилище пользовательских данных
user_data: Dict[int, Dict] = {}

# Файлы для хранения данных о кодах
USED_CODES_FILE = 'used_codes.json'
FAILED_CODES_FILE = 'failed_codes.json'
USER_SETTINGS_FILE = 'user_settings.json'  # Новый файл для настроек пользователей

# Настройки активации
BATCH_SIZE = 25  # Количество кодов за один раз
MAX_CODES_PER_SESSION = 30  # Максимум кодов за сессию

def load_user_settings() -> Dict[int, Dict]:
    """Загружает настройки пользователей из файла"""
    try:
        import json
        if os.path.exists(USER_SETTINGS_FILE):
            with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек пользователей: {e}")
    return {}

def save_user_settings(settings: Dict[int, Dict]):
    """Сохраняет настройки пользователей в файл"""
    try:
        import json
        # Конвертируем ключи в строки для JSON
        settings_str_keys = {str(k): v for k, v in settings.items()}
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_str_keys, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек пользователей: {e}")

def get_user_uid(user_id: int) -> Optional[str]:
    """Получает сохраненный UID пользователя"""
    settings = load_user_settings()
    user_settings = settings.get(str(user_id), {})
    return user_settings.get('uid')

def save_user_uid(user_id: int, uid: str):
    """Сохраняет UID пользователя"""
    settings = load_user_settings()
    if str(user_id) not in settings:
        settings[str(user_id)] = {}
    settings[str(user_id)]['uid'] = uid
    settings[str(user_id)]['last_updated'] = datetime.now().isoformat()
    save_user_settings(settings)

def load_used_codes() -> Dict[str, List[str]]:
    """Загружает список использованных кодов из файла"""
    try:
        import json
        if os.path.exists(USED_CODES_FILE):
            with open(USED_CODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки использованных кодов: {e}")
    return {}

def save_used_codes(used_codes: Dict[str, List[str]]):
    """Сохраняет список использованных кодов в файл"""
    try:
        import json
        with open(USED_CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(used_codes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения использованных кодов: {e}")

def load_failed_codes() -> Dict[str, List[str]]:
    """Загружает список неуспешных кодов из файла"""
    try:
        import json
        if os.path.exists(FAILED_CODES_FILE):
            with open(FAILED_CODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки неуспешных кодов: {e}")
    return {}

def save_failed_codes(failed_codes: Dict[str, List[str]]):
    """Сохраняет список неуспешных кодов в файл"""
    try:
        import json
        with open(FAILED_CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(failed_codes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения неуспешных кодов: {e}")

def add_used_codes(uid: str, codes: List[str]):
    """Добавляет коды в список использованных для конкретного UID"""
    used_codes = load_used_codes()
    if uid not in used_codes:
        used_codes[uid] = []
    
    # Добавляем новые коды, избегая дубликатов
    for code in codes:
        if code.lower() not in [c.lower() for c in used_codes[uid]]:
            used_codes[uid].append(code)
    
    save_used_codes(used_codes)
    logger.info(f"Добавлено {len(codes)} использованных кодов для UID {uid}")

def add_failed_codes(uid: str, codes: List[str]):
    """Добавляет коды в список неуспешных для конкретного UID"""
    failed_codes = load_failed_codes()
    if uid not in failed_codes:
        failed_codes[uid] = []
    
    # Добавляем новые коды, избегая дубликатов
    for code in codes:
        if code.lower() not in [c.lower() for c in failed_codes[uid]]:
            failed_codes[uid].append(code)
    
    save_failed_codes(failed_codes)
    logger.info(f"Добавлено {len(codes)} неуспешных кодов для UID {uid}")

def get_used_codes(uid: str) -> List[str]:
    """Получает список использованных кодов для конкретного UID"""
    used_codes = load_used_codes()
    return used_codes.get(uid, [])

def get_failed_codes(uid: str) -> List[str]:
    """Получает список неуспешных кодов для конкретного UID"""
    failed_codes = load_failed_codes()
    return failed_codes.get(uid, [])

def filter_new_codes(uid: str, codes: List[Dict]) -> List[Dict]:
    """Фильтрует коды, исключая уже использованные и неуспешные"""
    used_codes = get_used_codes(uid)
    failed_codes = get_failed_codes(uid)
    
    # Объединяем списки и приводим к нижнему регистру
    excluded_codes = used_codes + failed_codes
    excluded_codes_lower = [c.lower() for c in excluded_codes]
    
    new_codes = []
    for code_data in codes:
        code = code_data.get('code', '').strip()
        if code and code.lower() not in excluded_codes_lower:
            new_codes.append(code_data)
    
    logger.info(f"Отфильтровано: {len(codes)} → {len(new_codes)} новых кодов для UID {uid}")
    logger.info(f"Исключено: {len(used_codes)} использованных + {len(failed_codes)} неуспешных")
    return new_codes

def clear_failed_codes(uid: str):
    """Очищает список неуспешных кодов для UID (для повторной попытки)"""
    failed_codes = load_failed_codes()
    if uid in failed_codes:
        del failed_codes[uid]
        save_failed_codes(failed_codes)
        logger.info(f"Очищены неуспешные коды для UID {uid}")

class AFKTelegramBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.application = None  # Инициализируем позже
        
        # Загружаем сохраненные настройки пользователей
        self.load_saved_user_data()
    
    def load_saved_user_data(self):
        """Загружает сохраненные настройки пользователей в память"""
        global user_data
        
        settings = load_user_settings()
        logger.info(f"📂 Загружаем настройки для {len(settings)} пользователей")
        
        for user_id_str, user_settings in settings.items():
            try:
                user_id = int(user_id_str)
                if user_id not in user_data:
                    user_data[user_id] = {}
                
                # Восстанавливаем UID
                if 'uid' in user_settings:
                    user_data[user_id]['uid'] = user_settings['uid']
                    logger.info(f"✅ Восстановлен UID для пользователя {user_id}: {user_settings['uid']}")
                
                # Время последнего обновления
                if 'last_updated' in user_settings:
                    user_data[user_id]['last_updated'] = user_settings['last_updated']
                    
            except Exception as e:
                logger.error(f"Ошибка загрузки настроек пользователя {user_id_str}: {e}")
    
    def setup_handlers(self):
        """Настройка обработчиков команд и кнопок"""
        
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.main_menu))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Обработчик настройки аккаунта (исправлен warning)
        setup_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.setup_account, pattern="^setup_account$"),
                CallbackQueryHandler(self.quick_update_code, pattern="^quick_update_code$")  # Добавлен новый entry point
            ],
            states={
                WAITING_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_uid)],
                WAITING_VERIFICATION_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_verification_code)],
            },
            fallbacks=[
                CallbackQueryHandler(self.main_menu, pattern="^main_menu$"),
                CommandHandler("start", self.start_command),
                CommandHandler("menu", self.main_menu),
                MessageHandler(filters.COMMAND, self.main_menu)  # Добавлен обработчик команд
            ],
            per_message=False,
            per_chat=True,
            per_user=True,
            allow_reentry=True,
            conversation_timeout=300  # 5 минут таймаут
        )
        self.application.add_handler(setup_handler)
        
        # Обработчики кнопок
        self.application.add_handler(CallbackQueryHandler(self.main_menu, pattern="^main_menu$"))
        self.application.add_handler(CallbackQueryHandler(self.parse_codes_menu, pattern="^parse_codes$"))
        self.application.add_handler(CallbackQueryHandler(self.redeem_codes_menu, pattern="^redeem_codes$"))
        self.application.add_handler(CallbackQueryHandler(self.settings_menu, pattern="^settings$"))
        self.application.add_handler(CallbackQueryHandler(self.account_info, pattern="^account_info$"))
        
        # Парсинг кодов
        self.application.add_handler(CallbackQueryHandler(self.parse_afk_guide, pattern="^parse_afk_guide$"))
        self.application.add_handler(CallbackQueryHandler(self.parse_lolvvv, pattern="^parse_lolvvv$"))
        self.application.add_handler(CallbackQueryHandler(self.parse_all_sites, pattern="^parse_all_sites$"))
        
        # Активация кодов
        self.application.add_handler(CallbackQueryHandler(self.quick_redeem, pattern="^quick_redeem$"))
        self.application.add_handler(CallbackQueryHandler(self.redeem_with_parsing, pattern="^redeem_with_parsing$"))
        
        # Настройки
        self.application.add_handler(CallbackQueryHandler(self.clear_account, pattern="^clear_account$"))
        self.application.add_handler(CallbackQueryHandler(self.view_logs, pattern="^view_logs$"))
        self.application.add_handler(CallbackQueryHandler(self.view_used_codes, pattern="^view_used_codes$"))
        self.application.add_handler(CallbackQueryHandler(self.clear_used_codes, pattern="^clear_used_codes$"))
        self.application.add_handler(CallbackQueryHandler(self.view_failed_codes, pattern="^view_failed_codes$"))
        self.application.add_handler(CallbackQueryHandler(self.clear_failed_codes_handler, pattern="^clear_failed_codes$"))
        
        # Обработчик неизвестных команд
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        welcome_text = f"""
🎮 **AFK Arena Code Redeemer Bot**

Привет, {user_name}! 👋

Этот бот поможет тебе автоматически активировать промокоды для AFK Arena.

**Возможности:**
🔍 Парсинг кодов с популярных сайтов
🎁 Автоматическая активация кодов
⚙️ Управление аккаунтами
📊 Статистика активации

Для начала работы нажми кнопку ниже или используй /menu
        """
        
        keyboard = [
            [InlineKeyboardButton("🚀 Главное меню", callback_data="main_menu")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 **Справка по боту**

**Основные команды:**
/start - Запуск бота
/menu - Главное меню
/help - Эта справка
/status - Статус аккаунта

**Как использовать:**

1️⃣ **Настройка аккаунта**
   - Укажи свой UID из игры
   - Получи Verification Code в игре

2️⃣ **Парсинг кодов**
   - Выбери источник кодов
   - Бот найдет все активные коды

3️⃣ **Активация**
   - Бот автоматически активирует коды
   - Получишь отчет о результатах

**Получение данных из игры:**

🆔 **UID:** Настройки → Аккаунт → UID
🔑 **Verification Code:** Настройки → Redeem Code → Generate Code

⚠️ **Важно:** Verification Code действует только 2 минуты!
        """
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        
        # Проверяем настроен ли аккаунт
        has_uid = bool(user_info.get('uid'))
        status_emoji = "✅" if has_uid else "❌"
        
        menu_text = f"""
🎮 **AFK Arena Code Redeemer**

**Статус аккаунта:** {status_emoji} {'Настроен' if has_uid else 'Не настроен'}

Выберите действие:
        """
        
        keyboard = []
        
        if has_uid:
            keyboard.extend([
                [InlineKeyboardButton("🔍 Парсинг кодов", callback_data="parse_codes")],
                [InlineKeyboardButton("🎁 Активация кодов", callback_data="redeem_codes")],
                [InlineKeyboardButton("👤 Информация об аккаунте", callback_data="account_info")],
                [InlineKeyboardButton("🔄 Обновить Verification Code", callback_data="quick_update_code")]
            ])
        else:
            keyboard.append([InlineKeyboardButton("⚙️ Настроить аккаунт", callback_data="setup_account")])
        
        keyboard.extend([
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def setup_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало настройки аккаунта"""
        setup_text = """
⚙️ **Настройка аккаунта AFK Arena**

Для работы бота нужны данные из игры:

🆔 **UID** - твой игровой идентификатор
🔑 **Verification Code** - временный код для активации

**Как получить UID:**
1. Открой AFK Arena
2. Настройки → Аккаунт → UID
3. Скопируй число

Введи свой UID:
        """
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(setup_text, reply_markup=reply_markup, parse_mode='Markdown')
        return WAITING_UID
    
    async def receive_uid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение UID от пользователя"""
        user_id = update.effective_user.id
        uid = update.message.text.strip()
        
        # Валидация UID
        if not uid.isdigit() or len(uid) < 8:
            await update.message.reply_text(
                "❌ Неверный UID. Должен содержать только цифры (минимум 8 символов).\n\nВведи UID еще раз:"
            )
            return WAITING_UID
        
        # Сохраняем UID
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['uid'] = uid
        
        # Сохраняем UID в файл для постоянного хранения
        save_user_uid(user_id, uid)
        
        success_text = f"""
✅ **UID сохранен:** `{uid}`

Теперь нужен Verification Code из игры.

**Как получить Verification Code:**
1. Открой AFK Arena
2. Настройки → Redeem Code
3. Нажми "Generate Code"
4. Скопируй полученный код

⚠️ **Важно:** Код действует только 2 минуты!

Введи Verification Code:
        """
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
        return WAITING_VERIFICATION_CODE
    
    async def receive_verification_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение Verification Code от пользователя"""
        user_id = update.effective_user.id
        verification_code = update.message.text.strip()
        
        # Валидация кода
        if len(verification_code) < 6:
            await update.message.reply_text(
                "❌ Неверный код. Должен содержать минимум 6 символов.\n\nВведи код еще раз:"
            )
            return WAITING_VERIFICATION_CODE
        
        # Сохраняем код
        user_data[user_id]['verification_code'] = verification_code
        user_data[user_id]['setup_time'] = datetime.now()
        
        # Тестируем подключение
        await update.message.reply_text("🔄 Проверяю подключение к API...")
        
        try:
            uid = user_data[user_id]['uid']
            api = LilithAPI(uid, verification_code)
            
            if await self.test_api_connection(api):
                success_text = f"""
🎉 **Аккаунт успешно настроен!**

✅ UID: `{uid}`
✅ Verification Code: `{verification_code[:3]}***`
✅ Подключение к API: Работает

Теперь можешь использовать все функции бота!
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔍 Парсить коды", callback_data="parse_codes")],
                    [InlineKeyboardButton("🎁 Активировать коды", callback_data="redeem_codes")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
                return ConversationHandler.END
            else:
                error_text = """
❌ **Ошибка подключения к API**

Возможные причины:
- Неверный UID
- Истек Verification Code (действует 2 минуты)
- Проблемы с сетью

Попробуй получить новый Verification Code и настроить заново.
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Настроить заново", callback_data="setup_account")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Ошибка при тестировании API: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при проверке подключения: {str(e)}\n\nПопробуй еще раз."
            )
            return ConversationHandler.END
    
    async def test_api_connection(self, api: LilithAPI) -> bool:
        """Тестирование подключения к API"""
        try:
            # Запускаем синхронную функцию в отдельном потоке
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, api.verify_account)
        except Exception as e:
            logger.error(f"Ошибка тестирования API: {e}")
            return False
    
    async def quick_update_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрое обновление только Verification Code (UID уже сохранен)"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        
        if not user_info.get('uid'):
            await update.callback_query.edit_message_text(
                "❌ UID не найден. Сначала настройте аккаунт полностью.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Настроить аккаунт", callback_data="setup_account")]])
            )
            return
        
        uid = user_info['uid']
        
        update_text = f"""
🔄 **Быстрое обновление Verification Code**

✅ UID сохранен: `{uid}`

Теперь получите новый Verification Code:

**Как получить Verification Code:**
1. Откройте AFK Arena
2. Настройки → Redeem Code
3. Нажмите "Generate Code"
4. Скопируйте полученный код

⚠️ **Важно:** Код действует только 2 минуты!

Введите новый Verification Code:
        """
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(update_text, reply_markup=reply_markup, parse_mode='Markdown')
        return WAITING_VERIFICATION_CODE
    
    async def parse_codes_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню парсинга кодов"""
        menu_text = """
🔍 **Парсинг промокодов**

Выбери источник для парсинга кодов:

🌐 **afk.guide** - популярный гайд-сайт
🌐 **lolvvv.com** - база активных кодов
🌐 **Все сайты** - объединенный список без дубликатов
        """
        
        keyboard = [
            [InlineKeyboardButton("🌐 afk.guide", callback_data="parse_afk_guide")],
            [InlineKeyboardButton("🌐 lolvvv.com", callback_data="parse_lolvvv")],
            [InlineKeyboardButton("🌍 Все сайты", callback_data="parse_all_sites")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def parse_afk_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Парсинг кодов с afk.guide"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        await update.callback_query.edit_message_text("🔄 Парсю коды с afk.guide...")
        
        try:
            # Запускаем парсинг в отдельном потоке
            loop = asyncio.get_event_loop()
            codes = await loop.run_in_executor(None, parse_afk_guide_fixed, 'https://afk.guide/redemption-codes/')
            
            if codes:
                # Фильтруем уже использованные коды
                if uid:
                    new_codes = filter_new_codes(uid, codes)
                    used_count = len(codes) - len(new_codes)
                else:
                    new_codes = codes
                    used_count = 0
                
                codes_text = f"✅ **Найдено {len(codes)} кодов с afk.guide:**\n"
                
                if used_count > 0:
                    codes_text += f"🔄 Уже использовано: {used_count}\n"
                    codes_text += f"🆕 Новых кодов: {len(new_codes)}\n\n"
                else:
                    codes_text += "\n"
                
                for i, code_data in enumerate(new_codes[:20], 1):
                    code = code_data.get('code', 'N/A')
                    codes_text += f"`{i:2d}. {code}`\n"
                
                if len(new_codes) > 20:
                    codes_text += f"\n... и еще {len(new_codes) - 20} кодов"
                
                # Сохраняем только новые коды для пользователя
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['parsed_codes'] = new_codes
                
            else:
                codes_text = "❌ Коды не найдены на afk.guide"
            
            keyboard = []
            if codes and len(new_codes) > 0:
                keyboard.append([InlineKeyboardButton("🎁 Активировать новые коды", callback_data="quick_redeem")])
            elif codes and len(new_codes) == 0:
                codes_text += "\n💡 Все коды уже использованы!"
            
            keyboard.extend([
                [InlineKeyboardButton("🔙 Назад", callback_data="parse_codes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(codes_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка парсинга afk.guide: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка парсинга: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="parse_codes")]])
            )
    
    async def parse_lolvvv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Парсинг кодов с lolvvv.com"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        await update.callback_query.edit_message_text("🔄 Парсю коды с lolvvv.com...")
        
        try:
            # Запускаем парсинг в отдельном потоке
            loop = asyncio.get_event_loop()
            codes = await loop.run_in_executor(None, parse_lolvvv_fixed, 'https://www.lolvvv.com/codes/afk-arena')
            
            if codes:
                # Фильтруем уже использованные коды
                if uid:
                    new_codes = filter_new_codes(uid, codes)
                    used_count = len(codes) - len(new_codes)
                else:
                    new_codes = codes
                    used_count = 0
                
                codes_text = f"✅ **Найдено {len(codes)} кодов с lolvvv.com:**\n"
                
                if used_count > 0:
                    codes_text += f"🔄 Уже использовано: {used_count}\n"
                    codes_text += f"🆕 Новых кодов: {len(new_codes)}\n\n"
                else:
                    codes_text += "\n"
                
                for i, code_data in enumerate(new_codes[:20], 1):
                    code = code_data.get('code', 'N/A')
                    codes_text += f"`{i:2d}. {code}`\n"
                
                if len(new_codes) > 20:
                    codes_text += f"\n... и еще {len(new_codes) - 20} кодов"
                
                # Сохраняем только новые коды для пользователя
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['parsed_codes'] = new_codes
                
            else:
                codes_text = "❌ Коды не найдены на lolvvv.com"
            
            keyboard = []
            if codes and len(new_codes) > 0:
                keyboard.append([InlineKeyboardButton("🎁 Активировать новые коды", callback_data="quick_redeem")])
            elif codes and len(new_codes) == 0:
                codes_text += "\n💡 Все коды уже использованы!"
            
            keyboard.extend([
                [InlineKeyboardButton("🔙 Назад", callback_data="parse_codes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(codes_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка парсинга lolvvv.com: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка парсинга: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="parse_codes")]])
            )
    
    async def parse_all_sites(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Парсинг кодов со всех сайтов"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        await update.callback_query.edit_message_text("🔄 Парсю коды со всех сайтов...")
        
        try:
            # Запускаем парсинг в отдельном потоке
            loop = asyncio.get_event_loop()
            all_codes = await loop.run_in_executor(None, get_all_codes_fixed)
            
            if all_codes:
                # Фильтруем уже использованные коды
                if uid:
                    new_codes = filter_new_codes(uid, all_codes)
                    used_count = len(all_codes) - len(new_codes)
                else:
                    new_codes = all_codes
                    used_count = 0
                
                # Статистика по источникам (для всех найденных кодов)
                sources_stats = {}
                for code_data in all_codes:
                    source = code_data.get('source', 'unknown')
                    sources_stats[source] = sources_stats.get(source, 0) + 1
                
                # Статистика по источникам (для новых кодов)
                new_sources_stats = {}
                for code_data in new_codes:
                    source = code_data.get('source', 'unknown')
                    new_sources_stats[source] = new_sources_stats.get(source, 0) + 1
                
                codes_text = f"✅ **Найдено {len(all_codes)} уникальных кодов:**\n\n"
                
                # Показываем общую статистику
                codes_text += "📊 **Всего по источникам:**\n"
                for source, count in sources_stats.items():
                    codes_text += f"• {source}: {count} кодов\n"
                
                if used_count > 0:
                    codes_text += f"\n🔄 **Уже использовано:** {used_count}\n"
                    codes_text += f"🆕 **Новых кодов:** {len(new_codes)}\n"
                    
                    if new_sources_stats:
                        codes_text += "\n📊 **Новые по источникам:**\n"
                        for source, count in new_sources_stats.items():
                            codes_text += f"• {source}: {count} кодов\n"
                
                codes_text += f"\n📋 **Первые {min(15, len(new_codes))} новых кодов:**\n"
                
                for i, code_data in enumerate(new_codes[:15], 1):
                    code = code_data.get('code', 'N/A')
                    source = code_data.get('source', 'N/A')
                    codes_text += f"`{i:2d}. {code}` ({source})\n"
                
                if len(new_codes) > 15:
                    codes_text += f"\n... и еще {len(new_codes) - 15} кодов"
                
                # Сохраняем только новые коды для пользователя
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['parsed_codes'] = new_codes
                
            else:
                codes_text = "❌ Коды не найдены ни на одном сайте"
            
            keyboard = []
            if all_codes and len(new_codes) > 0:
                keyboard.append([InlineKeyboardButton("🎁 Активировать новые коды", callback_data="quick_redeem")])
            elif all_codes and len(new_codes) == 0:
                codes_text += "\n💡 Все найденные коды уже использованы!"
            
            keyboard.extend([
                [InlineKeyboardButton("🔙 Назад", callback_data="parse_codes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(codes_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка парсинга всех сайтов: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка парсинга: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="parse_codes")]])
            )
    
    async def redeem_codes_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню активации кодов"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        
        has_parsed_codes = bool(user_info.get('parsed_codes'))
        
        menu_text = """
🎁 **Активация промокодов**

Выбери способ активации:

🚀 **Быстрая активация** - использует ранее найденные коды
🔍 **С парсингом** - сначала парсит, потом активирует
        """
        
        if has_parsed_codes:
            parsed_count = len(user_info['parsed_codes'])
            menu_text += f"\n💾 У тебя есть {parsed_count} сохраненных кодов"
        
        keyboard = []
        
        if has_parsed_codes:
            keyboard.append([InlineKeyboardButton("🚀 Быстрая активация", callback_data="quick_redeem")])
        
        keyboard.extend([
            [InlineKeyboardButton("🔍 Активация с парсингом", callback_data="redeem_with_parsing")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def quick_redeem(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая активация сохраненных кодов"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        
        if not user_info.get('parsed_codes'):
            await update.callback_query.edit_message_text(
                "❌ Нет сохраненных кодов. Сначала выполни парсинг.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Парсить коды", callback_data="parse_codes")]])
            )
            return
        
        if not user_info.get('uid') or not user_info.get('verification_code'):
            await update.callback_query.edit_message_text(
                "❌ Аккаунт не настроен. Настрой аккаунт сначала.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Настроить", callback_data="setup_account")]])
            )
            return
        
        codes = user_info['parsed_codes']
        await update.callback_query.edit_message_text(f"🔄 Активирую {len(codes)} кодов...")
        
        try:
            uid = user_info['uid']
            verification_code = user_info['verification_code']
            
            api = LilithAPI(uid, verification_code)
            
            # Верификация аккаунта (асинхронно)
            loop = asyncio.get_event_loop()
            if not await loop.run_in_executor(None, api.verify_account):
                # Если верификация не удалась - предлагаем обновить код
                error_text = """
❌ **Не удалось верифицировать аккаунт**

Возможные причины:
🕐 Истек Verification Code (действует 2 минуты)
🔑 Неверный код

💡 **Получите новый Verification Code:**
1. Откройте AFK Arena
2. Настройки → Redeem Code  
3. Нажмите "Generate Code"
4. Обновите код в боте
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Обновить Verification Code", callback_data="setup_account")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="redeem_codes")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')
                return
            
            # Получаем аккаунты (асинхронно)
            accounts = await loop.run_in_executor(None, api.get_user_accounts)
            if not accounts:
                await update.callback_query.edit_message_text(
                    "❌ Не удалось получить список аккаунтов.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="redeem_codes")]])
                )
                return
            
            # Активируем коды батчами (асинхронно)
            codes_list = [code_data['code'] for code_data in codes]
            
            # Ограничиваем количество кодов
            codes_to_activate = codes_list[:MAX_CODES_PER_SESSION]
            if len(codes_list) > MAX_CODES_PER_SESSION:
                await update.callback_query.edit_message_text(
                    f"🔄 Найдено {len(codes_list)} кодов. Активирую первые {MAX_CODES_PER_SESSION} за эту сессию..."
                )
            
            stats = await loop.run_in_executor(None, api.redeem_codes_batch_with_tracking, codes_to_activate, BATCH_SIZE)
            
            # Сохраняем результаты
            if stats["successful_codes"]:
                add_used_codes(uid, stats["successful_codes"])
                logger.info(f"Сохранено {len(stats['successful_codes'])} успешных кодов для UID {uid}")
            
            if stats["failed_codes"]:
                add_failed_codes(uid, stats["failed_codes"])
                logger.info(f"Сохранено {len(stats['failed_codes'])} неуспешных кодов для UID {uid}")
            
            # Формируем отчет
            total_attempts = stats["success"] + stats["failed"]
            success_rate = (stats["success"] / total_attempts * 100) if total_attempts > 0 else 0
            
            result_text = f"""
🎉 **Активация завершена!**

📊 **Статистика:**
✅ Успешных активаций: {stats['success']}
❌ Неудачных попыток: {stats['failed']}
📈 Всего попыток: {total_attempts}
📊 Успешность: {success_rate:.1f}%

🎯 **По кодам:**
✅ Успешных кодов: {len(stats['successful_codes'])}
❌ Неуспешных кодов: {len(stats['failed_codes'])}
📦 Обработано кодов: {stats['total_processed']}

👥 **Аккаунтов обработано:** {len(accounts)}
            """
            
            if len(codes_list) > MAX_CODES_PER_SESSION:
                result_text += f"\n💡 Осталось {len(codes_list) - MAX_CODES_PER_SESSION} кодов для следующей сессии"
            
            if stats["successful_codes"]:
                result_text += "\n💎 Проверь игру - награды должны быть в почте!"
            
            if stats["failed_codes"]:
                result_text += f"\n🔄 {len(stats['failed_codes'])} кодов сохранены как неуспешные и будут пропущены в будущем"
            
            keyboard = [
                [InlineKeyboardButton("🔍 Парсить новые коды", callback_data="parse_codes")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(result_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка активации кодов: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка активации: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="redeem_codes")]])
            )
    
    async def redeem_with_parsing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Активация с предварительным парсингом"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        
        if not user_info.get('uid') or not user_info.get('verification_code'):
            await update.callback_query.edit_message_text(
                "❌ Аккаунт не настроен. Настрой аккаунт сначала.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Настроить", callback_data="setup_account")]])
            )
            return
        
        await update.callback_query.edit_message_text("🔄 Парсю коды со всех сайтов...")
        
        try:
            # Парсим коды
            all_codes = get_all_codes_fixed()
            
            if not all_codes:
                await update.callback_query.edit_message_text(
                    "❌ Не найдено активных кодов на сайтах.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="redeem_codes")]])
                )
                return
            
            # Сохраняем коды
            user_data[user_id]['parsed_codes'] = all_codes
            
            await update.callback_query.edit_message_text(f"🔄 Найдено {len(all_codes)} кодов. Активирую...")
            
            # Активируем коды (используем ту же логику что и в quick_redeem)
            uid = user_info['uid']
            verification_code = user_info['verification_code']
            
            api = LilithAPI(uid, verification_code)
            
            # Все API вызовы делаем асинхронными
            loop = asyncio.get_event_loop()
            if not await loop.run_in_executor(None, api.verify_account):
                await update.callback_query.edit_message_text(
                    "❌ Не удалось верифицировать аккаунт. Возможно истек Verification Code.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Обновить код", callback_data="setup_account")]])
                )
                return
            
            accounts = await loop.run_in_executor(None, api.get_user_accounts)
            if not accounts:
                await update.callback_query.edit_message_text(
                    "❌ Не удалось получить список аккаунтов.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="redeem_codes")]])
                )
                return
            
            codes_list = [code_data['code'] for code_data in all_codes]
            
            # Ограничиваем количество кодов
            codes_to_activate = codes_list[:MAX_CODES_PER_SESSION]
            if len(codes_list) > MAX_CODES_PER_SESSION:
                await update.callback_query.edit_message_text(
                    f"🔄 Найдено {len(codes_list)} кодов. Активирую первые {MAX_CODES_PER_SESSION} за эту сессию..."
                )
            
            stats = await loop.run_in_executor(None, api.redeem_codes_batch_with_tracking, codes_to_activate, BATCH_SIZE)
            
            # Сохраняем результаты
            if stats["successful_codes"]:
                add_used_codes(uid, stats["successful_codes"])
                logger.info(f"Сохранено {len(stats['successful_codes'])} успешных кодов для UID {uid}")
            
            if stats["failed_codes"]:
                add_failed_codes(uid, stats["failed_codes"])
                logger.info(f"Сохранено {len(stats['failed_codes'])} неуспешных кодов для UID {uid}")
            
            # Статистика по источникам
            sources_stats = {}
            for code_data in all_codes:
                source = code_data.get('source', 'unknown')
                sources_stats[source] = sources_stats.get(source, 0) + 1
            
            total_attempts = stats["success"] + stats["failed"]
            success_rate = (stats["success"] / total_attempts * 100) if total_attempts > 0 else 0
            
            result_text = f"""
🎉 **Парсинг и активация завершены!**

🔍 **Найдено кодов:**
"""
            
            for source, count in sources_stats.items():
                result_text += f"• {source}: {count}\n"
            
            result_text += f"""
📊 **Результат активации:**
✅ Успешных активаций: {stats['success']}
❌ Неудачных попыток: {stats['failed']}
📈 Всего попыток: {total_attempts}
📊 Успешность: {success_rate:.1f}%

🎯 **По кодам:**
✅ Успешных кодов: {len(stats['successful_codes'])}
❌ Неуспешных кодов: {len(stats['failed_codes'])}
📦 Обработано кодов: {stats['total_processed']}

👥 **Аккаунтов обработано:** {len(accounts)}
            """
            
            if len(codes_list) > MAX_CODES_PER_SESSION:
                result_text += f"\n💡 Осталось {len(codes_list) - MAX_CODES_PER_SESSION} кодов для следующей сессии"
            
            if stats["successful_codes"]:
                result_text += "\n💎 Проверь игру - награды должны быть в почте!"
            
            if stats["failed_codes"]:
                result_text += f"\n🔄 {len(stats['failed_codes'])} кодов сохранены как неуспешные"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Повторить", callback_data="redeem_with_parsing")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(result_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка парсинга и активации: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="redeem_codes")]])
            )
    
    async def account_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация об аккаунте"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        
        if not user_info.get('uid'):
            await update.callback_query.edit_message_text(
                "❌ Аккаунт не настроен.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Настроить", callback_data="setup_account")]])
            )
            return
        
        await update.callback_query.edit_message_text("🔄 Получаю информацию об аккаунте...")
        
        try:
            uid = user_info['uid']
            verification_code = user_info.get('verification_code', '')
            
            if not verification_code:
                info_text = f"""
👤 **Информация об аккаунте**

🆔 **UID:** `{uid}`
🔑 **Verification Code:** Не установлен

❌ Для получения полной информации нужен Verification Code
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔑 Обновить код", callback_data="setup_account")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
            else:
                api = LilithAPI(uid, verification_code)
                
                # Асинхронные вызовы API
                loop = asyncio.get_event_loop()
                if await loop.run_in_executor(None, api.verify_account):
                    accounts = await loop.run_in_executor(None, api.get_user_accounts)
                    
                    info_text = f"""
👤 **Информация об аккаунте**

🆔 **UID:** `{uid}`
🔑 **Verification Code:** `{verification_code[:3]}***`
✅ **Статус API:** Подключен

👥 **Игровые аккаунты ({len(accounts)}):**
"""
                    
                    for i, account in enumerate(accounts, 1):
                        name = account.get('name', 'Unknown')
                        level = account.get('level', '?')
                        svr_id = account.get('svr_id', '?')
                        is_main = account.get('is_main', False)
                        main_mark = " 👑" if is_main else ""
                        
                        info_text += f"`{i}. {name}` - Ур.{level}, Сервер {svr_id}{main_mark}\n"
                    
                    # Информация о сохраненных кодах
                    parsed_codes = user_info.get('parsed_codes', [])
                    if parsed_codes:
                        info_text += f"\n💾 **Сохранено кодов:** {len(parsed_codes)}"
                    
                    setup_time = user_info.get('setup_time')
                    if setup_time:
                        info_text += f"\n⏰ **Настроен:** {setup_time.strftime('%d.%m.%Y %H:%M')}"
                    
                else:
                    info_text = f"""
👤 **Информация об аккаунте**

🆔 **UID:** `{uid}`
🔑 **Verification Code:** `{verification_code[:3]}***`
❌ **Статус API:** Ошибка подключения

Возможно истек Verification Code (действует 2 минуты)
                    """
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Обновить код", callback_data="setup_account")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка получения информации об аккаунте: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])
            )
    
    async def settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню настроек"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        # Подсчитываем коды
        used_codes_count = len(get_used_codes(uid)) if uid else 0
        failed_codes_count = len(get_failed_codes(uid)) if uid else 0
        
        menu_text = f"""
⚙️ **Настройки бота**

Управление настройками и данными:

📊 **Статистика:**
✅ Успешных кодов: {used_codes_count}
❌ Неуспешных кодов: {failed_codes_count}
📦 Всего обработано: {used_codes_count + failed_codes_count}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить аккаунт", callback_data="setup_account")],
            [InlineKeyboardButton("📋 Успешные коды", callback_data="view_used_codes")],
            [InlineKeyboardButton("❌ Неуспешные коды", callback_data="view_failed_codes")],
            [InlineKeyboardButton("🗑️ Очистить данные", callback_data="clear_account")],
            [InlineKeyboardButton("🧹 Сбросить неуспешные", callback_data="clear_failed_codes")],
            [InlineKeyboardButton("📋 Просмотр логов", callback_data="view_logs")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def clear_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка данных аккаунта"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        # Подсчитываем что будет удалено
        used_codes_count = len(get_used_codes(uid)) if uid else 0
        failed_codes_count = len(get_failed_codes(uid)) if uid else 0
        
        # Очищаем данные пользователя
        if user_id in user_data:
            del user_data[user_id]
        
        # Очищаем использованные коды
        if uid:
            used_codes = load_used_codes()
            if uid in used_codes:
                del used_codes[uid]
                save_used_codes(used_codes)
            
            # Очищаем неуспешные коды
            failed_codes = load_failed_codes()
            if uid in failed_codes:
                del failed_codes[uid]
                save_failed_codes(failed_codes)
        
        success_text = f"""
🗑️ **Все данные очищены**

Удалено:
- UID и Verification Code  
- Сохраненные коды
- {used_codes_count} успешных кодов
- {failed_codes_count} неуспешных кодов

Для использования бота настрой аккаунт заново.
        """
        
        keyboard = [
            [InlineKeyboardButton("⚙️ Настроить аккаунт", callback_data="setup_account")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def view_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр логов"""
        try:
            # Читаем последние 20 строк лога
            if os.path.exists('telegram_bot.log'):
                with open('telegram_bot.log', 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = lines[-20:] if len(lines) > 20 else lines
                
                log_text = "📋 **Последние записи лога:**\n\n```\n"
                log_text += ''.join(last_lines)
                log_text += "\n```"
                
                if len(log_text) > 4000:  # Telegram limit
                    log_text = log_text[:4000] + "...\n```"
            else:
                log_text = "📋 **Лог файл не найден**"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(log_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка чтения логов: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка чтения логов: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="settings")]])
            )
    
    async def view_used_codes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр использованных кодов"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        if not uid:
            await update.callback_query.edit_message_text(
                "❌ UID не настроен. Настройте аккаунт сначала.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Настроить", callback_data="setup_account")]])
            )
            return
        
        try:
            used_codes = get_used_codes(uid)
            
            if used_codes:
                codes_text = f"📋 **Использованные коды для UID {uid}:**\n\n"
                codes_text += f"📊 **Всего:** {len(used_codes)} кодов\n\n"
                
                # Показываем последние 30 кодов
                recent_codes = used_codes[-30:] if len(used_codes) > 30 else used_codes
                
                for i, code in enumerate(recent_codes, 1):
                    codes_text += f"`{i:2d}. {code}`\n"
                
                if len(used_codes) > 30:
                    codes_text += f"\n... и еще {len(used_codes) - 30} кодов"
                
                codes_text += f"\n💡 Эти коды будут пропущены при следующем парсинге"
            else:
                codes_text = f"📋 **Использованные коды для UID {uid}:**\n\n❌ Нет использованных кодов"
            
            keyboard = [
                [InlineKeyboardButton("🧹 Очистить список", callback_data="clear_used_codes")] if used_codes else [],
                [InlineKeyboardButton("🔙 Назад", callback_data="settings")]
            ]
            keyboard = [row for row in keyboard if row]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(codes_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка просмотра использованных кодов: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="settings")]])
            )
    
    async def clear_used_codes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка списка использованных кодов"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        if not uid:
            await update.callback_query.edit_message_text(
                "❌ UID не настроен.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="settings")]])
            )
            return
        
        try:
            used_codes = load_used_codes()
            codes_count = len(used_codes.get(uid, []))
            
            if uid in used_codes:
                del used_codes[uid]
                save_used_codes(used_codes)
            
            success_text = f"""
🧹 **Список использованных кодов очищен**

Удалено {codes_count} кодов для UID {uid}

Теперь все коды будут считаться новыми при следующем парсинге.
            """
            
            keyboard = [
                [InlineKeyboardButton("🔍 Парсить коды", callback_data="parse_codes")],
                [InlineKeyboardButton("🔙 Назад", callback_data="settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка очистки использованных кодов: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="settings")]])
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        status_text = f"""
📊 **Статус бота**

👤 **Пользователь:** {update.effective_user.first_name}
🆔 **Telegram ID:** `{user_id}`

⚙️ **Настройки:**
"""
        
        if uid:
            status_text += f"✅ UID: `{uid}`\n"
        else:
            status_text += "❌ UID: Не настроен\n"
        
        if user_info.get('verification_code'):
            status_text += f"✅ Verification Code: `{user_info['verification_code'][:3]}***`\n"
        else:
            status_text += "❌ Verification Code: Не настроен\n"
        
        parsed_codes = user_info.get('parsed_codes', [])
        status_text += f"💾 Сохранено кодов: {len(parsed_codes)}\n"
        
        # Информация об использованных кодах
        used_codes_count = len(get_used_codes(uid)) if uid else 0
        failed_codes_count = len(get_failed_codes(uid)) if uid else 0
        status_text += f"✅ Успешных кодов: {used_codes_count}\n"
        status_text += f"❌ Неуспешных кодов: {failed_codes_count}\n"
        
        setup_time = user_info.get('setup_time')
        if setup_time:
            status_text += f"⏰ Настроен: {setup_time.strftime('%d.%m.%Y %H:%M')}\n"
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неизвестных сообщений"""
        await update.message.reply_text(
            "🤔 Не понимаю эту команду. Используй /menu для навигации.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
    
    def run(self):
        """Запуск бота с обработкой ошибок"""
        logger.info("🚀 Запуск AFK Arena Telegram Bot")
        
        try:
            # Проверяем токен перед запуском
            print("🔍 Проверяю токен бота...")
            
            # Создаем приложение с правильными таймаутами
            self.application = (
                Application.builder()
                .token(self.bot_token)
                .get_updates_read_timeout(10)
                .get_updates_write_timeout(10)
                .get_updates_connect_timeout(10)
                .get_updates_pool_timeout(5)
                .build()
            )
            self.setup_handlers()
            
            print("✅ Бот настроен, запускаю polling...")
            
            # Запускаем без устаревших параметров
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Критическая ошибка при запуске бота: {e}")
            
            # Детальная диагностика ошибок
            error_msg = str(e).lower()
            
            if "unauthorized" in error_msg or "401" in error_msg:
                print("❌ ОШИБКА: Неверный токен бота")
                print("💡 Решение:")
                print("1. Проверьте токен в .env файле")
                print("2. Убедитесь что бот создан через @BotFather")
                print("3. Токен должен быть в формате: 1234567890:ABCdef...")
                
            elif "timed out" in error_msg or "timeout" in error_msg:
                print("❌ ОШИБКА: Таймаут подключения")
                print("💡 Решение:")
                print("1. Проверьте интернет соединение")
                print("2. Попробуйте через VPN если Telegram заблокирован")
                print("3. Подождите несколько минут и попробуйте снова")
                
            elif "network" in error_msg or "connection" in error_msg:
                print("❌ ОШИБКА: Проблемы с сетью")
                print("💡 Решение:")
                print("1. Проверьте подключение к интернету")
                print("2. Проверьте настройки файрвола")
                print("3. Убедитесь что порты не заблокированы")
                
            else:
                print(f"❌ НЕИЗВЕСТНАЯ ОШИБКА: {e}")
                print("💡 Попробуйте:")
                print("1. Перезапустить бота")
                print("2. Проверить логи: tail -f telegram_bot.log")
                print("3. Обновить зависимости: pip3 install -r requirements.txt")
            
            raise

    async def view_failed_codes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр неуспешных кодов"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        if not uid:
            await update.callback_query.edit_message_text(
                "❌ UID не настроен. Настройте аккаунт сначала.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Настроить", callback_data="setup_account")]])
            )
            return
        
        try:
            failed_codes = get_failed_codes(uid)
            
            if failed_codes:
                codes_text = f"❌ **Неуспешные коды для UID {uid}:**\n\n"
                codes_text += f"📊 **Всего:** {len(failed_codes)} кодов\n\n"
                codes_text += "💡 Эти коды не удалось активировать и они исключены из парсинга\n\n"
                
                # Показываем последние 30 кодов
                recent_codes = failed_codes[-30:] if len(failed_codes) > 30 else failed_codes
                
                for i, code in enumerate(recent_codes, 1):
                    codes_text += f"`{i:2d}. {code}`\n"
                
                if len(failed_codes) > 30:
                    codes_text += f"\n... и еще {len(failed_codes) - 30} кодов"
                
                codes_text += f"\n🔄 Можно сбросить список для повторной попытки"
            else:
                codes_text = f"❌ **Неуспешные коды для UID {uid}:**\n\n✅ Нет неуспешных кодов"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Сбросить для повтора", callback_data="clear_failed_codes")] if failed_codes else [],
                [InlineKeyboardButton("🔙 Назад", callback_data="settings")]
            ]
            keyboard = [row for row in keyboard if row]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(codes_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка просмотра неуспешных кодов: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="settings")]])
            )
    
    async def clear_failed_codes_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка списка неуспешных кодов"""
        user_id = update.effective_user.id
        user_info = user_data.get(user_id, {})
        uid = user_info.get('uid', '')
        
        if not uid:
            await update.callback_query.edit_message_text(
                "❌ UID не настроен.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="settings")]])
            )
            return
        
        try:
            failed_codes = get_failed_codes(uid)
            codes_count = len(failed_codes)
            
            clear_failed_codes(uid)
            
            success_text = f"""
🔄 **Список неуспешных кодов сброшен**

Удалено {codes_count} неуспешных кодов для UID {uid}

Теперь эти коды будут снова включены в парсинг и можно попробовать их активировать повторно.

💡 Возможно некоторые коды стали активными или проблема была временной.
            """
            
            keyboard = [
                [InlineKeyboardButton("🔍 Парсить коды", callback_data="parse_codes")],
                [InlineKeyboardButton("🔙 Назад", callback_data="settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка очистки неуспешных кодов: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="settings")]])
            )

def main():
    """Главная функция"""
    print("🎮 AFK Arena Code Redeemer - Telegram Bot")
    print("=" * 50)
    
    # Загружаем переменные окружения из .env файла
    try:
        from dotenv import load_dotenv
        load_dotenv()  # Загружаем .env файл
        print("✅ Файл .env загружен")
    except ImportError:
        print("⚠️ python-dotenv не установлен, используем системные переменные")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки .env: {e}")
    
    # Получаем токен бота
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ Не найден TELEGRAM_BOT_TOKEN в переменных окружения")
        print("\n📝 Создайте бота:")
        print("1. Напишите @BotFather в Telegram")
        print("2. Отправьте /newbot")
        print("3. Следуйте инструкциям")
        print("4. Скопируйте токен")
        print("\n💡 Установите токен в .env файл:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        
        # Проверяем есть ли .env файл
        if os.path.exists('.env'):
            print(f"\n📁 Файл .env найден, проверьте что токен правильно указан")
            # Показываем содержимое .env (без токена)
            try:
                with open('.env', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if 'TELEGRAM_BOT_TOKEN=' in line:
                            if 'your_bot_token_here' in line:
                                print("❌ Токен не заменен на реальный")
                            else:
                                print("✅ Токен найден в .env файле")
                            break
            except:
                pass
        else:
            print(f"\n❌ Файл .env не найден, создайте его из .env.example")
        
        sys.exit(1)
    
    print(f"✅ Токен бота найден: {bot_token[:10]}...")
    
    try:
        # Создаем и запускаем бота
        bot = AFKTelegramBot(bot_token)
        bot.run()
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"❌ Ошибка запуска: {e}")
        
        # Дополнительная диагностика
        if "Timed out" in str(e):
            print("\n🔧 Диагностика timeout:")
            print("1. Проверьте интернет соединение")
            print("2. Убедитесь что токен бота правильный")
            print("3. Попробуйте перезапустить через несколько минут")
            print("4. Проверьте что бот не заблокирован Telegram")
        
        sys.exit(1)

if __name__ == "__main__":
    main()