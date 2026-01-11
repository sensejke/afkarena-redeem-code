#!/usr/bin/env python3
"""
AFK Arena Code Redeemer - Автоматический активатор промокодов
Парсит коды с afk.guide + lolvvv.com и активирует через API Lilith
"""

import logging
import sys
import os
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set
import time
import json
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Модуль python-dotenv не найден")
    print("💡 Установите: pip3 install python-dotenv")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('afk_redeemer.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Конфигурация
LILITH_BASE_URL = 'https://cdkey.lilith.com'
CODE_WEBSITES = [
    'https://afk.guide/redemption-codes/',
    'https://www.lolvvv.com/codes/afk-arena'
]

# Заголовки для запросов
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru-RU,ru;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Origin': 'https://cdkey.lilith.com',
    'Referer': 'https://cdkey.lilith.com/afk-global',
}

# Настройки
CONNECT_TIMEOUT = 10
RECEIVE_TIMEOUT = 15
REDEEM_DELAY = 5

# Полный список сайтов для парсинга
FULL_CODE_WEBSITES = [
    'https://afk.guide/redemption-codes/',
    'https://www.lolvvv.com/codes/afk-arena'
]

def fix_truncated_code(code: str) -> str:
    """НЕ НУЖНО исправлять коды - они правильные в HTML"""
    # Убираем функцию исправления - коды правильные
    return code

def parse_afk_guide_fixed(url: str) -> List[Dict]:
    """ИСПРАВЛЕННЫЙ парсер для afk.guide - использует точные селекторы таблицы"""
    logger.info(f"🔧 ИСПРАВЛЕННЫЙ парсинг afk.guide: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        found_codes = set()
        
        # Ищем таблицу с кодами - несколько вариантов селекторов
        table = soup.find('table', {'data-ninja_table_instance': 'ninja_table_instance_0'})
        
        if not table:
            # Пробуем альтернативные селекторы
            table = soup.find('table', class_='ninja_table')
            if not table:
                table = soup.find('table')
        
        if not table:
            logger.warning("❌ Не найдена таблица с кодами")
            return []
        
        logger.info("✅ Найдена таблица с кодами")
        
        # Ищем все строки таблицы - несколько вариантов
        rows = table.find_all('tr', class_=lambda x: x and 'ninja_table_row_' in x)
        
        if not rows:
            # Альтернативный поиск строк
            rows = table.find_all('tr')
            logger.info(f"📊 Найдено {len(rows)} строк (альтернативный поиск)")
        else:
            logger.info(f"📊 Найдено {len(rows)} строк в таблице")
        
        for row in rows:
            # Ищем первую колонку с кодом - несколько вариантов
            code_cell = row.find('td', class_='ninja_column_0')
            
            if not code_cell:
                # Альтернативный поиск - первая колонка
                code_cell = row.find('td')
            
            if code_cell:
                code = code_cell.get_text().strip()
                
                # Проверяем что это похоже на код (буквы/цифры, длина 3-20)
                if code and len(code) >= 3 and len(code) <= 20 and code.replace(' ', '').isalnum():
                    found_codes.add(code)
                    logger.debug(f"  Найден: {code}")
        
        # Дополнительный поиск по всему тексту страницы
        if len(found_codes) == 0:
            logger.info("🔍 Дополнительный поиск кодов по всей странице...")
            
            # Ищем коды по паттернам
            import re
            text = soup.get_text()
            
            # Паттерны для кодов AFK Arena
            patterns = [
                r'\b[A-Z0-9]{6,15}\b',  # Заглавные буквы и цифры
                r'\b[a-z0-9]{6,15}\b',  # Строчные буквы и цифры
                r'\b[A-Za-z0-9]{6,15}\b'  # Смешанный регистр
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Фильтруем очевидно неподходящие коды
                    if (len(match) >= 6 and len(match) <= 15 and 
                        not match.lower() in ['redemption', 'codes', 'arena', 'guide', 'table', 'column']):
                        found_codes.add(match)
                        logger.debug(f"  Найден (паттерн): {match}")
            
            logger.info(f"🔍 Дополнительный поиск нашел {len(found_codes)} кодов")
        
        # Преобразуем в список словарей
        codes_list = []
        for code in found_codes:
            codes_list.append({
                'code': code,
                'gifts': {'Unknown': 'Parsed from afk.guide table'},
                'source': 'afk.guide'
            })
        
        logger.info(f"✅ afk.guide ТОЧНЫЙ парсинг: найдено {len(codes_list)} кодов")
        
        # Выводим найденные коды для проверки
        if codes_list:
            logger.info("🔍 Найденные коды:")
            for code_data in sorted(codes_list, key=lambda x: x['code'])[:15]:
                logger.info(f"  📋 {code_data['code']}")
            if len(codes_list) > 15:
                logger.info(f"  ... и еще {len(codes_list) - 15} кодов")
        
        return codes_list
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка ИСПРАВЛЕННОГО парсинга afk.guide: {e}")
        return []

def parse_lolvvv_fixed(url: str) -> List[Dict]:
    """ТОЧНЫЙ парсер для lolvvv.com - использует точные селекторы таблицы"""
    logger.info(f"🔧 ТОЧНЫЙ парсинг lolvvv.com: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        found_codes = set()
        
        # Ищем таблицу с кодами по точному селектору
        table = soup.find('table')
        
        if table:
            # Проверяем что это правильная таблица по заголовку
            caption = table.find('caption')
            if caption and 'Active AFK Arena Codes' in caption.get_text():
                logger.info("✅ Найдена таблица 'Active AFK Arena Codes'")
                
                # Ищем все строки в tbody
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    logger.info(f"📊 Найдено {len(rows)} строк в таблице")
                    
                    for row in rows:
                        # Ищем первую колонку с кодом (td.select-all)
                        code_cell = row.find('td', class_='select-all')
                        
                        if code_cell:
                            code = code_cell.get_text().strip()
                            
                            if code and len(code) >= 3:
                                found_codes.add(code)
                                logger.debug(f"  Найден: {code}")
                else:
                    logger.warning("❌ Не найден tbody в таблице")
            else:
                logger.warning("❌ Таблица не содержит 'Active AFK Arena Codes'")
        else:
            logger.warning("❌ Не найдена таблица на странице")
        
        # Дополнительный поиск по кнопкам копирования (как резерв)
        copy_buttons = soup.find_all('button', class_='btn rounded')
        if copy_buttons:
            logger.info(f"🔍 Найдено {len(copy_buttons)} кнопок копирования")
            
            for button in copy_buttons:
                # Ищем код в той же строке что и кнопка
                row = button.find_parent('tr')
                if row:
                    code_cell = row.find('td', class_='select-all')
                    if code_cell:
                        code = code_cell.get_text().strip()
                        if code and len(code) >= 3:
                            found_codes.add(code)
        
        # Преобразуем в список словарей
        codes_list = []
        for code in found_codes:
            codes_list.append({
                'code': code,
                'gifts': {'Unknown': 'Parsed from lolvvv.com table'},
                'source': 'lolvvv.com'
            })
        
        logger.info(f"✅ lolvvv.com ТОЧНЫЙ парсинг: найдено {len(codes_list)} кодов")
        
        # Выводим найденные коды для проверки
        if codes_list:
            logger.info("🔍 Найденные коды:")
            for code_data in sorted(codes_list, key=lambda x: x['code'])[:10]:
                logger.info(f"  📋 {code_data['code']}")
            if len(codes_list) > 10:
                logger.info(f"  ... и еще {len(codes_list) - 10} кодов")
        
        return codes_list
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка ТОЧНОГО парсинга lolvvv.com: {e}")
        return []

def get_all_codes_fixed() -> List[Dict]:
    """ИСПРАВЛЕННЫЙ сбор кодов с ВСЕХ сайтов без дубликатов"""
    logger.info("🔧 ИСПРАВЛЕННЫЙ ПАРСИНГ КОДОВ С ДВУХ САЙТОВ")
    logger.info("=" * 50)
    
    all_codes = []
    unique_codes: Set[str] = set()
    
    # Парсим afk.guide
    afk_guide_codes = parse_afk_guide_fixed(FULL_CODE_WEBSITES[0])
    
    # Парсим lolvvv.com
    lolvvv_codes = parse_lolvvv_fixed(FULL_CODE_WEBSITES[1])
    
    # Объединяем коды без дубликатов
    for codes_list, source_name in [(afk_guide_codes, 'afk.guide'), (lolvvv_codes, 'lolvvv.com')]:
        new_codes_count = 0
        for code_data in codes_list:
            code = code_data.get('code', '').strip()
            if code and code.lower() not in [c.lower() for c in unique_codes]:
                unique_codes.add(code)
                all_codes.append(code_data)
                new_codes_count += 1
        
        logger.info(f"📊 {source_name}: добавлено {new_codes_count} уникальных кодов")
    
    logger.info(f"📥 ИТОГО: {len(all_codes)} уникальных кодов с двух сайтов")
    
    # Показываем статистику по источникам
    sources_stats = {}
    for code_data in all_codes:
        source = code_data.get('source', 'unknown')
        sources_stats[source] = sources_stats.get(source, 0) + 1
    
    logger.info("📊 Статистика по источникам:")
    for source, count in sources_stats.items():
        logger.info(f"  - {source}: {count} кодов")
    
    return all_codes

# Импортируем остальные функции из оригинального файла
def get_uid_from_env(env_file='.env'):
    """Получает UID из указанного .env файла"""
    if not os.path.exists(env_file):
        return None
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('AFK_UID='):
                    uid = line.split('=', 1)[1].strip('"\'')
                    return uid if uid and uid != 'your_uid_here' else None
    except:
        pass
    return None

def update_env_file(uid, verification_code, env_file='.env'):
    """Обновляет указанный .env файл с новыми данными"""
    env_content = []
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.readlines()
    
    uid_found = False
    code_found = False
    
    for i, line in enumerate(env_content):
        if line.strip().startswith('AFK_UID='):
            env_content[i] = f'AFK_UID={uid}\n'
            uid_found = True
        elif line.strip().startswith('AFK_VERIFICATION_CODE='):
            env_content[i] = f'AFK_VERIFICATION_CODE={verification_code}\n'
            code_found = True
    
    if not uid_found:
        env_content.append(f'AFK_UID={uid}\n')
    if not code_found:
        env_content.append(f'AFK_VERIFICATION_CODE={verification_code}\n')
    
    with open(env_file, 'w') as f:
        f.writelines(env_content)
    
    print(f"💾 Настройки сохранены в {env_file}")

def main():
    """Главная функция - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    print("🔧 AFK Arena Code Redeemer - ИСПРАВЛЕННАЯ ВЕРСИЯ")
    print("РЕШАЕТ проблему обрезанных кодов в HTML таблице")
    print("Парсинг с ДВУХ сайтов: afk.guide + lolvvv.com")
    print("=" * 70)
    
    # Определяем файл конфигурации
    env_file = '.env_fixed'  # Отдельный файл для исправленной версии
    
    # Получаем UID
    uid = get_uid_from_env(env_file)
    
    if not uid:
        print("📱 Настройка аккаунта AFK Arena")
        print("Введите ваш UID из игры:")
        print("(Найти: Настройки → Аккаунт → UID)")
        uid = input("UID: ").strip()
        
        if not uid or not uid.isdigit():
            print("❌ Неверный UID. Должен содержать только цифры.")
            return
        
        print(f"💡 Настройки будут сохранены в {env_file}")
    else:
        print(f"✅ Используем UID: {uid} (из {env_file})")
    
    # Запрашиваем verification code
    print("\n🔑 Получение Verification Code")
    print("1. Откройте AFK Arena")
    print("2. Перейдите: Настройки → Redeem Code")
    print("3. Нажмите 'Generate Code'")
    print("4. Введите полученный код (действует 2 минуты!)")
    print()
    
    verification_code = input("Verification Code: ").strip()
    
    if not verification_code or len(verification_code) < 6:
        print("❌ Неверный код. Код должен содержать минимум 6 символов.")
        return
    
    # Обновляем файл конфигурации
    update_env_file(uid, verification_code, env_file)
    
    try:
        # Загружаем переменные окружения
        load_dotenv(env_file, override=True)
        os.environ['AFK_UID'] = uid
        os.environ['AFK_VERIFICATION_CODE'] = verification_code
        
        # Получаем ВСЕ коды с двух сайтов ИСПРАВЛЕННЫМ способом
        print("\n🔧 ИСПРАВЛЕННЫЙ ПАРСИНГ КОДОВ...")
        print("-" * 50)
        
        all_codes = get_all_codes_fixed()
        
        if all_codes:
            print(f"\n✅ Найдено {len(all_codes)} уникальных кодов!")
            
            # Показываем статистику
            sources_stats = {}
            for code_data in all_codes:
                source = code_data.get('source', 'unknown')
                sources_stats[source] = sources_stats.get(source, 0) + 1
            
            print("📊 Источники кодов:")
            for source, count in sources_stats.items():
                print(f"  - {source}: {count} кодов")
            
            # Показываем первые 20 кодов
            print(f"\n📋 Первые {min(20, len(all_codes))} кодов:")
            for i, code_data in enumerate(all_codes[:20]):
                code = code_data.get('code', 'N/A')
                source = code_data.get('source', 'N/A')
                print(f"  {i+1:2d}. {code} ({source})")
            
            if len(all_codes) > 20:
                print(f"  ... и еще {len(all_codes) - 20} кодов")
            
            # Проверяем есть ли исправленные коды
            fixed_codes = ['vdj82fht4r3000', 'ujqrukd2at1x', 'u4fctemje23x']
            found_fixed = []
            for fixed in fixed_codes:
                if any(code_data.get('code', '').lower() == fixed.lower() for code_data in all_codes):
                    found_fixed.append(fixed)
            
            if found_fixed:
                print(f"\n🔧 Найдены ИСПРАВЛЕННЫЕ коды: {', '.join(found_fixed)}")
        else:
            print("❌ Коды не найдены с обоих сайтов")
            return
        
        # Запускаем активацию через прямой API
        from direct_lilith_api import LilithAPI
        
        print(f"\n🚀 ЗАПУСКАЕМ АКТИВАЦИЮ {len(all_codes)} КОДОВ!")
        print("⏰ У вас есть ~2 минуты с момента генерации кода")
        print("-" * 50)
        
        # Инициализируем прямой API
        api = LilithAPI(uid, verification_code)
        
        # Верификация аккаунта
        logger.info(f"🔐 Верифицируем аккаунт UID: {uid}")
        if not api.verify_account():
            logger.error("❌ Не удалось верифицировать аккаунт через прямой API")
            return
        
        # Получаем список аккаунтов
        logger.info(f"📋 Получаем список аккаунтов для UID: {uid}")
        accounts = api.get_user_accounts()
        if not accounts:
            logger.error("❌ Не удалось получить аккаунты")
            return
        
        logger.info(f"✅ Получено {len(accounts)} аккаунтов")
        for acc in accounts:
            main_mark = " (Основной)" if acc.get('is_main') else ""
            logger.info(f"  - {acc.get('name')} - Уровень {acc.get('level')}, Сервер {acc.get('svr_id')}{main_mark}")
        
        # Извлекаем только коды из данных
        codes = [code_data['code'] for code_data in all_codes]
        
        # Активируем коды для всех аккаунтов
        logger.info(f"🎁 Начинаем активацию {len(codes)} кодов...")
        stats = api.redeem_codes_for_all_accounts(codes)
        
        # Логируем статистику
        total_attempts = stats["success"] + stats["failed"]
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"  ✅ Успешно активировано: {stats['success']}")
        print(f"  ❌ Неудачных попыток: {stats['failed']}")
        print(f"  📈 Всего попыток: {total_attempts}")
        print(f"  📊 Процент успеха: {(stats['success']/total_attempts*100):.1f}%" if total_attempts > 0 else "  📊 Процент успеха: 0%")
        
        if stats["success"] > 0:
            print(f"\n🎉 КОДЫ УСПЕШНО АКТИВИРОВАНЫ!")
            print(f"💎 Проверьте игру - награды должны быть в почте!")
        else:
            print(f"\n😞 Коды не активированы. Возможные причины:")
            print(f"  - Все коды уже использованы")
            print(f"  - Коды истекли")
            print(f"  - Превышен лимит активации")
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("📁 Убедитесь что файлы direct_lilith_api.py существует")
        print("💡 Установите: pip3 install python-dotenv requests beautifulsoup4")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")
        logger.error(f"Ошибка выполнения: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()