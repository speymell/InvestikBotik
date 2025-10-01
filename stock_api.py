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
                            'description': f"Российская акция {shortname}",
                            'logo_url': self._get_logo_url(secid)
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
    
    def _get_logo_url(self, ticker):
        """Получает URL логотипа для тикера"""
        try:
            # Пытаемся получить логотип с MOEX API
            logo_url = self._fetch_logo_from_moex(ticker)
            if logo_url:
                return logo_url
        except Exception as e:
            logger.warning(f"Не удалось получить логотип с MOEX для {ticker}: {e}")
        
        # Последний fallback: генерируем логотип через UI Avatars API
        company_name = self._get_company_short_name(ticker)
        avatar_url = f"https://ui-avatars.com/api/?name={company_name}&size=96&background=random&color=fff&bold=true"
        
        logger.info(f"Используем сгенерированный логотип для {ticker}: {avatar_url}")
        return avatar_url
    
    def _fetch_logo_from_moex(self, ticker):
        """Пытается получить логотип компании с различных API"""
        try:
            # 1. Пробуем получить с MOEX (расширенная информация о компании)
            moex_url = f"{self.moex_base_url}/securities/{ticker}.json?iss.meta=off"
            response = self.session.get(moex_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # Ищем дополнительную информацию о компании
                if 'description' in data:
                    # MOEX может предоставлять ссылки на сайты компаний
                    pass
            
            # 2. Пробуем Alpha Vantage API (бесплатный, но нужен ключ)
            # alpha_logo = self._try_alpha_vantage_logo(ticker)
            # if alpha_logo:
            #     return alpha_logo
            
            # 3. Пробуем Yahoo Finance (неофициальное API)
            yahoo_logo = self._try_yahoo_finance_logo(ticker)
            if yahoo_logo:
                return yahoo_logo
                
            # 4. Пробуем Clearbit Logo API (бесплатный для базового использования)
            clearbit_logo = self._try_clearbit_logo(ticker)
            if clearbit_logo:
                return clearbit_logo
                
            # 5. Пробуем Financial Modeling Prep API (бесплатный лимит)
            fmp_logo = self._try_fmp_logo(ticker)
            if fmp_logo:
                return fmp_logo
                
        except Exception as e:
            logger.warning(f"Ошибка получения логотипа для {ticker}: {e}")
        
        return None
    
    def _try_yahoo_finance_logo(self, ticker):
        """Пытается получить логотип с Yahoo Finance"""
        try:
            # Yahoo Finance иногда предоставляет логотипы
            # Формат: https://logo.clearbit.com/{domain}
            company_domains = {
                'SBER': 'sberbank.ru',
                'GAZP': 'gazprom.ru', 
                'LKOH': 'lukoil.ru',
                'YNDX': 'yandex.ru',
                'ROSN': 'rosneft.ru',
                'NVTK': 'novatek.ru',
                'TCSG': 'tinkoff.ru',
                'VTBR': 'vtb.ru',
                'GMKN': 'nornickel.com',
                'MTSS': 'mts.ru'
            }
            
            domain = company_domains.get(ticker)
            if domain:
                logo_url = f"https://logo.clearbit.com/{domain}"
                # Проверяем, что логотип существует
                response = self.session.head(logo_url, timeout=3)
                if response.status_code == 200:
                    return logo_url
                    
        except Exception:
            pass
        return None
    
    def _try_clearbit_logo(self, ticker):
        """Пытается получить логотип через Clearbit Logo API"""
        try:
            # Clearbit предоставляет бесплатные логотипы по доменам
            company_domains = {
                'SBER': 'sberbank.com',
                'GAZP': 'gazprom.com', 
                'LKOH': 'lukoil.com',
                'YNDX': 'yandex.com',
                'ROSN': 'rosneft.com',
                'NVTK': 'novatek.ru',
                'TCSG': 'tinkoff.ru',
                'VTBR': 'vtb.ru',
                'GMKN': 'nornickel.com',
                'MTSS': 'mts.ru',
                'MAGN': 'mmk.ru',
                'NLMK': 'nlmk.com',
                'MOEX': 'moex.com',
                'AFLT': 'aeroflot.ru'
            }
            
            domain = company_domains.get(ticker)
            if domain:
                # Clearbit Logo API
                logo_url = f"https://logo.clearbit.com/{domain}?size=96"
                
                # Проверяем доступность логотипа
                response = self.session.head(logo_url, timeout=3)
                if response.status_code == 200:
                    return logo_url
                    
        except Exception:
            pass
        return None
    
    def _try_fmp_logo(self, ticker):
        """Пытается получить логотип через Financial Modeling Prep API"""
        try:
            # FMP предоставляет логотипы компаний
            # Нужно сопоставить российские тикеры с международными
            international_tickers = {
                'SBER': 'SBER.ME',  # Московская биржа
                'GAZP': 'GAZP.ME',
                'LKOH': 'LKOH.ME', 
                'ROSN': 'ROSN.ME',
                'NVTK': 'NVTK.ME',
                'GMKN': 'GMKN.ME',
                'MTSS': 'MTSS.ME'
            }
            
            international_ticker = international_tickers.get(ticker)
            if international_ticker:
                # FMP API для логотипов (бесплатный лимит 250 запросов в день)
                fmp_url = f"https://financialmodelingprep.com/image-stock/{international_ticker}.png"
                
                # Проверяем доступность
                response = self.session.head(fmp_url, timeout=3)
                if response.status_code == 200:
                    return fmp_url
                    
        except Exception:
            pass
        return None
    
    def _get_company_short_name(self, ticker):
        """Получает короткое название компании для генерации аватара"""
        name_map = {
            'SBER': 'СБ', 'GAZP': 'ГП', 'LKOH': 'ЛК', 'YNDX': 'ЯН',
            'ROSN': 'РН', 'NVTK': 'НВ', 'TCSG': 'ТК', 'VTBR': 'ВТБ',
            'GMKN': 'ГМК', 'MTSS': 'МТС', 'MAGN': 'ММК', 'NLMK': 'НЛМ',
            'CHMF': 'СМ', 'ALRS': 'АЛР', 'TATN': 'ТАТ', 'SNGS': 'СГС',
            'MOEX': 'МБ', 'AFLT': 'АФ', 'PHOR': 'ФОС', 'FEES': 'ФСК',
            'HYDR': 'ГЭС', 'IRAO': 'ИРА', 'PIKK': 'ПИК', 'FIVE': '5Р',
            'MGNT': 'МАГ', 'OZON': 'ОЗ', 'MAIL': 'МР', 'RTKM': 'РТК',
            'PLZL': 'ПЛЗ', 'RUAL': 'РУС'
        }
        
        return name_map.get(ticker, ticker[:2])
    
    def _get_fallback_stocks(self):
        """Резервный список акций на случай недоступности API"""
        fallback_stocks = [
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
        
        # Добавляем логотипы к fallback акциям
        for stock in fallback_stocks:
            stock['logo_url'] = self._get_logo_url(stock['ticker'])
        
        return fallback_stocks
    
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
                        if stock_data.get('description'):
                            existing_stock.description = stock_data['description']
                        if stock_data.get('logo_url'):
                            existing_stock.logo_url = stock_data['logo_url']
                        updated_count += 1
                    else:
                        # Добавляем новую акцию
                        new_stock = Stock(
                            ticker=stock_data['ticker'],
                            name=stock_data['name'],
                            price=stock_data['price'],
                            sector=stock_data['sector'],
                            description=stock_data.get('description', ''),
                            logo_url=stock_data.get('logo_url', '')
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
