"""
Скрипт для загрузки всех российских акций с Московской биржи
Использует официальное API MOEX ISS
"""

import requests
import time
from database import db, Stock
from app import app

def load_all_moex_stocks():
    """Загружает все акции с MOEX и сохраняет в базу данных"""
    
    print("Начинаем загрузку акций с Московской биржи...")
    
    # URL для получения списка всех акций на основном рынке
    moex_url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
    
    try:
        response = requests.get(moex_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Извлекаем данные об акциях
        securities = data.get('securities', {})
        columns = securities.get('columns', [])
        rows = securities.get('data', [])
        
        if not columns or not rows:
            print("Ошибка: Нет данных от MOEX")
            return
        
        # Находим индексы нужных колонок
        secid_idx = columns.index('SECID') if 'SECID' in columns else 0
        shortname_idx = columns.index('SHORTNAME') if 'SHORTNAME' in columns else 1
        prevprice_idx = columns.index('PREVPRICE') if 'PREVPRICE' in columns else -1
        
        print(f"Найдено {len(rows)} акций")
        
        with app.app_context():
            added_count = 0
            updated_count = 0
            
            for row in rows:
                try:
                    ticker = row[secid_idx]
                    name = row[shortname_idx] if shortname_idx < len(row) else ticker
                    price = float(row[prevprice_idx]) if prevprice_idx >= 0 and prevprice_idx < len(row) and row[prevprice_idx] else 0.0
                    
                    # Пропускаем акции без названия
                    if not ticker or not name:
                        continue
                    
                    # Определяем сектор
                    sector = get_sector_by_ticker(ticker)
                    
                    # Проверяем, существует ли акция
                    existing_stock = Stock.query.filter_by(ticker=ticker).first()
                    
                    if existing_stock:
                        # Обновляем существующую акцию
                        existing_stock.name = name
                        existing_stock.price = price if price > 0 else existing_stock.price
                        if not existing_stock.sector:
                            existing_stock.sector = sector
                        updated_count += 1
                    else:
                        # Добавляем новую акцию
                        new_stock = Stock(
                            ticker=ticker,
                            name=name,
                            price=price,
                            sector=sector,
                            description=f"Акция {name} торгуется на Московской бирже"
                        )
                        db.session.add(new_stock)
                        added_count += 1
                    
                    # Добавляем небольшую задержку
                    if (added_count + updated_count) % 50 == 0:
                        time.sleep(0.5)
                        
                except (ValueError, IndexError) as e:
                    print(f"Ошибка обработки строки {row}: {e}")
                    continue
            
            try:
                db.session.commit()
                print(f"\n✅ Успешно загружено:")
                print(f"   - Новых акций: {added_count}")
                print(f"   - Обновлено акций: {updated_count}")
                print(f"   - Всего обработано: {len(rows)}")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Ошибка сохранения в базу данных: {e}")
                
    except requests.RequestException as e:
        print(f"❌ Ошибка при загрузке данных с MOEX: {e}")


def get_sector_by_ticker(ticker):
    """Определяет сектор по тикеру акции"""
    sectors = {
        # Банки
        'SBER': 'Банки', 'VTBR': 'Банки', 'TCSG': 'Банки', 'CBOM': 'Банки',
        'SBERP': 'Банки', 'BSPB': 'Банки', 'SNGSP': 'Банки',
        
        # Нефть и газ
        'GAZP': 'Нефть и газ', 'LKOH': 'Нефть и газ', 'ROSN': 'Нефть и газ', 
        'NVTK': 'Нефть и газ', 'TATN': 'Нефть и газ', 'SNGS': 'Нефть и газ',
        'TATNP': 'Нефть и газ', 'TRNFP': 'Нефть и газ',
        
        # Металлургия
        'GMKN': 'Металлургия', 'RUAL': 'Металлургия', 'MAGN': 'Металлургия',
        'NLMK': 'Металлургия', 'CHMF': 'Металлургия', 'ALRS': 'Металлургия',
        'PLZL': 'Металлургия', 'POSI': 'Металлургия',
        
        # IT
        'YNDX': 'IT', 'MAIL': 'IT', 'OZON': 'IT', 'VKCO': 'IT',
        'FIXP': 'IT', 'HEADHUNTER': 'IT',
        
        # Телеком
        'MTSS': 'Телеком', 'RTKM': 'Телеком', 'MGTS': 'Телеком',
        
        # Энергетика
        'FEES': 'Энергетика', 'HYDR': 'Энергетика', 'IRAO': 'Энергетика',
        'LSRG': 'Энергетика', 'MSRS': 'Энергетика', 'UPRO': 'Энергетика',
        'ENPG': 'Энергетика', 'TGKA': 'Энергетика', 'TGKB': 'Энергетика',
        
        # Транспорт
        'AFLT': 'Транспорт', 'FESH': 'Транспорт', 'FLOT': 'Транспорт',
        
        # Финансы
        'MOEX': 'Финансы', 'SPBE': 'Финансы',
        
        # Химия
        'PHOR': 'Химия', 'AKRN': 'Химия', 'NKNC': 'Химия', 'NKNCP': 'Химия',
        
        # Недвижимость
        'PIKK': 'Недвижимость', 'LSRG': 'Недвижимость', 'ETLN': 'Недвижимость',
        'SMLT': 'Недвижимость',
        
        # Ритейл
        'FIVE': 'Ритейл', 'MGNT': 'Ритейл', 'OZON': 'Ритейл', 'FIXP': 'Ритейл',
        'LENT': 'Ритейл',
        
        # Машиностроение
        'KMAZ': 'Машиностроение', 'AVTOVAZ': 'Машиностроение',
        
        # Фармацевтика
        'APTK': 'Фармацевтика', 'PRMB': 'Фармацевтика',
        
        # Медиа
        'TRMK': 'Медиа',
    }
    return sectors.get(ticker, 'Прочие')


def update_stock_prices():
    """Обновляет цены всех акций в базе данных"""
    print("\nОбновление цен акций...")
    
    moex_url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
    
    try:
        response = requests.get(moex_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        securities = data.get('securities', {})
        columns = securities.get('columns', [])
        rows = securities.get('data', [])
        
        if not columns or not rows:
            print("Ошибка: Нет данных о ценах")
            return
        
        secid_idx = columns.index('SECID') if 'SECID' in columns else 0
        prevprice_idx = columns.index('PREVPRICE') if 'PREVPRICE' in columns else -1
        
        # Создаем словарь цен
        price_updates = {}
        for row in rows:
            try:
                ticker = row[secid_idx]
                price = float(row[prevprice_idx]) if prevprice_idx >= 0 and prevprice_idx < len(row) and row[prevprice_idx] else None
                
                if ticker and price and price > 0:
                    price_updates[ticker] = price
            except (ValueError, IndexError):
                continue
        
        with app.app_context():
            stocks = Stock.query.all()
            updated_count = 0
            
            for stock in stocks:
                if stock.ticker in price_updates:
                    stock.price = price_updates[stock.ticker]
                    updated_count += 1
            
            try:
                db.session.commit()
                print(f"✅ Обновлено цен: {updated_count} из {len(stocks)}")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Ошибка обновления цен: {e}")
                
    except requests.RequestException as e:
        print(f"❌ Ошибка при загрузке цен: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Загрузка акций с Московской биржи")
    print("=" * 60)
    
    load_all_moex_stocks()
    update_stock_prices()
    
    print("\n" + "=" * 60)
    print("  Загрузка завершена!")
    print("=" * 60)
