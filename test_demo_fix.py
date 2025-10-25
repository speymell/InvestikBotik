"""
Тест исправления демо-режима
"""
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from database import db, User

def test_demo_flag():
    """Тест флага демо-режима"""
    with app.app_context():
        with app.test_client() as client:
            print("\n=== Тест 1: Проверка context_processor ===")
            
            # Создаём тестовую сессию
            with client.session_transaction() as sess:
                sess['is_demo'] = True
            
            # Делаем запрос к главной странице
            response = client.get('/')
            print(f"✅ Главная страница загружена: {response.status_code}")
            
            # Проверяем, что флаг передаётся в шаблон
            html = response.data.decode('utf-8')
            if 'data-is-demo="1"' in html:
                print("✅ Флаг is_demo корректно передаётся в шаблон")
            else:
                print("❌ Флаг is_demo НЕ найден в шаблоне")
            
            print("\n=== Тест 2: Демо-вход блокируется из Telegram ===")
            
            # Имитируем запрос из Telegram
            response = client.get('/demo_login', headers={
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10) TelegramBot'
            })
            
            if response.status_code == 302 and '/login' in response.location:
                print("✅ Демо-вход заблокирован из Telegram (редирект на /login)")
            else:
                print(f"❌ Демо-вход НЕ заблокирован: {response.status_code}, {response.location}")
            
            print("\n=== Тест 3: Демо-вход работает из обычного браузера ===")
            
            # Имитируем запрос из обычного браузера
            response = client.get('/demo_login', headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            })
            
            if response.status_code == 302 and '/dashboard' in response.location:
                print("✅ Демо-вход работает из обычного браузера (редирект на /dashboard)")
                
                # Проверяем флаг в сессии
                with client.session_transaction() as sess:
                    if sess.get('is_demo') == True:
                        print("✅ Флаг is_demo установлен в сессии")
                    else:
                        print("❌ Флаг is_demo НЕ установлен в сессии")
            else:
                print(f"❌ Демо-вход НЕ работает: {response.status_code}, {response.location}")
            
            print("\n=== Тест 4: Telegram-вход очищает флаг демо ===")
            
            # Сначала устанавливаем демо-флаг
            with client.session_transaction() as sess:
                sess['is_demo'] = True
            
            # Имитируем вход через Telegram
            response = client.get('/login?telegram_id=123456&username=TestUser')
            
            if response.status_code == 302:
                with client.session_transaction() as sess:
                    if sess.get('is_demo') is None:
                        print("✅ Флаг is_demo очищен при Telegram-входе")
                    else:
                        print("❌ Флаг is_demo НЕ очищен при Telegram-входе")
            
            print("\n=== Все тесты завершены ===\n")

if __name__ == '__main__':
    test_demo_flag()
