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
        
        # Проверяем, есть ли новые колонки в таблице stock
        try:
            # Пытаемся выполнить запрос с новыми колонками
            db.session.execute(db.text("SELECT logo_url, sector, description FROM stock LIMIT 1"))
            print("New columns already exist in stock table")
        except Exception as e:
            print(f"Adding new columns to stock table: {e}")
            # Добавляем новые колонки
            try:
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN logo_url VARCHAR(255)"))
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN sector VARCHAR(100)"))
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN description TEXT"))
                db.session.commit()
                print("Successfully added new columns to stock table")
            except Exception as alter_error:
                print(f"Error adding columns: {alter_error}")
                db.session.rollback()
        
        db.create_all()
        print("Database tables created successfully!")
        
        # Добавим несколько тестовых акций, если их нет
        if Stock.query.count() == 0:
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
                      sector='Нефть и газ', description='Крупнейшая нефтяная компания России'),
                Stock(ticker='NVTK', name='НОВАТЭК', price=1125.40,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Novatek_logo.svg/200px-Novatek_logo.svg.png',
                      sector='Нефть и газ', description='Крупнейший производитель природного газа в России'),
                Stock(ticker='TCSG', name='TCS Group', price=2890.60,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Tinkoff_Bank_logo.svg/200px-Tinkoff_Bank_logo.svg.png',
                      sector='Банки', description='Частный банк, лидер в сфере цифрового банкинга'),
                Stock(ticker='RUAL', name='РУСАЛ', price=45.85,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Rusal_logo.svg/200px-Rusal_logo.svg.png',
                      sector='Металлургия', description='Крупнейший производитель алюминия в России'),
                Stock(ticker='MAGN', name='ММК', price=52.30,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/MMK_logo.svg/200px-MMK_logo.svg.png',
                      sector='Металлургия', description='Магнитогорский металлургический комбинат'),
                Stock(ticker='GMKN', name='ГМК Норникель', price=15680.00,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Nornickel_logo.svg/200px-Nornickel_logo.svg.png',
                      sector='Металлургия', description='Крупнейший производитель никеля и палладия'),
                Stock(ticker='PLZL', name='Полюс', price=12450.00,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Polyus_logo.svg/200px-Polyus_logo.svg.png',
                      sector='Металлургия', description='Крупнейший производитель золота в России'),
                Stock(ticker='TATN', name='Татнефть', price=685.20,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Tatneft_logo.svg/200px-Tatneft_logo.svg.png',
                      sector='Нефть и газ', description='Крупная нефтяная компания Татарстана'),
                Stock(ticker='SNGS', name='Сургутнефтегаз', price=28.45,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Surgutneftegas_logo.svg/200px-Surgutneftegas_logo.svg.png',
                      sector='Нефть и газ', description='Нефтегазовая компания Западной Сибири'),
                Stock(ticker='VTBR', name='ВТБ', price=85.60,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/VTB_logo.svg/200px-VTB_logo.svg.png',
                      sector='Банки', description='Второй по величине банк России'),
                Stock(ticker='ALRS', name='АЛРОСА', price=78.90,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Alrosa_logo.svg/200px-Alrosa_logo.svg.png',
                      sector='Металлургия', description='Крупнейшая алмазодобывающая компания мира'),
                Stock(ticker='CHMF', name='Северсталь', price=1245.80,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Severstal_logo.svg/200px-Severstal_logo.svg.png',
                      sector='Металлургия', description='Крупная металлургическая компания'),
                Stock(ticker='NLMK', name='НЛМК', price=185.40,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/NLMK_logo.svg/200px-NLMK_logo.svg.png',
                      sector='Металлургия', description='Новолипецкий металлургический комбинат'),
                Stock(ticker='MOEX', name='Московская Биржа', price=198.50,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Moscow_Exchange_logo.svg/200px-Moscow_Exchange_logo.svg.png',
                      sector='Финансы', description='Крупнейшая биржевая группа России'),
                Stock(ticker='AFLT', name='Аэрофлот', price=45.20,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Aeroflot_logo.svg/200px-Aeroflot_logo.svg.png',
                      sector='Транспорт', description='Национальный авиаперевозчик России'),
                Stock(ticker='PHOR', name='ФосАгро', price=6890.00,
                      logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/PhosAgro_logo.svg/200px-PhosAgro_logo.svg.png',
                      sector='Химия', description='Ведущий производитель фосфорных удобрений')
            ]
            
            for stock in test_stocks:
                db.session.add(stock)
            
            db.session.commit()
            print(f"Added {len(test_stocks)} test stocks to database!")
        else:
            # Обновляем существующие акции новыми данными, если у них нет логотипов
            existing_stocks = Stock.query.filter(Stock.logo_url.is_(None)).all()
            if existing_stocks:
                print(f"Updating {len(existing_stocks)} existing stocks with logos and descriptions...")
                
                # Словарь с данными для обновления
                stock_updates = {
                    'SBER': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Sberbank_Logo.svg/200px-Sberbank_Logo.svg.png', 'sector': 'Банки', 'description': 'Крупнейший банк России и Восточной Европы'},
                    'GAZP': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Gazprom-Logo.svg/200px-Gazprom-Logo.svg.png', 'sector': 'Нефть и газ', 'description': 'Крупнейшая газовая компания мира'},
                    'LKOH': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Lukoil_logo.svg/200px-Lukoil_logo.svg.png', 'sector': 'Нефть и газ', 'description': 'Одна из крупнейших нефтяных компаний мира'},
                    'YNDX': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Yandex_icon.svg/200px-Yandex_icon.svg.png', 'sector': 'IT', 'description': 'Российская IT-компания, поисковая система'},
                    'ROSN': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Rosneft_logo.svg/200px-Rosneft_logo.svg.png', 'sector': 'Нефть и газ', 'description': 'Крупнейшая нефтяная компания России'},
                    'NVTK': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Novatek_logo.svg/200px-Novatek_logo.svg.png', 'sector': 'Нефть и газ', 'description': 'Крупнейший производитель природного газа в России'},
                    'TCSG': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Tinkoff_Bank_logo.svg/200px-Tinkoff_Bank_logo.svg.png', 'sector': 'Банки', 'description': 'Частный банк, лидер в сфере цифрового банкинга'},
                    'RUAL': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Rusal_logo.svg/200px-Rusal_logo.svg.png', 'sector': 'Металлургия', 'description': 'Крупнейший производитель алюминия в России'},
                    'MAGN': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/MMK_logo.svg/200px-MMK_logo.svg.png', 'sector': 'Металлургия', 'description': 'Магнитогорский металлургический комбинат'},
                    'GMKN': {'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Nornickel_logo.svg/200px-Nornickel_logo.svg.png', 'sector': 'Металлургия', 'description': 'Крупнейший производитель никеля и палладия'}
                }
                
                for stock in existing_stocks:
                    if stock.ticker in stock_updates:
                        update_data = stock_updates[stock.ticker]
                        stock.logo_url = update_data['logo_url']
                        stock.sector = update_data['sector']
                        stock.description = update_data['description']
                
                db.session.commit()
                print("Updated existing stocks with logos and descriptions!")
        
    except Exception as e:
        print(f"Error creating database tables: {e}")
        # Не падаем при ошибке подключения к БД на этапе билда

if __name__ == "__main__":
    app.run()
