#!/usr/bin/env python3
"""
Скрипт для принудительного обновления логотипов всех акций в базе данных
"""

from app import app, db
from database import Stock
from stock_api import stock_api_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_all_logos():
    """Обновляет логотипы для всех акций в базе данных"""
    with app.app_context():
        stocks = Stock.query.all()
        updated_count = 0
        
        logger.info(f"Найдено {len(stocks)} акций для обновления логотипов")
        
        for stock in stocks:
            try:
                # Генерируем новый URL логотипа
                new_logo_url = stock_api_service._get_logo_url(stock.ticker)
                
                if new_logo_url:
                    stock.logo_url = new_logo_url
                    updated_count += 1
                    logger.info(f"✅ {stock.ticker}: {new_logo_url}")
                else:
                    logger.warning(f"⚠️ {stock.ticker}: не удалось сгенерировать логотип")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка для {stock.ticker}: {e}")
                continue
        
        # Сохраняем изменения
        db.session.commit()
        logger.info(f"\n✨ Обновлено {updated_count} из {len(stocks)} логотипов")
        logger.info("🎉 Все логотипы успешно обновлены в базе данных!")
        
        return updated_count

if __name__ == '__main__':
    logger.info("🚀 Запуск обновления логотипов акций...")
    count = update_all_logos()
    logger.info(f"✅ Готово! Обновлено {count} логотипов")
