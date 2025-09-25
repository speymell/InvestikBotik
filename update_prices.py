"""
Скрипт для автоматического обновления цен акций
Можно запускать по расписанию (cron/Task Scheduler)
"""

import sys
import os
from datetime import datetime
from app import create_app
from stock_parser import StockParser

def update_stock_prices():
    """Обновление цен акций"""
    app = create_app()
    
    with app.app_context():
        print(f"[{datetime.now()}] Начинаем обновление цен акций...")
        
        parser = StockParser()
        try:
            parser.update_stock_prices()
            print(f"[{datetime.now()}] Цены акций успешно обновлены")
        except Exception as e:
            print(f"[{datetime.now()}] Ошибка при обновлении цен: {e}")
            sys.exit(1)

if __name__ == "__main__":
    update_stock_prices()
