#!/usr/bin/env python3
"""
Прямая работа с API Lilith для активации кодов AFK Arena
Основано на анализе реального трафика браузера из Burp логов
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
import hashlib
import hmac
import base64
from urllib.parse import urlencode

class LilithAPI:
    def __init__(self, uid: str, verification_code: str):
        self.uid = uid
        self.verification_code = verification_code
        self.session = requests.Session()
        self.token = None
        # сlient-Id  
        self.client_id = "cid_c3ee9eb5-1e2f-4bbb-811c-b8a3f48289881"
        
        # Точные заголовки 
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Ch-Ua': '"Chromium";v="143", "Not A(Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Origin': 'https://cdkey.lilith.com',
            'Referer': 'https://cdkey.lilith.com/afk-global',
            'Priority': 'u=1, i'
        })
    
    def verify_account(self) -> bool:
        """
        Верификация аккаунта и получение токена
        Эндпоинт: POST /api/verify-afk-code
        """
        url = "https://cdkey.lilith.com/api/verify-afk-code"
        
        # Точный формат payload  
        payload = {
            "uid": self.uid,
            "game": "afk", 
            "code": self.verification_code
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-Client-Id': self.client_id
        }
        
        try:
            logging.info(f"🔐 Верифицируем аккаунт UID: {self.uid}")
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            
            logging.debug(f"Статус ответа: {response.status_code}")
            logging.debug(f"Заголовки ответа: {dict(response.headers)}")
            
            response.raise_for_status()
            
            data = response.json()
            logging.debug(f"Ответ API: {data}")
            
            if data.get('success'):
                token_data = data.get('data', {})
                self.token = token_data.get('token')
                if self.token:
                    logging.info(f"✅ Аккаунт верифицирован, токен получен")
                    return True
                else:
                    logging.error(f"❌ Токен не найден в ответе")
                    return False
            else:
                message = data.get('message', data.get('info', 'Неизвестная ошибка'))
                logging.error(f"❌ Ошибка верификации: {message}")
                return False
                
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Ошибка сети при верификации: {e}")
            return False
        except json.JSONDecodeError as e:
            logging.error(f"❌ Ошибка парсинга JSON: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Неожиданная ошибка при верификации: {e}")
            return False
    
    def get_user_accounts(self) -> List[Dict]:
        """
        Получение списка аккаунтов пользователя
        Эндпоинт: POST /api/users (из реальных Burp логов)
        """
        if not self.token:
            logging.error("❌ Токен не найден, сначала выполните верификацию")
            return []
            
        url = "https://cdkey.lilith.com/api/users"
        
        # Точный формат payload 
        payload = {
            "uid": self.uid,
            "game": "afk"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}',
            'X-Client-Id': self.client_id
        }
        
        try:
            logging.info(f"📋 Получаем список аккаунтов для UID: {self.uid}")
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            
            logging.debug(f"Статус ответа: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            logging.debug(f"Ответ API: {data}")
            
            if data.get('success'):
                # Из реальных логов: data.roles содержит массив ролей
                roles_data = data.get('data', {})
                roles = roles_data.get('roles', [])
                
                logging.info(f"✅ Получено {len(roles)} аккаунтов")
                
                # Логируем информацию об аккаунтах (формат из реальных логов)
                for i, role in enumerate(roles, 1):
                    name = role.get('name', 'Unknown')
                    svr_id = role.get('svr_id', 'Unknown')
                    level = role.get('level', 'Unknown')
                    uid = role.get('uid', 'Unknown')
                    is_main = role.get('is_main', False)
                    main_text = " (Основной)" if is_main else ""
                    logging.info(f"  {i}. {name} - Уровень {level}, Сервер {svr_id}{main_text}")
                
                return roles
            else:
                message = data.get('message', data.get('info', 'Неизвестная ошибка'))
                logging.error(f"❌ Ошибка получения аккаунтов: {message}")
                return []
                
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Ошибка сети при получении аккаунтов: {e}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"❌ Ошибка парсинга JSON: {e}")
            return []
        except Exception as e:
            logging.error(f"❌ Неожиданная ошибка при получении аккаунтов: {e}")
            return []
    
    def redeem_code(self, code: str, account_data: Dict) -> bool:
        """
        Активация кода для конкретного аккаунта
        Эндпоинт: POST /api/consume (из реальных Burp логов)
        """
        if not self.token:
            logging.error("❌ Токен не найден, сначала выполните верификацию")
            return False
            
        url = "https://cdkey.lilith.com/api/consume"
        
        # Точный формат payload из Burp логов
        payload = {
            "appId": "6241329",  # Из реальных логов
            "roleId": self.uid,  # В логах используется UID как roleId
            "game": "afk",
            "cdkey": code,
            "pupBody": "lilith"  # Из реальных логов
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}',
            'X-Client-Id': self.client_id
        }
        
        try:
            role_name = account_data.get('name', f"UID {self.uid}")
            logging.info(f"🎁 Активируем код {code} для аккаунта {role_name}")
            
            response = self.session.post(url, json=payload, headers=headers, timeout=30)
            
            logging.debug(f"Статус ответа: {response.status_code}")
            logging.debug(f"Payload: {payload}")
            
            # Обрабатываем разные статус коды
            if response.status_code == 400:
                # Код 400 может означать недействительный код или истекший verification code
                try:
                    data = response.json()
                    message = data.get('message', data.get('info', 'Неизвестная ошибка'))
                    
                    # Проверяем специфичные ошибки
                    if 'verification code' in message.lower() or 'expired' in message.lower():
                        logging.error(f"❌ Истек Verification Code! Нужно получить новый код в игре")
                        return False
                    elif 'not_found' in message or 'record_not_found' in message:
                        logging.warning(f"⚠️ Код {code} не найден или недействителен")
                    elif 'already' in message.lower():
                        logging.warning(f"⚠️ Код {code} уже был использован")
                    elif 'invalid' in message.lower():
                        logging.warning(f"⚠️ Код {code} недействителен")
                    else:
                        logging.warning(f"⚠️ Ошибка активации кода {code}: {message}")
                except:
                    logging.warning(f"⚠️ Код {code} недействителен (статус 400)")
                return False
            
            elif response.status_code == 401:
                logging.error(f"❌ Ошибка авторизации! Verification Code истек или неверен")
                return False
            
            response.raise_for_status()
            
            data = response.json()
            logging.debug(f"Ответ API: {data}")
            
            if data.get('success'):
                logging.info(f"✅ Код {code} успешно активирован для {role_name}")
                return True
            else:
                message = data.get('message', data.get('info', 'Неизвестная ошибка'))
                
                # Проверяем типичные ошибки
                if 'already' in message.lower() or 'уже' in message.lower():
                    logging.warning(f"⚠️ Код {code} уже был активирован для {role_name}")
                elif 'invalid' in message.lower() or 'недействительн' in message.lower():
                    logging.warning(f"⚠️ Код {code} недействителен или истек")
                elif 'expired' in message.lower() or 'истек' in message.lower():
                    logging.warning(f"⚠️ Код {code} истек")
                elif 'not_found' in message.lower() or 'record_not_found' in message.lower():
                    logging.warning(f"⚠️ Код {code} не найден")
                else:
                    logging.warning(f"⚠️ Не удалось активировать код {code} для {role_name}: {message}")
                
                return False
                
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Ошибка сети при активации кода {code}: {e}")
            return False
        except json.JSONDecodeError as e:
            logging.error(f"❌ Ошибка парсинга JSON при активации кода {code}: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Неожиданная ошибка при активации кода {code}: {e}")
            return False
    
    def redeem_codes_for_all_accounts(self, codes: List[str]) -> Dict[str, int]:
        """
        Активация списка кодов для всех аккаунтов
        Возвращает статистику активации
        """
        if not codes:
            logging.warning("⚠️ Список кодов пуст")
            return {"success": 0, "failed": 0, "already_used": 0}
        
        # Получаем аккаунты
        accounts = self.get_user_accounts()
        if not accounts:
            logging.error("❌ Не удалось получить аккаунты")
            return {"success": 0, "failed": 0, "already_used": 0}
        
        stats = {"success": 0, "failed": 0, "already_used": 0}
        
        for code in codes:
            logging.info(f"\n🎯 Активируем код: {code}")
            
            for account in accounts:
                role_name = account.get('role_name', 'Unknown')
                
                # Увеличенная задержка между запросами (из-за err_freq_limit)
                time.sleep(5)
                
                success = self.redeem_code(code, account)
                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
        
        return stats
    
    def redeem_codes_batch_with_tracking(self, codes: List[str], batch_size: int = 25) -> Dict:
        """
        Улучшенная активация кодов с батчингом и отслеживанием результатов
        Возвращает детальную статистику с успешными и неуспешными кодами
        """
        if not codes:
            logging.warning("⚠️ Список кодов пуст")
            return {
                "success": 0, 
                "failed": 0, 
                "successful_codes": [], 
                "failed_codes": [],
                "total_processed": 0
            }
        
        # Получаем аккаунты
        accounts = self.get_user_accounts()
        if not accounts:
            logging.error("❌ Не удалось получить аккаунты")
            return {
                "success": 0, 
                "failed": 0, 
                "successful_codes": [], 
                "failed_codes": [],
                "total_processed": 0
            }
        
        # Ограничиваем количество кодов для обработки
        codes_to_process = codes[:batch_size]
        logging.info(f"🎯 Обрабатываем {len(codes_to_process)} кодов из {len(codes)} (батч размер: {batch_size})")
        
        stats = {
            "success": 0, 
            "failed": 0, 
            "successful_codes": [], 
            "failed_codes": [],
            "total_processed": len(codes_to_process)
        }
        
        for i, code in enumerate(codes_to_process, 1):
            logging.info(f"\n🎯 Активируем код {i}/{len(codes_to_process)}: {code}")
            
            code_success = False
            
            for account in accounts:
                role_name = account.get('name', 'Unknown')
                
                # Задержка между запросами (увеличена из-за err_freq_limit)
                time.sleep(8)  # Увеличил с 3 до 8 секунд
                
                success = self.redeem_code(code, account)
                if success:
                    code_success = True
                    stats["success"] += 1
                    logging.info(f"✅ Код {code} успешно активирован для {role_name}")
                else:
                    stats["failed"] += 1
            
            # Отслеживаем результат по коду
            if code_success:
                stats["successful_codes"].append(code)
            else:
                stats["failed_codes"].append(code)
                logging.warning(f"❌ Код {code} не удалось активировать ни для одного аккаунта")
        
        logging.info(f"📊 Батч завершен: {len(stats['successful_codes'])} успешных, {len(stats['failed_codes'])} неуспешных кодов")
        return stats

def test_direct_api():
    """Тестирование прямого API с реальными данными из Burp логов"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    uid = os.getenv('UID')
    verification_code = os.getenv('VERIFICATION_CODE')
    
    if not uid or not verification_code:
        print("❌ Не найдены UID или VERIFICATION_CODE в .env файле")
        return
    
    print(f"🧪 Тестируем прямой API Lilith для UID: {uid}")
    print(f"🔐 Используем verification code: {verification_code[:3]}***")
    
    # Включаем подробное логирование для тестирования
    logging.getLogger().setLevel(logging.DEBUG)
    
    api = LilithAPI(uid, verification_code)
    
    # Шаг 1: Верификация аккаунта
    print("\n📋 Шаг 1: Верификация аккаунта...")
    if not api.verify_account():
        print("❌ Не удалось верифицировать аккаунт")
        return
    
    # Шаг 2: Получение аккаунтов
    print("\n📋 Шаг 2: Получение списка аккаунтов...")
    accounts = api.get_user_accounts()
    if not accounts:
        print("❌ Не удалось получить аккаунты")
        return
    
    print(f"\n✅ API работает! Найдено {len(accounts)} аккаунтов:")
    for i, account in enumerate(accounts, 1):
        name = account.get('name', 'Unknown')
        svr_id = account.get('svr_id', 'Unknown')
        level = account.get('level', 'Unknown')
        uid = account.get('uid', 'Unknown')
        is_main = account.get('is_main', False)
        main_text = " (Основной)" if is_main else ""
        print(f"  {i}. {name} - Уровень {level}, Сервер {svr_id}{main_text}")
        print(f"     UID: {uid}")
    
    # Шаг 3: Тестирование активации кода (с заведомо неработающим кодом)
    print(f"\n📋 Шаг 3: Тестирование активации кода...")
    test_codes = ["TESTCODE123", "INVALID456"]  # Тестовые коды
    
    print("⚠️ Тестируем с заведомо неработающими кодами (для проверки API):")
    
    for test_code in test_codes:
        print(f"\n🧪 Тестируем код: {test_code}")
        
        for i, account in enumerate(accounts[:1], 1):  # Тестируем только первый аккаунт
            name = account.get('name', 'Unknown')
            print(f"  Тестируем для аккаунта: {name}")
            
            result = api.redeem_code(test_code, account)
            if result:
                print(f"  ✅ Код активирован (неожиданно!)")
            else:
                print(f"  ❌ Код не активирован (ожидаемо)")
    
    print(f"\n🎉 Тестирование завершено! API готов к работе с реальными кодами.")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('direct_api_test.log', encoding='utf-8')
        ]
    )
    test_direct_api()