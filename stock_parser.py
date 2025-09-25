import requests
from bs4 import BeautifulSoup
import json
import time
from database import db, Stock
from app import app

class StockParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def parse_moex_stocks(self):
        """Парсинг акций с Московской биржи"""
        url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            stocks = []
            securities = data['securities']['data']
            
            for security in securities:
                if len(security) > 2:  # Проверяем, что есть необходимые данные
                    ticker = security[0]  # SECID
                    name = security[2]    # SHORTNAME
                    
                    if ticker and name:
                        stocks.append({
                            'ticker': ticker,
                            'name': name,
                            'price': 0.0  # Цена будет обновляться отдельно
                        })
            
            return stocks
            
        except Exception as e:
            print(f"Ошибка при парсинге MOEX: {e}")
            return []

    def get_stock_price(self, ticker):
        """Получение текущей цены акции"""
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data['securities']['data']:
                # Цена находится в поле PREVPRICE (предыдущая цена закрытия)
                price_data = data['securities']['data'][0]
                if len(price_data) > 3:
                    return float(price_data[3]) if price_data[3] else 0.0
            
            return 0.0
            
        except Exception as e:
            print(f"Ошибка при получении цены для {ticker}: {e}")
            return 0.0

    def update_database(self):
        """Обновление базы данных акциями"""
        with app.app_context():
            stocks_data = self.parse_moex_stocks()
            
            print(f"Найдено {len(stocks_data)} акций")
            
            for stock_data in stocks_data:
                # Проверяем, существует ли акция в базе
                existing_stock = Stock.query.filter_by(ticker=stock_data['ticker']).first()
                
                if not existing_stock:
                    # Создаем новую запись
                    new_stock = Stock(
                        ticker=stock_data['ticker'],
                        name=stock_data['name'],
                        price=stock_data['price']
                    )
                    db.session.add(new_stock)
                else:
                    # Обновляем название, если оно изменилось
                    existing_stock.name = stock_data['name']
                
                # Добавляем небольшую задержку, чтобы не перегружать API
                time.sleep(0.1)
            
            try:
                db.session.commit()
                print("База данных успешно обновлена")
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка при обновлении базы данных: {e}")

    def update_stock_prices(self):
        """Обновление цен акций"""
        with app.app_context():
            stocks = Stock.query.all()
            
            for stock in stocks:
                price = self.get_stock_price(stock.ticker)
                stock.price = price
                
                # Добавляем задержку между запросами
                time.sleep(0.2)
            
            try:
                db.session.commit()
                print("Цены акций обновлены")
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка при обновлении цен: {e}")

if __name__ == "__main__":
    parser = StockParser()
    parser.update_database()
    parser.update_stock_prices()
