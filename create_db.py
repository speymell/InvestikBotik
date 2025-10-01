"""
Скрипт для создания базы данных с нуля
"""

from app import app
from database import db

with app.app_context():
    # Удаляем все таблицы
    db.drop_all()
    print("Dropped all tables")
    
    # Создаем все таблицы заново
    db.create_all()
    print("Created all tables")
    
    # Проверяем, что таблицы созданы
    from database import Stock, User, Account, Transaction
    
    # Добавляем несколько тестовых акций
    test_stocks = [
        Stock(ticker='SBER', name='ПАО Сбербанк', price=280.50, 
              logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Sberbank_Logo.svg/200px-Sberbank_Logo.svg.png',
              sector='Банки', description='Крупнейший банк России и Восточной Европы'),
        Stock(ticker='GAZP', name='ПАО Газпром', price=128.75,
              logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Gazprom-Logo.svg/200px-Gazprom-Logo.svg.png',
              sector='Нефть и газ', description='Крупнейшая газовая компания мира'),
        Stock(ticker='LKOH', name='ЛУКОЙЛ', price=6850.00,
              logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Lukoil_logo.svg/200px-Lukoil_logo.svg.png',
              sector='Нефть и газ', description='Одна из крупнейших нефтяных компаний мира'),
        Stock(ticker='YNDX', name='Яндекс', price=3420.00,
              logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Yandex_icon.svg/200px-Yandex_icon.svg.png',
              sector='IT', description='Российская IT-компания, поисковая система'),
        Stock(ticker='ROSN', name='Роснефть', price=565.20,
              logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Rosneft_logo.svg/200px-Rosneft_logo.svg.png',
              sector='Нефть и газ', description='Крупнейшая нефтяная компания России')
    ]
    
    for stock in test_stocks:
        db.session.add(stock)
    
    db.session.commit()
    print(f"Added {len(test_stocks)} test stocks")
    
    print("Database created successfully!")
