"""
Сервис для получения реальных данных о российских акциях
Использует API MOEX (Московская биржа) и другие источники
"""

import requests
import json
from datetime import datetime, timedelta
from database import Stock, db
import logging

logger = logging.getLogger(__name__)

class StockAPIService:
    """Сервис для работы с API акций"""
    
    def __init__(self):
        self.moex_base_url = "https://iss.moex.com/iss"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'InvestBot/1.0'
        })
    
    def get_all_stocks(self):
        """Получает список всех акций с MOEX"""
        try:
            # Получаем список акций с основного рынка - упрощенный запрос
            url = f"{self.moex_base_url}/engines/stock/markets/shares/securities.json"
            
            # Добавляем параметры для получения всех данных
            params = {
                'iss.meta': 'off',  # Отключаем метаданные
                'iss.only': 'securities',  # Только секции securities
                'securities.columns': 'SECID,SHORTNAME,PREVPRICE,SECTYPE,REGNUMBER'  # Только нужные колонки
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            logger.info(f"MOEX API response status: {response.status_code}")
            logger.info(f"MOEX API URL: {response.url}")
            
            data = response.json()
            
            if 'securities' not in data or 'data' not in data['securities']:
                logger.error("Неверный формат ответа от MOEX API")
                return []
            
            securities_data = data['securities']['data']
            columns = data['securities']['columns']
            
            stocks = []
            
            for row in securities_data:
                try:
                    # Создаем словарь из колонок и данных
                    security = dict(zip(columns, row))
                    
                    # Фильтруем только акции (не облигации, ETF и т.д.)
                    sectype = security.get('SECTYPE', '')
                    secid = security.get('SECID', '')
                    shortname = security.get('SHORTNAME', '')
                    prevprice = security.get('PREVPRICE')
                    
                    # Более гибкая фильтрация
                    if (secid and shortname and 
                        ('share' in sectype.lower() or sectype == '1') and
                        len(secid) <= 6):  # Российские тикеры обычно до 6 символов
                        
                        try:
                            price = float(prevprice) if prevprice and prevprice != '' else 0.0
                        except (ValueError, TypeError):
                            price = 0.0
                        
                        stocks.append({
                            'ticker': secid,
                            'name': shortname,
                            'price': price,
                            'sector': self._get_sector_by_ticker(secid),
                            'description': f"Российская акция {shortname}"
                        })
                        
                except Exception as e:
                    logger.warning(f"Ошибка обработки акции: {e}")
                    continue
            
            logger.info(f"Получено {len(stocks)} акций с MOEX")
            return stocks
            
        except Exception as e:
            logger.error(f"Ошибка получения акций с MOEX: {e}")
            return self._get_fallback_stocks()
    
    def _get_sector_by_ticker(self, ticker):
        """Определяет сектор по тикеру (упрощенная логика)"""
        sector_map = {
            'SBER': 'Банки', 'VTBR': 'Банки', 'TCSG': 'Банки', 'CBOM': 'Банки',
            'GAZP': 'Нефть и газ', 'LKOH': 'Нефть и газ', 'ROSN': 'Нефть и газ', 'NVTK': 'Нефть и газ',
            'TATN': 'Нефть и газ', 'SNGS': 'Нефть и газ', 'BANEP': 'Нефть и газ', 'TRNFP': 'Нефть и газ',
            'GMKN': 'Металлургия', 'NLMK': 'Металлургия', 'MAGN': 'Металлургия', 'CHMF': 'Металлургия',
            'RUAL': 'Металлургия', 'ALRS': 'Металлургия', 'PLZL': 'Металлургия', 'SELG': 'Металлургия',
            'YNDX': 'IT', 'MAIL': 'IT', 'OZON': 'IT', 'VKCO': 'IT',
            'MTSS': 'Телеком', 'RTKM': 'Телеком', 'TTLK': 'Телеком',
            'FIVE': 'Ритейл', 'MGNT': 'Ритейл', 'DSKY': 'Ритейл', 'FIXP': 'Ритейл',
            'FEES': 'Энергетика', 'HYDR': 'Энергетика', 'IRAO': 'Энергетика', 'MSNG': 'Энергетика',
            'UPRO': 'Энергетика', 'LSNG': 'Энергетика',
            'PIKK': 'Недвижимость', 'LSRG': 'Недвижимость', 'ETALON': 'Недвижимость',
            'MOEX': 'Финансы', 'SPBE': 'Финансы',
            'AFLT': 'Транспорт', 'FESH': 'Транспорт',
            'PHOR': 'Химия', 'AKRN': 'Химия', 'NKNC': 'Химия'
        }
        
        return sector_map.get(ticker, 'Прочее')
    
    def _get_fallback_stocks(self):
        """Резервный список акций на случай недоступности API"""
        return [
            {'ticker': 'SBER', 'name': 'ПАО Сбербанк', 'price': 280.50, 'sector': 'Банки', 'description': 'Крупнейший банк России'},
            {'ticker': 'GAZP', 'name': 'ПАО Газпром', 'price': 128.75, 'sector': 'Нефть и газ', 'description': 'Крупнейшая газовая компания'},
            {'ticker': 'LKOH', 'name': 'ЛУКОЙЛ', 'price': 6850.00, 'sector': 'Нефть и газ', 'description': 'Нефтяная компания'},
            {'ticker': 'YNDX', 'name': 'Яндекс', 'price': 3420.00, 'sector': 'IT', 'description': 'IT-компания'},
            {'ticker': 'ROSN', 'name': 'Роснефть', 'price': 565.20, 'sector': 'Нефть и газ', 'description': 'Нефтяная компания'},
            {'ticker': 'NVTK', 'name': 'НОВАТЭК', 'price': 1125.40, 'sector': 'Нефть и газ', 'description': 'Газовая компания'},
            {'ticker': 'TCSG', 'name': 'TCS Group', 'price': 2890.60, 'sector': 'Банки', 'description': 'Банк Тинькофф'},
            {'ticker': 'VTBR', 'name': 'ВТБ', 'price': 85.60, 'sector': 'Банки', 'description': 'Банк ВТБ'},
            {'ticker': 'GMKN', 'name': 'ГМК Норникель', 'price': 15680.00, 'sector': 'Металлургия', 'description': 'Горно-металлургическая компания'},
            {'ticker': 'MTSS', 'name': 'МТС', 'price': 285.40, 'sector': 'Телеком', 'description': 'Мобильные телесистемы'}
        ]
    
    def update_stock_prices(self):
        """Обновляет цены существующих акций"""
        try:
            # Получаем список тикеров из базы
            existing_stocks = Stock.query.all()
            tickers = [stock.ticker for stock in existing_stocks]
            
            if not tickers:
                return False
            
            # Получаем актуальные цены
            updated_count = 0
            for ticker in tickers:
                try:
                    price = self._get_stock_price(ticker)
                    if price and price > 0:
                        stock = Stock.query.filter_by(ticker=ticker).first()
                        if stock:
                            stock.price = price
                            updated_count += 1
                except Exception as e:
                    logger.warning(f"Ошибка обновления цены для {ticker}: {e}")
                    continue
            
            db.session.commit()
            logger.info(f"Обновлены цены для {updated_count} акций")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления цен: {e}")
            db.session.rollback()
            return False
    
    def _get_stock_price(self, ticker):
        """Получает текущую цену акции"""
        try:
            url = f"{self.moex_base_url}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if ('securities' in data and 'data' in data['securities'] and 
                len(data['securities']['data']) > 0):
                
                columns = data['securities']['columns']
                row = data['securities']['data'][0]
                security = dict(zip(columns, row))
                
                return float(security.get('PREVPRICE', 0)) or float(security.get('LAST', 0))
            
            return None
            
        except Exception as e:
            logger.warning(f"Ошибка получения цены для {ticker}: {e}")
            return None
    
    def sync_stocks_to_database(self):
        """Синхронизирует акции с базой данных"""
        try:
            stocks_data = self.get_all_stocks()
            
            if not stocks_data:
                logger.error("Не удалось получить данные об акциях")
                return False
            
            added_count = 0
            updated_count = 0
            
            for stock_data in stocks_data:
                try:
                    existing_stock = Stock.query.filter_by(ticker=stock_data['ticker']).first()
                    
                    if existing_stock:
                        # Обновляем существующую акцию
                        existing_stock.name = stock_data['name']
                        existing_stock.price = stock_data['price']
                        existing_stock.sector = stock_data['sector']
                        if stock_data['description']:
                            existing_stock.description = stock_data['description']
                        updated_count += 1
                    else:
                        # Добавляем новую акцию
                        new_stock = Stock(
                            ticker=stock_data['ticker'],
                            name=stock_data['name'],
                            price=stock_data['price'],
                            sector=stock_data['sector'],
                            description=stock_data['description']
                        )
                        db.session.add(new_stock)
                        added_count += 1
                        
                except Exception as e:
                    logger.warning(f"Ошибка обработки акции {stock_data.get('ticker', 'unknown')}: {e}")
                    continue
            
            db.session.commit()
            
            total_stocks = Stock.query.count()
            logger.info(f"Синхронизация завершена. Добавлено: {added_count}, обновлено: {updated_count}, всего: {total_stocks}")
            
            return {
                'success': True,
                'added': added_count,
                'updated': updated_count,
                'total': total_stocks
            }
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации акций: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

# Глобальный экземпляр сервиса
stock_api_service = StockAPIService()
