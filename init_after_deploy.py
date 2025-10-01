#!/usr/bin/env python3
"""
Скрипт автоматической инициализации после деплоя
Запускается автоматически для настройки базы данных и загрузки данных
"""

import os
import sys
import logging
from flask import Flask
from database import db, Stock
from stock_api import stock_api_service
from config import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Создает приложение Flask для инициализации"""
    app = Flask(__name__)
    
    # Определяем конфигурацию
    config_name = os.environ.get('FLASK_ENV', 'production')
    app.config.from_object(config[config_name])
    
    # Инициализируем расширения
    db.init_app(app)
    
    return app

def init_database(app):
    """Инициализирует базу данных"""
    try:
        with app.app_context():
            # Создаем все таблицы
            db.create_all()
            logger.info("✅ База данных инициализирована")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        return False

def load_stocks_data(app):
    """Загружает данные об акциях"""
    try:
        with app.app_context():
            # Проверяем, есть ли уже акции в базе
            existing_stocks_count = Stock.query.count()
            
            if existing_stocks_count > 0:
                logger.info(f"📊 В базе уже есть {existing_stocks_count} акций")
                return True
            
            # Загружаем акции с MOEX
            logger.info("📥 Загружаем данные об акциях с MOEX...")
            result = stock_api_service.sync_stocks_to_database()
            
            if result and result.get('success'):
                logger.info(f"✅ Загружено акций: добавлено {result['added']}, обновлено {result['updated']}, всего {result['total']}")
                return True
            else:
                error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Не удалось получить результат'
                logger.error(f"❌ Ошибка загрузки акций: {error_msg}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки данных об акциях: {e}")
        return False

def check_environment():
    """Проверяет переменные окружения"""
    required_vars = ['SECRET_KEY']
    optional_vars = ['TELEGRAM_BOT_TOKEN', 'WEB_APP_URL']
    
    logger.info("🔍 Проверка переменных окружения...")
    
    # Проверяем обязательные переменные
    missing_required = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)
    
    if missing_required:
        logger.warning(f"⚠️  Отсутствуют обязательные переменные: {', '.join(missing_required)}")
        return False
    
    # Проверяем опциональные переменные
    missing_optional = []
    for var in optional_vars:
        if not os.environ.get(var):
            missing_optional.append(var)
    
    if missing_optional:
        logger.warning(f"⚠️  Отсутствуют опциональные переменные: {', '.join(missing_optional)}")
        logger.warning("   Telegram бот может не работать без этих настроек")
    
    logger.info("✅ Проверка переменных окружения завершена")
    return True

def main():
    """Основная функция инициализации"""
    logger.info("🚀 Начинаем автоматическую инициализацию InvestBot...")
    
    # Проверяем переменные окружения
    if not check_environment():
        logger.error("❌ Критические ошибки в настройках окружения")
        sys.exit(1)
    
    # Создаем приложение
    app = create_app()
    
    # Инициализируем базу данных
    if not init_database(app):
        logger.error("❌ Не удалось инициализировать базу данных")
        sys.exit(1)
    
    # Загружаем данные об акциях
    if not load_stocks_data(app):
        logger.warning("⚠️  Не удалось загрузить данные об акциях")
        logger.warning("   Приложение будет работать с демо-данными")
    
    logger.info("🎉 Инициализация завершена успешно!")
    logger.info("📝 Следующие шаги:")
    logger.info("   1. Настройте Telegram бота (токен и Web App)")
    logger.info("   2. Проверьте работу приложения")
    logger.info("   3. При необходимости обновите цены: /admin/update-prices")

if __name__ == "__main__":
    main()
