"""
WSGI файл для запуска приложения в продакшене
Используется с Gunicorn или другими WSGI серверами
"""

import os
from app import create_app
from database import db

# Создаем приложение для продакшена
app = create_app('production')

# На первом деплое в Render создадим таблицы, если их ещё нет
with app.app_context():
    try:
        from database import Stock
        db.create_all()
        print("Database tables created successfully!")
        
        # Добавим несколько тестовых акций, если их нет
        if Stock.query.count() == 0:
            test_stocks = [
                Stock(ticker='SBER', name='ПАО Сбербанк', price=280.50),
                Stock(ticker='GAZP', name='ПАО Газпром', price=128.75),
                Stock(ticker='LKOH', name='ЛУКОЙЛ', price=6850.00),
                Stock(ticker='YNDX', name='Яндекс', price=3420.00),
                Stock(ticker='ROSN', name='Роснефть', price=565.20),
                Stock(ticker='NVTK', name='НОВАТЭК', price=1125.40),
                Stock(ticker='TCSG', name='TCS Group', price=2890.60),
                Stock(ticker='RUAL', name='РУСАЛ', price=45.85),
                Stock(ticker='MAGN', name='ММК', price=52.30),
                Stock(ticker='GMKN', name='ГМК Норникель', price=15680.00)
            ]
            
            for stock in test_stocks:
                db.session.add(stock)
            
            db.session.commit()
            print(f"Added {len(test_stocks)} test stocks to database!")
        
    except Exception as e:
        print(f"Error creating database tables: {e}")
        # Не падаем при ошибке подключения к БД на этапе билда

if __name__ == "__main__":
    app.run()
