from flask import Flask
import os
from database import db, User, Account, Stock, Transaction
from routes import init_routes
from config import config

def create_app(config_name=None):
    """Фабрика приложений Flask"""
    app = Flask(__name__)
    
    # Определяем конфигурацию
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Настройка для Telegram Web App
    @app.after_request
    def add_telegram_headers(response):
        """Добавляем заголовки для Telegram Web App"""
        # Разрешаем встраивание в iframe Telegram
        response.headers['X-Frame-Options'] = 'ALLOWALL'
        # Альтернатива для X-Frame-Options
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://web.telegram.org https://telegram.org"
        # CORS для Telegram
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    # Инициализируем расширения
    db.init_app(app)
    
    # Инициализируем маршруты
    init_routes(app)
    return app

app = create_app()

if __name__ == '__main__':
    # Запускаем планировщик в продакшене
    if not app.debug:
        try:
            from scheduler import scheduler
            scheduler.start()
            print("✅ Планировщик автоматического обновления запущен")
        except Exception as e:
            print(f"⚠️ Ошибка запуска планировщика: {e}")
    
    with app.app_context():
        db.create_all()
    app.run(debug=True)
