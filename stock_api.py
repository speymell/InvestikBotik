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

    def get_all_bonds(self):
        """Получает список всех облигаций с MOEX"""
        try:
            # Облигации на рынке bonds
            url = f"{self.moex_base_url}/engines/stock/markets/bonds/securities.json"
            params = {
                'iss.meta': 'off',
                'iss.only': 'securities',
                'securities.columns': 'SECID,SHORTNAME,FACEVALUE,PREVPRICE'
            }
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if 'securities' not in data or 'data' not in data['securities']:
                logger.error("Неверный формат ответа от MOEX API (bonds)")
                return []
            bonds_data = data['securities']['data']
            columns = data['securities']['columns']

            secid_idx = columns.index('SECID') if 'SECID' in columns else None
            shortname_idx = columns.index('SHORTNAME') if 'SHORTNAME' in columns else None
            facevalue_idx = columns.index('FACEVALUE') if 'FACEVALUE' in columns else None
            prevprice_idx = columns.index('PREVPRICE') if 'PREVPRICE' in columns else None

            bonds = []
            for row in bonds_data:
                try:
                    ticker = row[secid_idx] if secid_idx is not None else None
                    name = row[shortname_idx] if shortname_idx is not None else ticker
                    face_value = float(row[facevalue_idx]) if facevalue_idx is not None and row[facevalue_idx] else None
                    prevprice = None
                    if prevprice_idx is not None and row[prevprice_idx] not in (None, ''):
                        try:
                            prevprice = float(row[prevprice_idx])
                        except (ValueError, TypeError):
                            prevprice = None

                    # Цена облигации на MOEX часто в процентах от номинала
                    price = 0.0
                    if prevprice and face_value:
                        price = (prevprice / 100.0) * face_value

                    if ticker and name:
                        bonds.append({
                            'ticker': ticker,
                            'name': name,
                            'price': price,
                            'sector': 'Облигации',
                            'description': f"Российская облигация {name}",
                            'logo_url': self._get_logo_url(ticker),
                            'instrument_type': 'bond',
                            'face_value': face_value
                        })
                except Exception as e:
                    logger.warning(f"Ошибка обработки облигации: {e}")
                    continue

            logger.info(f"Получено {len(bonds)} облигаций с MOEX")
            return bonds

        except Exception as e:
            logger.error(f"Ошибка получения облигаций с MOEX: {e}")
            return []
    
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
        # Просто генерируем логотип через UI Avatars API для стабильности
        import hashlib
        import urllib.parse
        
        # Генерируем цвет на основе хэша тикера
        hash_object = hashlib.md5(ticker.encode())
        hash_hex = hash_object.hexdigest()
        bg_color = hash_hex[:6]  # Берем первые 6 символов хэша как цвет
        
        # Используем тикер как текст на логотипе
        avatar_url = f"https://ui-avatars.com/api/?name={urllib.parse.quote(ticker)}&size=96&background={bg_color}&color=fff&bold=true&font-size=0.45"
        
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
            {'ticker': 'YNDX', 'name': 'Яндекс', 'price': 3835.50, 'sector': 'IT', 'description': 'IT-компания'},
            {'ticker': 'ROSN', 'name': 'Роснефть', 'price': 565.20, 'sector': 'Нефть и газ', 'description': 'Нефтяная компания'},
            {'ticker': 'NVTK', 'name': 'НОВАТЭК', 'price': 1125.40, 'sector': 'Нефть и газ', 'description': 'Газовая компания'},
            {'ticker': 'TCSG', 'name': 'TCS Group', 'price': 2890.60, 'sector': 'Банки', 'description': 'Банк Тинькофф'},
            {'ticker': 'VTBR', 'name': 'ВТБ', 'price': 85.60, 'sector': 'Банки', 'description': 'Банк ВТБ'},
            {'ticker': 'GMKN', 'name': 'ГМК Норникель', 'price': 15680.00, 'sector': 'Металлургия', 'description': 'Горно-металлургическая компания'},
            {'ticker': 'MTSS', 'name': 'МТС', 'price': 285.40, 'sector': 'Телеком', 'description': 'Мобильные телесистемы'}
        ]
        
        # Пытаемся получить реальные цены для fallback акций
        logger.info("Попытка обновить fallback цены с MOEX...")
        for stock_data in fallback_stocks:
            try:
                real_price = self._get_stock_price(stock_data['ticker'])
                if real_price and real_price > 0:
                    stock_data['price'] = real_price
                    logger.info(f"Обновлена цена {stock_data['ticker']}: {real_price}")
            except Exception as e:
                logger.warning(f"Не удалось обновить цену для {stock_data['ticker']}: {e}")
        
        # Добавляем логотипы к fallback акциям
        for stock in fallback_stocks:
            stock['logo_url'] = self._get_logo_url(stock['ticker'])
        
        return fallback_stocks
    
    def get_stock_history(self, ticker, days=1):
        """Получает историю цен акции с MOEX"""
        try:
            from datetime import datetime, timedelta
            
            # Вычисляем даты
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Форматируем даты для API
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Нормализуем тикер (например YNDX -> YDEX, если требуется)
            norm_ticker = self._normalize_ticker(ticker) or ticker
            # Собираем список площадок: сначала динамические, затем стандартная TQBR
            dynamic_boards = self._get_ticker_boards(norm_ticker) or []
            boards_to_try = []
            for b in dynamic_boards + ['TQBR']:
                if b and b not in boards_to_try:
                    boards_to_try.append(b)

            # Пробуем последовательно все доступные площадки, пока не получим историю
            for board in boards_to_try:
                try:
                    url = f"{self.moex_base_url}/history/engines/stock/markets/shares/boards/{board}/securities/{norm_ticker}.json"
                    params = {
                        'from': start_str,
                        'till': end_str,
                        'iss.meta': 'off',
                        'iss.only': 'history',
                        'history.columns': 'TRADEDATE,CLOSE'
                    }
                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    if 'history' in data and 'data' in data['history'] and data['history']['data']:
                        history_data = []
                        for row in data['history']['data']:
                            if row and len(row) >= 2 and row[1]:
                                history_data.append({'date': row[0], 'price': float(row[1])})
                        logger.info(f"Получено {len(history_data)} точек истории для {ticker} с площадки {board}")
                        if history_data:
                            return history_data
                except Exception as e:
                    logger.warning(f"Ошибка получения истории {ticker} с площадки {board}: {e}")
                    continue

            logger.warning(f"Нет данных истории для {ticker} (SECID={norm_ticker}) ни на одной площадке")
            return []
            
        except Exception as e:
            logger.error(f"Ошибка получения истории для {ticker}: {e}")
            return []

    def get_intraday_history(self, ticker, interval=10, hours=24):
        """Получает внутридневную историю (свечи) за последние hours часов.
        interval: 1, 10, 60 (минуты)
        Возвращает список [{'time': ISO, 'price': float}].
        """
        try:
            from datetime import datetime, timedelta
            now = datetime.now()
            start_dt = now - timedelta(hours=hours)
            start_str = start_dt.strftime('%Y-%m-%d')
            end_str = now.strftime('%Y-%m-%d')

            # Нормализуем тикер и собираем доски
            norm_ticker = self._normalize_ticker(ticker) or ticker
            dynamic_boards = self._get_ticker_boards(norm_ticker) or []
            boards_to_try = []
            for b in dynamic_boards + ['TQBR', 'TQTF', 'TQPI']:
                if b and b not in boards_to_try:
                    boards_to_try.append(b)

            for board in boards_to_try:
                try:
                    url = f"{self.moex_base_url}/engines/stock/markets/shares/boards/{board}/securities/{norm_ticker}/candles.json"
                    params = {
                        'from': start_str,
                        'till': end_str,
                        'interval': interval,
                        'iss.meta': 'off',
                        'iss.only': 'candles',
                        # не все инстансы уважают columns, но это не критично
                        'candles.columns': 'begin,close'
                    }
                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    if 'candles' in data and 'data' in data['candles'] and data['candles']['data']:
                        cols = data['candles']['columns']
                        begin_idx = cols.index('begin') if 'begin' in cols else None
                        close_idx = cols.index('close') if 'close' in cols else None
                        result = []
                        for row in data['candles']['data']:
                            if row is None:
                                continue
                            try:
                                t = row[begin_idx] if begin_idx is not None else None
                                p = row[close_idx] if close_idx is not None else None
                                if t and p is not None:
                                    # Фильтруем по часовому окну
                                    try:
                                        # MOEX возвращает 'YYYY-MM-DD HH:MM:SS'
                                        t_dt = datetime.fromisoformat(t.replace(' ', 'T'))
                                        if t_dt < start_dt:
                                            continue
                                    except Exception:
                                        pass
                                    result.append({'time': t, 'price': float(p)})
                            except Exception:
                                continue
                        if result:
                            logger.info(f"Получено {len(result)} intraday-свечей для {ticker} (SECID={norm_ticker}) с {board} (interval={interval})")
                            return result
                except Exception as e:
                    logger.warning(f"Ошибка intraday для {ticker} на {board}: {e}")
                    continue

            logger.warning(f"Intraday-данные для {ticker} (SECID={norm_ticker}) не найдены")
            return []
        except Exception as e:
            logger.error(f"Ошибка intraday получения для {ticker}: {e}")
            return []
    
    def update_stock_prices(self):
        """Обновляет цены существующих акций"""
        try:
            # Получаем список тикеров из базы
            existing_stocks = Stock.query.all()
            if not existing_stocks:
                return False

            updated_count = 0
            for stock in existing_stocks:
                try:
                    if getattr(stock, 'instrument_type', 'share') == 'bond':
                        price = self._get_bond_price(stock.ticker, getattr(stock, 'face_value', None))
                    else:
                        price = self._get_stock_price(stock.ticker)
                    if price and price > 0:
                        stock.price = price
                        updated_count += 1
                except Exception as e:
                    logger.warning(f"Ошибка обновления цены для {stock.ticker}: {e}")
                    continue
            
            db.session.commit()
            logger.info(f"Обновлены цены для {updated_count} акций")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления цен: {e}")
            db.session.rollback()
            return False
    
    def get_multiple_stock_prices(self, tickers, timeout=10):
        """Получает цены нескольких акций одним запросом"""
        try:
            # Ограничиваем количество тикеров в одном запросе для стабильности
            if len(tickers) > 20:
                # Разбиваем на части по 20 акций
                all_prices = {}
                for i in range(0, len(tickers), 20):
                    batch = tickers[i:i+20]
                    batch_prices = self.get_multiple_stock_prices(batch, timeout)
                    all_prices.update(batch_prices)
                return all_prices
            
            # Нормализуем тикеры (например YNDX -> YDEX)
            norm_map = {}
            normalized_tickers_list = []
            normalized_seen = set()
            for t in tickers:
                norm = self._normalize_ticker(t) or t
                norm_map[t] = norm
                if norm not in normalized_seen:
                    normalized_seen.add(norm)
                    normalized_tickers_list.append(norm)

            # Пробуем разные торговые площадки
            boards = ['TQBR', 'TQPI', 'TQTF']  # Основные площадки для акций
            prices = {}
            
            for board in boards:
                if len(prices) == len(tickers):  # Если все цены уже получены
                    break
                    
                try:
                    tickers_str = ','.join(normalized_tickers_list)
                    url = f"{self.moex_base_url}/engines/stock/markets/shares/boards/{board}/securities.json?securities={tickers_str}"
                    
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()
                    
                    data = response.json()
                    logger.info(f"Получен ответ MOEX API для площадки {board}, акций: {len(tickers)}")
                    
                    # Обрабатываем marketdata (текущие торговые данные)
                    if ('marketdata' in data and 'data' in data['marketdata'] and 
                        len(data['marketdata']['data']) > 0):
                        
                        columns = data['marketdata']['columns']
                        secid_idx = columns.index('SECID') if 'SECID' in columns else None
                        
                        # Ищем индексы нужных полей
                        last_idx = columns.index('LAST') if 'LAST' in columns else None
                        close_idx = columns.index('CLOSE') if 'CLOSE' in columns else None
                        open_idx = columns.index('OPEN') if 'OPEN' in columns else None
                        
                        for row in data['marketdata']['data']:
                            if secid_idx is not None:
                                secid = row[secid_idx]
                                # Сопоставляем SECID обратно к исходному тикеру
                                original = None
                                for orig, norm in norm_map.items():
                                    if norm == secid:
                                        original = orig
                                        break
                                if not original:
                                    continue
                                if original in prices:
                                    continue
                                price = None
                                
                                # Приоритет: LAST > CLOSE > OPEN
                                if last_idx is not None and row[last_idx] is not None:
                                    price = float(row[last_idx])
                                elif close_idx is not None and row[close_idx] is not None:
                                    price = float(row[close_idx])
                                elif open_idx is not None and row[open_idx] is not None:
                                    price = float(row[open_idx])
                                
                                if price and price > 0:
                                    prices[original] = price
                                    logger.info(f"Получена цена {original} (SECID={secid}) с площадки {board}: {price}")
                except Exception as e:
                    logger.warning(f"Ошибка получения данных с площадки {board}: {e}")
                    continue
            
            # Для акций, которые не найдены, пробуем индивидуальные запросы
            missing_tickers = [t for t in tickers if t not in prices]
            if missing_tickers:
                logger.info(f"Пробуем индивидуальные запросы для {missing_tickers}")
                for ticker in missing_tickers:
                    try:
                        price = self._get_stock_price(ticker, timeout=5)
                        if price and price > 0:
                            prices[ticker] = price
                    except Exception as e:
                        logger.warning(f"Не удалось получить цену для {ticker}: {e}")
            
            return prices
            
        except Exception as e:
            logger.error(f"Ошибка получения массовых цен: {e}")
            return {}

    def get_multiple_stock_trade_metrics(self, tickers, timeout=10):
        """Возвращает метрики торгов для нескольких акций одним запросом.
        Результат: dict[ticker] = { 'price': float, 'turnover': float|None, 'volume': int|None, 'change_pct': float|None }
        """
        try:
            if not tickers:
                return {}
            # Ограничиваем размер батча для стабильности
            if len(tickers) > 20:
                merged = {}
                for i in range(0, len(tickers), 20):
                    batch = tickers[i:i+20]
                    part = self.get_multiple_stock_trade_metrics(batch, timeout)
                    merged.update(part)
                return merged

            # Нормализация тикеров -> SECID
            norm_map = {}
            normalized = []
            seen = set()
            for t in tickers:
                n = self._normalize_ticker(t) or t
                norm_map[t] = n
                if n not in seen:
                    seen.add(n)
                    normalized.append(n)

            boards = ['TQBR', 'TQPI', 'TQTF']
            result = {}
            for board in boards:
                if len(result) == len(tickers):
                    break
                try:
                    tickers_str = ','.join(normalized)
                    url = f"{self.moex_base_url}/engines/stock/markets/shares/boards/{board}/securities.json?securities={tickers_str}"
                    resp = self.session.get(url, timeout=timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    if not ('marketdata' in data and 'data' in data['marketdata'] and data['marketdata']['data']):
                        continue
                    cols = data['marketdata']['columns']
                    idx = {
                        'SECID': cols.index('SECID') if 'SECID' in cols else None,
                        'LAST': cols.index('LAST') if 'LAST' in cols else None,
                        'CLOSE': cols.index('CLOSE') if 'CLOSE' in cols else None,
                        'OPEN': cols.index('OPEN') if 'OPEN' in cols else None,
                        'VALTODAY': cols.index('VALTODAY') if 'VALTODAY' in cols else None,
                        'VALTODAY_RUR': cols.index('VALTODAY_RUR') if 'VALTODAY_RUR' in cols else None,
                        'VOLTODAY': cols.index('VOLTODAY') if 'VOLTODAY' in cols else None,
                        'LASTCHANGEPRC': cols.index('LASTCHANGEPRC') if 'LASTCHANGEPRC' in cols else None,
                        'LASTTOPREVPRICE': cols.index('LASTTOPREVPRICE') if 'LASTTOPREVPRICE' in cols else None,
                    }
                    for row in data['marketdata']['data']:
                        secid = row[idx['SECID']] if idx['SECID'] is not None else None
                        if not secid:
                            continue
                        # Map SECID to original ticker
                        original = None
                        for orig, n in norm_map.items():
                            if n == secid:
                                original = orig
                                break
                        if not original or original in result:
                            continue
                        # Price
                        price = None
                        for key in ('LAST', 'CLOSE', 'OPEN'):
                            k = idx[key]
                            if k is not None and row[k] is not None:
                                try:
                                    price = float(row[k])
                                    break
                                except Exception:
                                    pass
                        # Turnover (prefer RUB)
                        turnover = None
                        if idx['VALTODAY_RUR'] is not None and row[idx['VALTODAY_RUR']] is not None:
                            try:
                                turnover = float(row[idx['VALTODAY_RUR']])
                            except Exception:
                                turnover = None
                        elif idx['VALTODAY'] is not None and row[idx['VALTODAY']] is not None:
                            try:
                                turnover = float(row[idx['VALTODAY']])
                            except Exception:
                                turnover = None
                        # Volume
                        volume = None
                        if idx['VOLTODAY'] is not None and row[idx['VOLTODAY']] is not None:
                            try:
                                volume = int(row[idx['VOLTODAY']])
                            except Exception:
                                try:
                                    volume = int(float(row[idx['VOLTODAY']]))
                                except Exception:
                                    volume = None
                        # Change percent
                        change_pct = None
                        if idx['LASTCHANGEPRC'] is not None and row[idx['LASTCHANGEPRC']] is not None:
                            try:
                                change_pct = float(row[idx['LASTCHANGEPRC']])
                            except Exception:
                                change_pct = None
                        elif idx['LASTTOPREVPRICE'] is not None and row[idx['LASTTOPREVPRICE']] is not None:
                            try:
                                # LASTTOPREVPRICE уже в %, по спецификации MOEX
                                change_pct = float(row[idx['LASTTOPREVPRICE']])
                            except Exception:
                                change_pct = None

                        if price is not None and price > 0:
                            result[original] = {
                                'price': price,
                                'turnover': turnover,
                                'volume': volume,
                                'change_pct': change_pct,
                            }
                except Exception as e:
                    logger.warning(f"Ошибка метрик на борде {board}: {e}")
                    continue

            # Индивидуальные попытки для отсутствующих тикеров (только цена)
            missing = [t for t in tickers if t not in result]
            for t in missing:
                try:
                    p = self._get_stock_price(t, timeout=5)
                    if p and p > 0:
                        result[t] = {'price': p, 'turnover': None, 'volume': None, 'change_pct': None}
                except Exception:
                    pass
            return result
        except Exception as e:
            logger.error(f"Ошибка получения метрик: {e}")
            return {}

    def get_multiple_bond_prices(self, tickers, face_values_map=None, timeout=10):
        """Получает цены нескольких облигаций одним запросом (в рублях)
        face_values_map: dict[ticker] -> face_value
        """
        try:
            if len(tickers) > 20:
                all_prices = {}
                for i in range(0, len(tickers), 20):
                    batch = tickers[i:i+20]
                    batch_prices = self.get_multiple_bond_prices(batch, face_values_map, timeout)
                    all_prices.update(batch_prices)
                return all_prices

            boards = ['TQCB', 'TQOB', 'TQIR']
            prices = {}
            for board in boards:
                if len(prices) == len(tickers):
                    break
                try:
                    tickers_str = ','.join(tickers)
                    url = f"{self.moex_base_url}/engines/stock/markets/bonds/boards/{board}/securities.json?securities={tickers_str}"
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()
                    data = response.json()

                    if ('marketdata' in data and 'data' in data['marketdata'] and len(data['marketdata']['data']) > 0):
                        columns = data['marketdata']['columns']
                        secid_idx = columns.index('SECID') if 'SECID' in columns else None
                        last_idx = columns.index('LAST') if 'LAST' in columns else None
                        close_idx = columns.index('CLOSE') if 'CLOSE' in columns else None
                        open_idx = columns.index('OPEN') if 'OPEN' in columns else None
                        for row in data['marketdata']['data']:
                            if secid_idx is not None and row[secid_idx] in tickers and row[secid_idx] not in prices:
                                t = row[secid_idx]
                                raw = None
                                if last_idx is not None and row[last_idx] is not None:
                                    raw = float(row[last_idx])
                                elif close_idx is not None and row[close_idx] is not None:
                                    raw = float(row[close_idx])
                                elif open_idx is not None and row[open_idx] is not None:
                                    raw = float(row[open_idx])
                                if raw is not None:
                                    fv = (face_values_map or {}).get(t)
                                    price_rub = (raw / 100.0 * fv) if fv else raw
                                    prices[t] = price_rub
                except Exception as e:
                    logger.warning(f"Ошибка получения данных облигаций с площадки {board}: {e}")
                    continue
            return prices
        except Exception as e:
            logger.error(f"Ошибка получения массовых цен облигаций: {e}")
            return {}

    def _get_stock_price(self, ticker, timeout=10):
        """Получает текущую цену акции"""
        try:
            orig_ticker = ticker
            ticker = self._normalize_ticker(ticker) or ticker
            # Сначала пытаемся определить доступные площадки для данного тикера динамически,
            # затем добавляем стандартные как запасной вариант
            dynamic_boards = self._get_ticker_boards(ticker) or []
            # Пробуем разные торговые площадки (уникально, сохраняя порядок)
            boards = []
            for b in dynamic_boards + ['TQBR', 'TQPI', 'TQTF']:
                if b and b not in boards:
                    boards.append(b)
            
            for board in boards:
                try:
                    url = f"{self.moex_base_url}/engines/stock/markets/shares/boards/{board}/securities/{ticker}.json"
                    
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()
                    
                    data = response.json()
                    logger.info(f"Получен ответ MOEX API для {orig_ticker} (SECID={ticker}) с площадки {board}, секции: {list(data.keys())}")
                    
                    # Пробуем получить цену с этой площадки
                    price = self._extract_price_from_data(data, ticker, board)
                    if price and price > 0:
                        return price
                        
                except Exception as e:
                    logger.warning(f"Ошибка получения {ticker} с площадки {board}: {e}")
                    continue
            
            # Если не получилось ни с одной площадки
            logger.error(f"Не удалось получить цену {ticker} ни с одной площадки")
            return None

        except Exception as e:
            logger.error(f"Общая ошибка получения цены {ticker}: {e}")
            return None

    def _get_bond_price(self, ticker, face_value=None, timeout=10):
        """Получает текущую цену облигации (в рублях, переводя из % от номинала)"""
        try:
            boards = ['TQCB', 'TQOB', 'TQIR']
            for board in boards:
                try:
                    url = f"{self.moex_base_url}/engines/stock/markets/bonds/boards/{board}/securities/{ticker}.json"
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()
                    data = response.json()
                    price = self._extract_bond_price_from_data(data, ticker, board, face_value)
                    if price and price > 0:
                        return price
                except Exception as e:
                    logger.warning(f"Ошибка получения {ticker} (bond) с площадки {board}: {e}")
                    continue
            logger.error(f"Не удалось получить цену облигации {ticker} ни с одной площадки")
            return None
        except Exception as e:
            logger.error(f"Общая ошибка получения цены облигации {ticker}: {e}")
            return None
    
    def _extract_price_from_data(self, data, ticker, board):
        """Извлекает цену из данных MOEX API"""
        try:
            
            # 1. Пытаемся получить цену из marketdata (текущие торговые данные)
            if ('marketdata' in data and 'data' in data['marketdata'] and 
                len(data['marketdata']['data']) > 0):
                
                columns = data['marketdata']['columns']
                row = data['marketdata']['data'][0]
                market = dict(zip(columns, row))
                
                # Расширенный приоритет цен: LAST > LCURRENTPRICE > CLOSE > OPEN > WAPRICE > MARKETPRICE2
                price = (
                    market.get('LAST')
                    or market.get('LCURRENTPRICE')
                    or market.get('CLOSE')
                    or market.get('OPEN')
                    or market.get('WAPRICE')
                    or market.get('MARKETPRICE2')
                )
                if price and price > 0:
                    logger.info(f"Получена цена {ticker} из marketdata с площадки {board}: {price}")
                    return float(price)
            
            # 2. Пытаемся получить цену из securities (информация о ценных бумагах)
            if ('securities' in data and 'data' in data['securities'] and 
                len(data['securities']['data']) > 0):
                
                columns = data['securities']['columns']
                row = data['securities']['data'][0]
                security = dict(zip(columns, row))
                
                # Пытаемся получить цену из разных полей (на случай разных наборов колонок)
                price = (
                    security.get('PREVPRICE')
                    or security.get('LAST')
                    or security.get('MARKETPRICE')
                    or security.get('LCURRENTPRICE')
                    or security.get('MARKETPRICE2')
                    or security.get('CLOSE')
                    or security.get('OPEN')
                    or security.get('PREVADMITTEDQUOTE')
                )
                if price and price > 0:
                    logger.info(f"Получена цена {ticker} из securities с площадки {board}: {price}")
                    return float(price)
            
            # 3. Если не получилось получить из основного запроса, пробуем историю для этой площадки
            logger.info(f"Пытаемся получить цену {ticker} из истории торгов площадки {board}")
            history_url = f"{self.moex_base_url}/history/engines/stock/markets/shares/boards/{board}/securities/{ticker}.json"
            params = {'iss.meta': 'off', 'iss.only': 'history', 'history.columns': 'TRADEDATE,CLOSE', 'limit': 1}
            
            response = self.session.get(history_url, params=params, timeout=5)
            response.raise_for_status()
            
            hist_data = response.json()
            if 'history' in hist_data and 'data' in hist_data['history'] and len(hist_data['history']['data']) > 0:
                row = hist_data['history']['data'][0]
                if row and len(row) >= 2 and row[1]:
                    logger.info(f"Получена цена {ticker} из истории площадки {board}: {row[1]}")
                    return float(row[1])
            
            logger.warning(f"Не удалось получить цену для {ticker} с площадки {board}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения цены для {ticker}: {e}")
            return None

    def _normalize_ticker(self, ticker: str) -> str:
        """Нормализует тикер для MOEX (например, YNDX -> YDEX). Возвращает SECID для запросов."""
        try:
            mapping = {
                # Яндекс: исторически YNDX, текущий SECID на MOEX – YDEX
                'YNDX': 'YDEX',
                # Можно добавлять сюда другие переименованные тикеры при необходимости
            }
            return mapping.get(ticker.upper(), ticker)
        except Exception:
            return ticker

    def _get_ticker_boards(self, ticker, timeout=5):
        """Возвращает список доступных торговых площадок (BOARDID) для тикера"""
        try:
            url = f"{self.moex_base_url}/securities/{ticker}.json"
            params = {
                'iss.meta': 'off',
                'iss.only': 'boards',
                'boards.columns': 'BOARDID'
            }
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            boards = []
            if 'boards' in data and 'data' in data['boards']:
                for row in data['boards']['data']:
                    if row and row[0]:
                        boards.append(row[0])
            # Логируем для отладки
            if boards:
                logger.info(f"Для {ticker} найдены площадки: {boards}")
            return boards
        except Exception as e:
            logger.warning(f"Не удалось получить список площадок для {ticker}: {e}")
            return []
    
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

    def sync_bonds_to_database(self):
        """Синхронизирует облигации с базой данных"""
        try:
            bonds_data = self.get_all_bonds()
            if not bonds_data:
                logger.error("Не удалось получить данные об облигациях")
                return {'success': False, 'error': 'no_data'}

            added_count = 0
            updated_count = 0
            for bond in bonds_data:
                try:
                    existing = Stock.query.filter_by(ticker=bond['ticker']).first()
                    if existing:
                        existing.name = bond['name']
                        existing.price = bond['price']
                        existing.sector = bond['sector']
                        existing.description = bond.get('description') or existing.description
                        existing.logo_url = bond.get('logo_url') or existing.logo_url
                        # Новые поля
                        if hasattr(existing, 'instrument_type'):
                            existing.instrument_type = 'bond'
                        if hasattr(existing, 'face_value'):
                            existing.face_value = bond.get('face_value')
                        updated_count += 1
                    else:
                        new_sec = Stock(
                            ticker=bond['ticker'],
                            name=bond['name'],
                            price=bond['price'],
                            sector=bond['sector'],
                            description=bond.get('description', ''),
                            logo_url=bond.get('logo_url', ''),
                            instrument_type='bond',
                            face_value=bond.get('face_value')
                        )
                        db.session.add(new_sec)
                        added_count += 1
                except Exception as e:
                    logger.warning(f"Ошибка обработки облигации {bond.get('ticker', 'unknown')}: {e}")
                    continue

            db.session.commit()
            total = Stock.query.count()
            logger.info(f"Синхронизация облигаций завершена. Добавлено: {added_count}, обновлено: {updated_count}, всего бумаг: {total}")
            return {'success': True, 'added': added_count, 'updated': updated_count, 'total': total}
        except Exception as e:
            logger.error(f"Ошибка синхронизации облигаций: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

# Глобальный экземпляр сервиса
stock_api_service = StockAPIService()
