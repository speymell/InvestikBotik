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
    
    # Инициализируем расширения
    db.init_app(app)
    
    # Инициализируем маршруты
    init_routes(app)
    
    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

