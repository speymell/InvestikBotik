"""
WSGI файл для запуска приложения в продакшене
Используется с Gunicorn или другими WSGI серверами
"""

import os
import logging
from app import create_app
from database import db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем приложение для продакшена
app = create_app('production')

# Автоматическая инициализация при первом запуске
with app.app_context():
    try:
        # Создаем все таблицы
        db.create_all()
        logger.info("✅ База данных инициализирована")
        
        # Проверяем и загружаем данные об акциях
        from database import Stock
        from stock_api import stock_api_service
        
        existing_stocks_count = Stock.query.count()
        
        if existing_stocks_count == 0:
            logger.info("📥 Загружаем начальные данные об акциях...")
            try:
                result = stock_api_service.sync_stocks_to_database()
                if result and result.get('success'):
                    logger.info(f"✅ Загружено {result['total']} акций с MOEX")
                else:
                    logger.warning("⚠️  Не удалось загрузить данные с MOEX, используем fallback данные")
            except Exception as e:
                logger.warning(f"⚠️  Ошибка загрузки данных: {e}")
        else:
            logger.info(f"📊 В базе уже есть {existing_stocks_count} акций")
            
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        # В случае ошибки создаем минимальные fallback данные
        try:
            if Stock.query.count() == 0:
                from stock_api import stock_api_service
                fallback_stocks = stock_api_service._get_fallback_stocks()
                
                for stock_data in fallback_stocks[:5]:  # Добавляем только 5 основных акций
                    stock = Stock(
                        ticker=stock_data['ticker'],
                        name=stock_data['name'],
                        price=stock_data['price'],
                        sector=stock_data['sector'],
                        description=stock_data['description'],
                        logo_url=stock_data.get('logo_url', '')
                    )
                    db.session.add(stock)
                
                db.session.commit()
                logger.info("✅ Добавлены fallback данные об акциях")
        except Exception as fallback_error:
            logger.error(f"❌ Ошибка добавления fallback данных: {fallback_error}")

if __name__ == "__main__":
    app.run()
