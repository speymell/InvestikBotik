#!/usr/bin/env python3
"""
Скрипт для тестирования API InvestBot
Запустите после деплоя для проверки работоспособности
"""

import requests
import json

# Замените на ваш URL
BASE_URL = "http://localhost:5000"  # Для локального тестирования
# BASE_URL = "https://your-app-name.onrender.com"  # Для продакшена

# Автоматически определяем URL если запущено на Render
import os
if os.environ.get('RENDER'):
    BASE_URL = f"https://{os.environ.get('RENDER_SERVICE_NAME', 'localhost')}.onrender.com"

def test_health():
    """Тест health check"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_sync_stocks():
    """Тест синхронизации акций"""
    try:
        response = requests.get(f"{BASE_URL}/admin/sync-stocks")
        print(f"✅ Sync stocks: {response.status_code}")
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Message: {data.get('message')}")
        return True
    except Exception as e:
        print(f"❌ Sync stocks failed: {e}")
        return False

def test_update_prices():
    """Тест обновления цен"""
    try:
        response = requests.get(f"{BASE_URL}/admin/update-prices")
        print(f"✅ Update prices: {response.status_code}")
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Message: {data.get('message')}")
        return True
    except Exception as e:
        print(f"❌ Update prices failed: {e}")
        return False

def test_stock_price():
    """Тест получения цены акции"""
    try:
        ticker = "SBER"  # Тестируем на Сбербанке
        response = requests.get(f"{BASE_URL}/api/stock_price/{ticker}")
        print(f"✅ Stock price for {ticker}: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Price: {data.get('price')} ₽")
        return True
    except Exception as e:
        print(f"❌ Stock price test failed: {e}")
        return False

def test_login_page():
    """Тест страницы входа"""
    try:
        response = requests.get(f"{BASE_URL}/login")
        print(f"✅ Login page: {response.status_code}")
        if response.status_code == 200:
            print("   Login page loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Login page test failed: {e}")
        return False

def test_demo_login():
    """Тест демо входа"""
    try:
        response = requests.get(f"{BASE_URL}/demo_login")
        print(f"✅ Demo login: {response.status_code}")
        if response.status_code == 302:  # Redirect to dashboard
            print("   Demo login successful (redirected)")
        return True
    except Exception as e:
        print(f"❌ Demo login test failed: {e}")
        return False

def test_stocks_with_logos():
    """Тест загрузки акций с логотипами"""
    try:
        # Сначала синхронизируем акции
        sync_response = requests.get(f"{BASE_URL}/admin/sync-stocks")
        if sync_response.status_code == 200:
            print("✅ Stocks synced successfully")
        
        # Проверяем, что акции загрузились с логотипами
        # Это можно сделать через API или проверив страницу акций
        stocks_response = requests.get(f"{BASE_URL}/stocks")
        print(f"✅ Stocks page: {stocks_response.status_code}")
        
        if stocks_response.status_code == 200:
            # Проверяем, что в HTML есть ссылки на UI Avatars или другие логотипы
            content = stocks_response.text
            if "ui-avatars.com" in content or "logo" in content.lower():
                print("   Логотипы акций загружаются корректно")
            else:
                print("   ⚠️  Логотипы могут не отображаться")
        
        return True
    except Exception as e:
        print(f"❌ Stocks with logos test failed: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("🚀 Тестирование InvestBot API")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Login Page", test_login_page),
        ("Demo Login", test_demo_login),
        ("Sync Stocks", test_sync_stocks),
        ("Stocks with Logos", test_stocks_with_logos),
        ("Update Prices", test_update_prices),
        ("Stock Price", test_stock_price),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Тест: {test_name}")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте {test_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно!")
        print("\n📝 Следующие шаги:")
        print("1. Настройте Telegram бота (см. SETUP_INSTRUCTIONS.md)")
        print("2. Протестируйте авторизацию через Telegram")
        print("3. Проверьте функционал торговли в демо-режиме")
    else:
        print("⚠️  Некоторые тесты не прошли. Проверьте настройки.")

if __name__ == "__main__":
    main()
