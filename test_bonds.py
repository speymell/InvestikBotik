#!/usr/bin/env python3
"""
Скрипт для тестирования функциональности облигаций
"""

import requests
import json
import sys
from datetime import datetime

def test_endpoint(url, description):
    """Тестирует конкретный endpoint"""
    print(f"\n🔍 Тестируем: {description}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'success':
                    print(f"✅ Успешно: {data.get('message', 'OK')}")
                    return True
                else:
                    print(f"❌ Ошибка: {data.get('message', 'Неизвестная ошибка')}")
                    return False
            except json.JSONDecodeError:
                print("✅ Успешно: HTML страница загружена")
                return True
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка соединения: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование функциональности облигаций InvestBot")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Базовый URL (измените на ваш)
    base_url = "http://localhost:5000"  # или ваш URL
    
    # Список тестов
    tests = [
        (f"{base_url}/health", "Health check"),
        (f"{base_url}/admin/test-bonds", "Тестирование API облигаций"),
        (f"{base_url}/admin/sync-bonds", "Синхронизация облигаций"),
        (f"{base_url}/stocks?type=bond", "Страница облигаций"),
        (f"{base_url}/stocks?type=share", "Страница акций"),
        (f"{base_url}/admin", "Админ-панель"),
        (f"{base_url}/portfolio-analysis", "Анализ портфеля"),
    ]
    
    # Выполняем тесты
    results = []
    for url, description in tests:
        success = test_endpoint(url, description)
        results.append((description, success))
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for description, success in results:
        status = "✅ ПРОШЕЛ" if success else "❌ ПРОВАЛЕН"
        print(f"{status:<12} {description}")
        if success:
            passed += 1
    
    print(f"\nИтого: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно! Система готова к работе.")
        return 0
    else:
        print("⚠️  Некоторые тесты провалены. Проверьте настройки.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
