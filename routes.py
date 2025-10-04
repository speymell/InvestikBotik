from flask import render_template, request, jsonify, redirect, url_for, session
from database import db, User, Account, Stock, Transaction
from utils import calculate_portfolio_stats, get_top_stocks
import datetime
import logging

logger = logging.getLogger(__name__)

def init_routes(app):
    
    @app.route('/health')
    def health():
        """Health check endpoint для Render"""
        return jsonify({'status': 'ok', 'message': 'InvestBot is running'})
    
    @app.route('/admin/sync-stocks')
    def sync_stocks():
        """Синхронизация акций с MOEX API"""
        try:
            from stock_api import stock_api_service
            
            # Получаем данные с MOEX
            result = stock_api_service.sync_stocks_to_database()
            
            if result and result.get('success'):
                return jsonify({
                    'status': 'success',
                    'message': f'Синхронизация завершена. Добавлено: {result["added"]}, обновлено: {result["updated"]}, всего: {result["total"]} акций'
                })
            else:
                error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Не удалось получить результат'
                return jsonify({
                    'status': 'error',
                    'message': f'Ошибка синхронизации: {error_msg}'
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Ошибка синхронизации: {str(e)}'
            }), 500
    
    @app.route('/admin/update-prices')
    def update_prices():
        """Обновление цен акций"""
        try:
            from stock_api import stock_api_service
            import logging
            
            logger = logging.getLogger(__name__)
            logger.info("Начинаем обновление цен акций...")
            
            # Получаем все акции из БД
            stocks = Stock.query.all()
            updated_count = 0
            failed_count = 0
            
            for stock in stocks:
                try:
                    # Получаем актуальную цену с MOEX (учитываем тип инструмента)
                    if getattr(stock, 'instrument_type', 'share') == 'bond':
                        price = stock_api_service._get_bond_price(stock.ticker, getattr(stock, 'face_value', None))
                    else:
                        price = stock_api_service._get_stock_price(stock.ticker)
                    if price and price > 0:
                        old_price = stock.price
                        stock.price = price
                        updated_count += 1
                        logger.info(f"Обновлена цена {stock.ticker}: {old_price} → {price}")
                    else:
                        failed_count += 1
                        logger.warning(f"Не удалось получить цену для {stock.ticker}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Ошибка обновления {stock.ticker}: {e}")
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Обновлено: {updated_count} акций, ошибок: {failed_count}, всего: {len(stocks)}'
            })
                
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Ошибка обновления цен: {str(e)}'
            }), 500
    
    @app.route('/admin/test-moex')
    def test_moex():
        """Тестирование MOEX API"""
        try:
            from stock_api import stock_api_service
            
            # Тестируем получение акций
            stocks = stock_api_service.get_all_stocks()
            
            return jsonify({
                'status': 'success',
                'message': f'Получено {len(stocks)} акций с MOEX',
                'sample_stocks': stocks[:5] if stocks else [],
                'total_count': len(stocks)
            })
            
        except Exception as e:
            import traceback
            return jsonify({
                'status': 'error',
                'message': f'Ошибка тестирования MOEX: {str(e)}',
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/admin')
    def admin_panel():
        """Админ-панель"""
        return render_template('admin.html')
    
    @app.route('/admin/stats')
    def admin_stats():
        """Статистика для админ-панели"""
        try:
            from database import User, Account, Transaction
            
            stats = {
                'stocks': Stock.query.count(),
                'users': User.query.count(),
                'accounts': Account.query.count(),
                'transactions': Transaction.query.count()
            }
            
            return jsonify({
                'status': 'success',
                'stats': stats
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/admin/stocks-list')
    def admin_stocks_list():
        """Список акций для админ-панели"""
        try:
            stocks = Stock.query.order_by(Stock.id.desc()).limit(20).all()
            
            stocks_data = []
            for stock in stocks:
                stocks_data.append({
                    'ticker': stock.ticker,
                    'name': stock.name,
                    'sector': stock.sector,
                    'price': stock.price,
                    'updated_at': stock.updated_at.isoformat() if hasattr(stock, 'updated_at') and stock.updated_at else None
                })
            
            return jsonify({
                'status': 'success',
                'stocks': stocks_data
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/test')
    def test():
        """Test endpoint"""
        return jsonify({'status': 'ok', 'message': 'Routes are working', 'routes': 'initialized'})
    
    @app.route('/migrate')
    def migrate():
        """Принудительная миграция БД"""
        try:
            from database import Stock
            
            # Сначала откатываем любую незавершенную транзакцию
            try:
                db.session.rollback()
            except Exception:
                pass
            
            # Проверяем, есть ли новые колонки
            try:
                result = db.session.execute(db.text("SELECT logo_url FROM stock LIMIT 1"))
                db.session.commit()
                return jsonify({'status': 'success', 'message': 'Columns already exist'})
            except Exception:
                db.session.rollback()
                
                # Добавляем колонки по одной с отдельными транзакциями
                try:
                    # Добавляем logo_url
                    try:
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN logo_url VARCHAR(255)"))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        if "already exists" not in str(e).lower():
                            print(f"Error adding logo_url: {e}")
                    
                    # Добавляем sector
                    try:
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN sector VARCHAR(100)"))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        if "already exists" not in str(e).lower():
                            print(f"Error adding sector: {e}")
                    
                    # Добавляем description
                    try:
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN description TEXT"))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        if "already exists" not in str(e).lower():
                            print(f"Error adding description: {e}")
                    
                    # Добавляем instrument_type
                    try:
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN instrument_type VARCHAR(20) DEFAULT 'share'"))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        if "already exists" not in str(e).lower():
                            print(f"Error adding instrument_type: {e}")
                    
                    # Добавляем face_value
                    try:
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN face_value FLOAT"))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        if "already exists" not in str(e).lower():
                            print(f"Error adding face_value: {e}")
                    
                    # Обновляем существующие записи
                    stocks_to_update = [
                        ('SBER', 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Sberbank_Logo.svg/200px-Sberbank_Logo.svg.png', 'Банки', 'Крупнейший банк России и Восточной Европы'),
                        ('GAZP', 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Gazprom-Logo.svg/200px-Gazprom-Logo.svg.png', 'Нефть и газ', 'Крупнейшая газовая компания мира'),
                        ('LKOH', 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Lukoil_logo.svg/200px-Lukoil_logo.svg.png', 'Нефть и газ', 'Одна из крупнейших нефтяных компаний мира'),
                        ('YNDX', 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Yandex_icon.svg/200px-Yandex_icon.svg.png', 'IT', 'Российская IT-компания, поисковая система'),
                        ('ROSN', 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Rosneft_logo.svg/200px-Rosneft_logo.svg.png', 'Нефть и газ', 'Крупнейшая нефтяная компания России'),
                        ('NVTK', 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Novatek_logo.svg/200px-Novatek_logo.svg.png', 'Нефть и газ', 'Крупнейший производитель природного газа в России'),
                        ('TCSG', 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Tinkoff_Bank_logo.svg/200px-Tinkoff_Bank_logo.svg.png', 'Банки', 'Частный банк, лидер в сфере цифрового банкинга'),
                        ('RUAL', 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Rusal_logo.svg/200px-Rusal_logo.svg.png', 'Металлургия', 'Крупнейший производитель алюминия в России'),
                        ('MAGN', 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/MMK_logo.svg/200px-MMK_logo.svg.png', 'Металлургия', 'Магнитогорский металлургический комбинат'),
                        ('GMKN', 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Nornickel_logo.svg/200px-Nornickel_logo.svg.png', 'Металлургия', 'Крупнейший производитель никеля и палладия')
                    ]
                    
                    # Обновляем существующие записи
                    try:
                        for ticker, logo_url, sector, description in stocks_to_update:
                            db.session.execute(db.text(
                                "UPDATE stock SET logo_url = :logo_url, sector = :sector, description = :description WHERE ticker = :ticker"
                            ), {
                                'ticker': ticker,
                                'logo_url': logo_url,
                                'sector': sector,
                                'description': description
                            })
                        
                        db.session.commit()
                        return jsonify({'status': 'success', 'message': 'Migration completed successfully'})
                    except Exception as e:
                        db.session.rollback()
                        return jsonify({'status': 'error', 'message': f'Update failed: {str(e)}'})
                    
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': f'Migration failed: {str(e)}'})
                    
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            return jsonify({'status': 'error', 'message': f'Migration error: {str(e)}'})
    
    @app.route('/add_stocks')
    def add_stocks():
        """Добавить недостающие акции"""
        try:
            from database import Stock
            
            # Откатываем любую незавершенную транзакцию
            try:
                db.session.rollback()
            except Exception:
                pass
            
            # Список всех акций для добавления
            all_stocks = [
                ('SBER', 'ПАО Сбербанк', 280.50, 'https://logos-world.net/wp-content/uploads/2020/12/Sberbank-Logo.png', 'Банки', 'Крупнейший банк России и Восточной Европы'),
                ('GAZP', 'ПАО Газпром', 128.75, 'https://logos-world.net/wp-content/uploads/2020/12/Gazprom-Logo.png', 'Нефть и газ', 'Крупнейшая газовая компания мира'),
                ('LKOH', 'ЛУКОЙЛ', 6850.00, 'https://logos-world.net/wp-content/uploads/2020/12/Lukoil-Logo.png', 'Нефть и газ', 'Одна из крупнейших нефтяных компаний мира'),
                ('YNDX', 'Яндекс', 3420.00, 'https://logos-world.net/wp-content/uploads/2020/11/Yandex-Logo.png', 'IT', 'Российская IT-компания, поисковая система'),
                ('ROSN', 'Роснефть', 565.20, 'https://logos-world.net/wp-content/uploads/2020/12/Rosneft-Logo.png', 'Нефть и газ', 'Крупнейшая нефтяная компания России'),
                ('NVTK', 'НОВАТЭК', 1125.40, 'https://logos-world.net/wp-content/uploads/2020/12/Novatek-Logo.png', 'Нефть и газ', 'Крупнейший производитель природного газа в России'),
                ('TCSG', 'TCS Group', 2890.60, 'https://logos-world.net/wp-content/uploads/2020/12/Tinkoff-Logo.png', 'Банки', 'Частный банк, лидер в сфере цифрового банкинга'),
                ('RUAL', 'РУСАЛ', 45.85, 'https://logos-world.net/wp-content/uploads/2020/12/Rusal-Logo.png', 'Металлургия', 'Крупнейший производитель алюминия в России'),
                ('MAGN', 'ММК', 52.30, 'https://logos-world.net/wp-content/uploads/2020/12/MMK-Logo.png', 'Металлургия', 'Магнитогорский металлургический комбинат'),
                ('GMKN', 'ГМК Норникель', 15680.00, 'https://logos-world.net/wp-content/uploads/2020/12/Nornickel-Logo.png', 'Металлургия', 'Крупнейший производитель никеля и палладия'),
                ('PLZL', 'Полюс', 12450.00, 'https://logos-world.net/wp-content/uploads/2020/12/Polyus-Logo.png', 'Металлургия', 'Крупнейший производитель золота в России'),
                ('TATN', 'Татнефть', 685.20, 'https://logos-world.net/wp-content/uploads/2020/12/Tatneft-Logo.png', 'Нефть и газ', 'Крупная нефтяная компания Татарстана'),
                ('SNGS', 'Сургутнефтегаз', 28.45, 'https://logos-world.net/wp-content/uploads/2020/12/Surgutneftegas-Logo.png', 'Нефть и газ', 'Нефтегазовая компания Западной Сибири'),
                ('VTBR', 'ВТБ', 85.60, 'https://logos-world.net/wp-content/uploads/2020/12/VTB-Logo.png', 'Банки', 'Второй по величине банк России'),
                ('ALRS', 'АЛРОСА', 78.90, 'https://logos-world.net/wp-content/uploads/2020/12/Alrosa-Logo.png', 'Металлургия', 'Крупнейшая алмазодобывающая компания мира'),
                ('CHMF', 'Северсталь', 1245.80, 'https://logos-world.net/wp-content/uploads/2020/12/Severstal-Logo.png', 'Металлургия', 'Крупная металлургическая компания'),
                ('NLMK', 'НЛМК', 185.40, 'https://logos-world.net/wp-content/uploads/2020/12/NLMK-Logo.png', 'Металлургия', 'Новолипецкий металлургический комбинат'),
                ('MOEX', 'Московская Биржа', 198.50, 'https://logos-world.net/wp-content/uploads/2020/12/MOEX-Logo.png', 'Финансы', 'Крупнейшая биржевая группа России'),
                ('AFLT', 'Аэрофлот', 45.20, 'https://logos-world.net/wp-content/uploads/2020/12/Aeroflot-Logo.png', 'Транспорт', 'Национальный авиаперевозчик России'),
                ('PHOR', 'ФосАгро', 6890.00, 'https://logos-world.net/wp-content/uploads/2020/12/PhosAgro-Logo.png', 'Химия', 'Ведущий производитель фосфорных удобрений'),
                ('MTSS', 'МТС', 285.40, 'https://logos-world.net/wp-content/uploads/2020/12/MTS-Logo.png', 'Телеком', 'Крупнейший мобильный оператор России'),
                ('FEES', 'ФСК ЕЭС', 0.185, 'https://logos-world.net/wp-content/uploads/2020/12/FGC-UES-Logo.png', 'Энергетика', 'Федеральная сетевая компания'),
                ('HYDR', 'РусГидро', 0.85, 'https://logos-world.net/wp-content/uploads/2020/12/RusHydro-Logo.png', 'Энергетика', 'Крупнейшая гидроэнергетическая компания России'),
                ('IRAO', 'Интер РАО', 4.25, 'https://logos-world.net/wp-content/uploads/2020/12/Inter-RAO-Logo.png', 'Энергетика', 'Энергетическая компания'),
                ('PIKK', 'ПИК', 890.20, 'https://logos-world.net/wp-content/uploads/2020/12/PIK-Logo.png', 'Недвижимость', 'Крупнейший девелопер России')
            ]
            
            added_count = 0
            updated_count = 0
            
            for ticker, name, price, logo_url, sector, description in all_stocks:
                try:
                    # Проверяем, существует ли акция
                    existing_stock = Stock.query.filter_by(ticker=ticker).first()
                    
                    if existing_stock:
                        # Обновляем существующую акцию
                        existing_stock.logo_url = logo_url
                        existing_stock.sector = sector
                        existing_stock.description = description
                        existing_stock.price = price
                        updated_count += 1
                    else:
                        # Добавляем новую акцию
                        new_stock = Stock(
                            ticker=ticker,
                            name=name,
                            price=price,
                            logo_url=logo_url,
                            sector=sector,
                            description=description
                        )
                        db.session.add(new_stock)
                        added_count += 1
                        
                except Exception as e:
                    print(f"Error processing {ticker}: {e}")
                    continue
            
            try:
                db.session.commit()
                return jsonify({
                    'status': 'success', 
                    'message': f'Added {added_count} new stocks, updated {updated_count} existing stocks'
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'status': 'error', 'message': f'Commit failed: {str(e)}'})
                
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            return jsonify({'status': 'error', 'message': f'Error: {str(e)}'})
    
    @app.route('/update_stocks_from_moex')
    def update_stocks_from_moex():
        """Загрузить актуальные акции с Московской биржи"""
        try:
            import requests
            from database import Stock
            
            # Откатываем любую незавершенную транзакцию
            try:
                db.session.rollback()
            except Exception:
                pass
            
            # API Московской биржи для получения списка акций
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
                    return jsonify({'status': 'error', 'message': 'No data received from MOEX'})
                
                # Создаем словарь для удобного доступа к данным
                secid_idx = columns.index('SECID') if 'SECID' in columns else 0
                shortname_idx = columns.index('SHORTNAME') if 'SHORTNAME' in columns else 1
                prevprice_idx = columns.index('PREVPRICE') if 'PREVPRICE' in columns else -1
                
                added_count = 0
                updated_count = 0
                
                for row in rows:
                    try:
                        ticker = row[secid_idx]
                        name = row[shortname_idx] if shortname_idx < len(row) else ticker
                        price = float(row[prevprice_idx]) if prevprice_idx >= 0 and prevprice_idx < len(row) and row[prevprice_idx] else 0.0
                        
                        # Пропускаем акции без названия или с нулевой ценой
                        if not ticker or not name or price <= 0:
                            continue
                            
                        # Определяем сектор по тикеру (упрощенная логика)
                        sector = get_sector_by_ticker(ticker)
                        
                        # Проверяем, существует ли акция
                        existing_stock = Stock.query.filter_by(ticker=ticker).first()
                        
                        if existing_stock:
                            # Обновляем цену существующей акции
                            existing_stock.price = price
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
                            
                    except (ValueError, IndexError) as e:
                        print(f"Error processing row {row}: {e}")
                        continue
                
                try:
                    db.session.commit()
                    return jsonify({
                        'status': 'success',
                        'message': f'Updated {updated_count} stocks, added {added_count} new stocks from MOEX',
                        'total_processed': len(rows)
                    })
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': f'Database commit failed: {str(e)}'})
                    
            except requests.RequestException as e:
                return jsonify({'status': 'error', 'message': f'Failed to fetch data from MOEX: {str(e)}'})
                
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            return jsonify({'status': 'error', 'message': f'Error: {str(e)}'})
    
    @app.route('/')
    def index():
        current_year = datetime.datetime.now().year
        try:
            # Безопасно пробуем посчитать количество бумаг
            stock_count = None
            try:
                stock_count = Stock.query.count()
            except Exception as e:
                logger.error(f"Index DB count error: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass
                # Автоматическая попытка добавить отсутствующие колонки (для прод базы без миграции)
                try:
                    dialect = ''
                    try:
                        bind = db.session.get_bind() if hasattr(db.session, 'get_bind') else db.session.bind
                        dialect = bind.dialect.name if bind is not None else ''
                    except Exception:
                        pass
                    if dialect.startswith('postgres'):
                        # PostgreSQL: используем IF NOT EXISTS
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS instrument_type VARCHAR(20) DEFAULT 'share'"))
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS face_value DOUBLE PRECISION"))
                        # Новые метрики торгов
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS turnover DOUBLE PRECISION"))
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS volume BIGINT"))
                        db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS change_pct DOUBLE PRECISION"))
                    else:
                        # SQLite/MySQL: пробуем добавить, игнорируем ошибку, если колонка уже есть
                        try:
                            db.session.execute(db.text("ALTER TABLE stock ADD COLUMN instrument_type VARCHAR(20) DEFAULT 'share'"))
                        except Exception:
                            db.session.rollback()
                        try:
                            db.session.execute(db.text("ALTER TABLE stock ADD COLUMN face_value FLOAT"))
                        except Exception:
                            db.session.rollback()
                        # Новые метрики торгов
                        try:
                            db.session.execute(db.text("ALTER TABLE stock ADD COLUMN turnover FLOAT"))
                        except Exception:
                            db.session.rollback()
                        try:
                            db.session.execute(db.text("ALTER TABLE stock ADD COLUMN volume INTEGER"))
                        except Exception:
                            db.session.rollback()
                        try:
                            db.session.execute(db.text("ALTER TABLE stock ADD COLUMN change_pct FLOAT"))
                        except Exception:
                            db.session.rollback()
                    db.session.commit()
                except Exception as mig_e:
                    logger.error(f"Auto-migration fails on index: {mig_e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

                # Переходим на безопасный raw COUNT, чтобы страница все равно загрузилась
                try:
                    stock_count = db.session.execute(db.text("SELECT COUNT(1) FROM stock")).scalar()
                except Exception as raw_e:
                    logger.error(f"Raw COUNT failed: {raw_e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    stock_count = None

            # Автосинхронизация при небольшой базе, с безопасным rollback
            if stock_count is not None and stock_count < 50:
                try:
                    from stock_api import stock_api_service
                    stock_api_service.sync_stocks_to_database()
                except Exception as e:
                    logger.error(f"Auto sync stocks error: {e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                try:
                    from stock_api import stock_api_service
                    stock_api_service.sync_bonds_to_database()
                except Exception as e:
                    logger.error(f"Auto sync bonds error: {e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
            
            return render_template('index.html', year=current_year)
        except Exception as e:
            # Возвращаем детальную информацию об ошибке
            import traceback
            return jsonify({
                'error': str(e), 
                'message': 'Template error',
                'traceback': traceback.format_exc()
            }), 500
    
    @app.route('/login')
    def login():
        """Страница входа через Telegram"""
        # Проверяем, пришел ли пользователь из Telegram Web App
        telegram_id = request.args.get('telegram_id')
        username = request.args.get('username')
        
        # Проверяем заголовки Telegram Web App
        user_agent = request.headers.get('User-Agent', '')
        is_telegram = any(x in user_agent.lower() for x in ['telegram', 'tgwebapp'])
        
        # Если есть данные Telegram или это Telegram браузер, автоматически логиним
        if telegram_id and username:
            # Проверяем, существует ли пользователь
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                # Создаем нового пользователя
                user = User(telegram_id=telegram_id, username=username)
                db.session.add(user)
                
                # Создаем основной счет
                main_account = Account(name="Основной счет", user=user)
                db.session.add(main_account)
                
                db.session.commit()
            
            # Сохраняем пользователя в сессии
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        
        return render_template('login.html')
    
    @app.route('/demo_login')
    def demo_login():
        """Демо-вход для тестирования без Telegram"""
        # Создаем или получаем демо-пользователя
        demo_user = User.query.filter_by(telegram_id='demo_user').first()
        
        if not demo_user:
            demo_user = User(telegram_id='demo_user', username='Демо пользователь')
            db.session.add(demo_user)
            
            # Создаем несколько счетов
            main_account = Account(name="Основной счет", balance=50000.0, user=demo_user)
            second_account = Account(name="Инвестиционный счет", balance=100000.0, user=demo_user)
            db.session.add(main_account)
            db.session.add(second_account)
            
            db.session.commit()
        
        session['user_id'] = demo_user.id
        return redirect(url_for('dashboard'))
    
    @app.route('/dashboard')
    def dashboard():
        """Главная панель пользователя"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        accounts = Account.query.filter_by(user_id=user.id).all()
        
        # Получаем статистику портфеля
        portfolio_stats = calculate_portfolio_stats(user.id)
        if not portfolio_stats:
            portfolio_stats = {
                'total_balance': sum(acc.balance for acc in accounts),
                'total_invested': 0,
                'total_current_value': 0,
                'total_profit_loss': 0,
                'total_profit_loss_percent': 0,
                'positions': []
            }
        
        # Получаем последние транзакции
        recent_transactions = Transaction.query.join(Account).filter(
            Account.user_id == user.id
        ).order_by(Transaction.timestamp.desc()).limit(10).all()
        # Гарантируем, что timestamp не None для шаблона
        try:
            for t in recent_transactions:
                if not getattr(t, 'timestamp', None):
                    t.timestamp = datetime.datetime.now()
        except Exception:
            pass
        
        # Получаем топ акций
        top_stocks = get_top_stocks(6)
        if not top_stocks:
            top_stocks = Stock.query.filter(Stock.price > 0).order_by(Stock.price.desc()).limit(6).all()

        # Структура портфеля по секторам (по текущей стоимости)
        sector_labels = []
        sector_values = []
        try:
            sector_totals = {}
            positions = []
            try:
                positions = portfolio_stats.get('positions') if isinstance(portfolio_stats, dict) else []
            except Exception:
                positions = []
            for pos in positions:
                try:
                    sec = getattr(pos.stock, 'sector', None) or 'Прочие'
                    val = float(getattr(pos, 'current_value', 0.0) or 0.0)
                    if val > 0:
                        sector_totals[sec] = sector_totals.get(sec, 0.0) + val
                except Exception:
                    continue
            ordered = sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)
            sector_labels = [k for k, _ in ordered]
            sector_values = [round(v, 2) for _, v in ordered]
        except Exception:
            pass
        
        return render_template('dashboard.html', 
                             user=user, 
                             accounts=accounts, 
                             portfolio_stats=portfolio_stats,
                             recent_transactions=recent_transactions,
                             top_stocks=top_stocks,
                             sector_labels=sector_labels,
                             sector_values=sector_values)

    @app.route('/account/<int:account_id>')
    def account_detail(account_id):
        """Страница деталей счета"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        # Проверяем, что счет принадлежит пользователю
        acc = Account.query.filter_by(id=account_id, user_id=session['user_id']).first()
        if not acc:
            return redirect(url_for('dashboard'))
        # Загружаем транзакции счета (последние сверху)
        transactions = Transaction.query.filter_by(account_id=acc.id).order_by(Transaction.timestamp.desc()).all()
        # Гарантируем наличие timestamp
        try:
            import datetime as _dt
            for t in transactions:
                if not getattr(t, 'timestamp', None):
                    t.timestamp = _dt.datetime.now()
        except Exception:
            pass
        return render_template('account_detail.html', account=acc, transactions=transactions)

    @app.route('/stocks')
    def stocks():
        """Страница со списком акций"""
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        ins_type = request.args.get('type', 'share')
        sort = request.args.get('sort', 'price_desc')

        # Безопасная авто-миграция нужных колонок (если пользователь зашел сразу на /stocks)
        try:
            dialect = ''
            try:
                bind = db.session.get_bind() if hasattr(db.session, 'get_bind') else db.session.bind
                dialect = bind.dialect.name if bind is not None else ''
            except Exception:
                pass
            if dialect.startswith('postgres'):
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS instrument_type VARCHAR(20) DEFAULT 'share'"))
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS face_value DOUBLE PRECISION"))
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS turnover DOUBLE PRECISION"))
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS volume BIGINT"))
                db.session.execute(db.text("ALTER TABLE stock ADD COLUMN IF NOT EXISTS change_pct DOUBLE PRECISION"))
                # Обновляем типы, если уже существовали как иные:
                try:
                    db.session.execute(db.text("ALTER TABLE stock ALTER COLUMN volume TYPE BIGINT USING volume::BIGINT"))
                except Exception:
                    pass
                try:
                    db.session.execute(db.text("ALTER TABLE stock ALTER COLUMN turnover TYPE DOUBLE PRECISION USING turnover::DOUBLE PRECISION"))
                except Exception:
                    pass
            else:
                for stmt in [
                    "ALTER TABLE stock ADD COLUMN instrument_type VARCHAR(20) DEFAULT 'share'",
                    "ALTER TABLE stock ADD COLUMN face_value FLOAT",
                    "ALTER TABLE stock ADD COLUMN turnover FLOAT",
                    "ALTER TABLE stock ADD COLUMN volume INTEGER",
                    "ALTER TABLE stock ADD COLUMN change_pct FLOAT",
                ]:
                    try:
                        db.session.execute(db.text(stmt))
                    except Exception:
                        db.session.rollback()
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        query = Stock.query
        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Stock.ticker.contains(search.upper()),
                    Stock.name.contains(search)
                )
            )

        # Пытаемся применить фильтр по типу инструмента; при ошибке (например, нет колонки) —
        # делаем fallback без этого фильтра
        try:
            if ins_type in ('share', 'bond'):
                query_filtered = query.filter(Stock.instrument_type == ins_type)
            else:
                query_filtered = query

            # Сортировка
            if sort == 'price_desc':
                query_filtered = query_filtered.order_by(Stock.price.desc())
            elif sort == 'price_asc':
                query_filtered = query_filtered.order_by(Stock.price.asc())
            elif sort == 'name_asc':
                query_filtered = query_filtered.order_by(Stock.name.asc())
            elif sort == 'name_desc':
                query_filtered = query_filtered.order_by(Stock.name.desc())
            elif sort == 'ticker_asc':
                query_filtered = query_filtered.order_by(Stock.ticker.asc())
            elif sort == 'ticker_desc':
                query_filtered = query_filtered.order_by(Stock.ticker.desc())
            elif sort == 'sector_asc':
                query_filtered = query_filtered.order_by(Stock.sector.asc().nulls_last()) if hasattr(Stock.sector, 'asc') else query_filtered.order_by(Stock.sector)
            elif sort == 'sector_desc':
                query_filtered = query_filtered.order_by(Stock.sector.desc().nulls_last()) if hasattr(Stock.sector, 'desc') else query_filtered.order_by(Stock.sector)
            elif sort == 'turnover_desc':
                try:
                    query_filtered = query_filtered.filter(Stock.turnover != None).order_by(Stock.turnover.desc())
                except Exception:
                    query_filtered = query_filtered.order_by(Stock.price.desc())
            elif sort == 'turnover_asc':
                try:
                    query_filtered = query_filtered.filter(Stock.turnover != None).order_by(Stock.turnover.asc())
                except Exception:
                    query_filtered = query_filtered.order_by(Stock.price.asc())
            elif sort == 'volume_desc':
                try:
                    query_filtered = query_filtered.filter(Stock.volume != None).order_by(Stock.volume.desc())
                except Exception:
                    query_filtered = query_filtered.order_by(Stock.price.desc())
            elif sort == 'volume_asc':
                try:
                    query_filtered = query_filtered.filter(Stock.volume != None).order_by(Stock.volume.asc())
                except Exception:
                    query_filtered = query_filtered.order_by(Stock.price.asc())
            elif sort == 'change_desc':
                try:
                    query_filtered = query_filtered.filter(Stock.change_pct != None).order_by(Stock.change_pct.desc())
                except Exception:
                    query_filtered = query_filtered.order_by(Stock.price.desc())
            elif sort == 'change_asc':
                try:
                    query_filtered = query_filtered.filter(Stock.change_pct != None).order_by(Stock.change_pct.asc())
                except Exception:
                    query_filtered = query_filtered.order_by(Stock.price.asc())
            else:
                query_filtered = query_filtered.order_by(Stock.price.desc())

            stocks = query_filtered.paginate(
                page=page, per_page=50, error_out=False
            )
        except Exception as e:
            try:
                logger.warning(f"Stocks query fallback (no instrument_type filter): {e}")
            except Exception:
                pass
            # Без фильтра и с базовой сортировкой
            base_q = query.order_by(Stock.price.desc()) if sort == 'price_desc' else query
            stocks = base_q.paginate(
                page=page, per_page=50, error_out=False
            )

        accounts = []
        if 'user_id' in session:
            accounts = Account.query.filter_by(user_id=session['user_id']).all()

        # Топ по обороту за сегодня (только для акций)
        top_by_turnover = []
        try:
            if ins_type == 'share':
                top_by_turnover = Stock.query.filter(Stock.turnover != None, Stock.turnover > 0).order_by(Stock.turnover.desc()).limit(12).all()
        except Exception:
            top_by_turnover = []

        return render_template('stocks.html', stocks=stocks, search=search, accounts=accounts, ins_type=ins_type, sort=sort, top_by_turnover=top_by_turnover)

    @app.route('/stock/<ticker>')
    def stock_detail(ticker):
        """Детальная страница акции"""
        stock = Stock.query.filter_by(ticker=ticker).first()
        if not stock:
            return redirect(url_for('stocks'))

        user_positions = None
        if 'user_id' in session:
            # Собираем позиции пользователя по данной бумаге
            txs = Transaction.query.join(Account).filter(
                Account.user_id == session['user_id'],
                Transaction.stock_id == stock.id,
                Transaction.type.in_(['buy', 'sell'])
            ).all()
            qty = 0
            total_cost = 0.0
            for t in txs:
                q = (t.quantity or 0)
                p = (t.price or 0.0)
                if t.type == 'buy':
                    qty += q
                    total_cost += q * p
                elif t.type == 'sell':
                    qty -= q
                    total_cost -= q * p
            if qty > 0:
                avg_price = total_cost / qty if qty else 0
                current_value = qty * (stock.price or 0.0)
                profit_loss = current_value - total_cost
                profit_loss_percent = (profit_loss / total_cost * 100) if total_cost > 0 else 0
                user_positions = {
                    'quantity': qty,
                    'avg_price': avg_price,
                    'current_value': current_value,
                    'profit_loss': profit_loss,
                    'profit_loss_percent': profit_loss_percent
                }

        today = datetime.date.today().isoformat()
        return render_template('stock_detail.html', stock=stock, user_positions=user_positions, today=today)

    @app.route('/api/news/<ticker>')
    def get_stock_news(ticker):
        """Возвращает список новостей с MOEX sitenews, отфильтрованных по тикеру/названию."""
        try:
            import requests
            stock = Stock.query.filter_by(ticker=ticker).first()
            name = stock.name if stock else ticker
            url = 'https://iss.moex.com/iss/sitenews.json'
            params = {'iss.meta': 'off'}
            r = requests.get(url, params=params, timeout=8)
            r.raise_for_status()
            data = r.json()
            items = []
            if 'sitenews' in data and 'data' in data['sitenews']:
                cols = data['sitenews']['columns']
                def idx(col):
                    return cols.index(col) if col in cols else None
                id_i = idx('id'); title_i = idx('title'); url_i = idx('url'); pub_i = idx('published_at')
                for row in data['sitenews']['data']:
                    try:
                        title = row[title_i] if title_i is not None else ''
                        if not title:
                            continue
                        key = ticker.upper(); company = (name or '').upper()
                        if key not in title.upper() and (company and company not in title.upper()):
                            continue
                        items.append({
                            'id': row[id_i] if id_i is not None else None,
                            'title': title,
                            'url': row[url_i] if url_i is not None else None,
                            'published_at': row[pub_i] if pub_i is not None else None
                        })
                        if len(items) >= 8:
                            break
                    except Exception:
                        continue
            return jsonify({'success': True, 'items': items, 'ticker': ticker})
        except Exception as e:
            logger.warning(f"Новости недоступны для {ticker}: {e}")
            return jsonify({'success': False, 'items': []})
        
    # Register routes defined below (plain functions without decorators)
    # '/stocks' and '/api/news/<ticker>' are already registered via decorators above
    # Avoid duplicate registration to prevent endpoint overwrite errors
    app.add_url_rule('/api/deposit', view_func=deposit, methods=['POST'])
    app.add_url_rule('/api/withdraw', view_func=withdraw, methods=['POST'])
    app.add_url_rule('/api/buy_stock', view_func=buy_stock, methods=['POST'])
    app.add_url_rule('/api/add_historical_buy', view_func=add_historical_buy, methods=['POST'])
    app.add_url_rule('/api/sell_stock', view_func=sell_stock, methods=['POST'])
    app.add_url_rule('/api/accounts', view_func=get_accounts)
    app.add_url_rule('/api/stock_history/<ticker>', view_func=get_stock_history_api)
    app.add_url_rule('/api/stock_intraday/<ticker>', view_func=get_stock_intraday_api)
    app.add_url_rule('/admin/logos', view_func=admin_logos_page)
    app.add_url_rule('/admin/update_logos', view_func=admin_update_logos)
    app.add_url_rule('/api/create_account', view_func=create_account, methods=['POST'])
    app.add_url_rule('/api/stock_price/<ticker>', view_func=get_stock_price)
    app.add_url_rule('/api/update_all_prices', view_func=update_all_prices)
    app.add_url_rule('/admin/sync-bonds', view_func=sync_bonds)
    app.add_url_rule('/api/portfolio_history', view_func=get_portfolio_history)
    
def deposit():
    """API для пополнения счета"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Некорректные данные запроса'}), 400
        
        account_id = int(data.get('account_id'))
        amount = float(data.get('amount', 0))
    except Exception as e:
        return jsonify({'error': f'Ошибка обработки данных: {str(e)}'}), 400
    
    if amount <= 0:
        return jsonify({'error': 'Сумма должна быть положительной'}), 400
    
    account = Account.query.filter_by(
        id=account_id, 
        user_id=session['user_id']
    ).first()
    
    if not account:
        return jsonify({'error': 'Счет не найден'}), 404
    
    # Создаем транзакцию пополнения
    transaction = Transaction(
        type='deposit',
        amount=amount,
        account=account
    )
    
    # Обновляем баланс счета
    account.balance += amount
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({'success': True, 'new_balance': account.balance})
 
def withdraw():
    """API для вывода средств со счета"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Некорректные данные запроса'}), 400
        account_id = int(data.get('account_id'))
        amount = float(data.get('amount', 0))
    except Exception as e:
        return jsonify({'error': f'Ошибка обработки данных: {str(e)}'}), 400
    if amount <= 0:
        return jsonify({'error': 'Сумма должна быть положительной'}), 400
    account = Account.query.filter_by(id=account_id, user_id=session['user_id']).first()
    if not account:
        return jsonify({'error': 'Счет не найден'}), 404
    if account.balance < amount:
        return jsonify({'error': 'Недостаточно средств на счете'}), 400
    transaction = Transaction(type='withdrawal', amount=amount, account=account)
    account.balance -= amount
    db.session.add(transaction)
    db.session.commit()
    return jsonify({'success': True, 'new_balance': account.balance})

def buy_stock():
    """API для покупки акций"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    data = request.get_json()
    account_id = int(data.get('account_id'))
    stock_id = int(data.get('stock_id'))
    quantity = int(data.get('quantity', 0))
    if quantity <= 0:
        return jsonify({'error': 'Количество должно быть положительным'}), 400
    account = Account.query.filter_by(id=account_id, user_id=session['user_id']).first()
    stock = Stock.query.get(stock_id)
    if not account or not stock:
        return jsonify({'error': 'Счет или акция не найдены'}), 404
    total_cost = quantity * stock.price
    if account.balance < total_cost:
        return jsonify({'error': 'Недостаточно средств на счете'}), 400
    transaction = Transaction(type='buy', amount=total_cost, price=stock.price, quantity=quantity, account=account, stock_id=stock.id)
    account.balance -= total_cost
    db.session.add(transaction)
    db.session.commit()
    return jsonify({'success': True, 'new_balance': account.balance})

def add_historical_buy():
    """API для добавления исторической покупки акций"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    data = request.get_json()
    account_id = int(data.get('account_id'))
    stock_id = int(data.get('stock_id'))
    quantity = int(data.get('quantity', 0))
    price = float(data.get('price', 0))
    purchase_date = data.get('purchase_date')
    if quantity <= 0:
        return jsonify({'error': 'Количество должно быть положительным'}), 400
    if price <= 0:
        return jsonify({'error': 'Цена должна быть положительной'}), 400
    account = Account.query.filter_by(id=account_id, user_id=session['user_id']).first()
    stock = Stock.query.get(stock_id)
    if not account or not stock:
        return jsonify({'error': 'Счет или акция не найдены'}), 404
    try:
        from datetime import datetime as dt
        purchase_datetime = dt.strptime(purchase_date, '%Y-%m-%d')
        if purchase_datetime > dt.now():
            return jsonify({'error': 'Дата покупки не может быть в будущем'}), 400
    except ValueError:
        return jsonify({'error': 'Неверный формат даты'}), 400
    total_cost = quantity * price
    transaction = Transaction(type='buy', amount=total_cost, price=price, quantity=quantity, account=account, stock_id=stock.id, timestamp=purchase_datetime)
    db.session.add(transaction)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Историческая покупка добавлена', 'total_cost': total_cost, 'transaction_id': transaction.id})

def sell_stock():
    """API для продажи акций"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    data = request.get_json()
    account_id = int(data.get('account_id'))
    stock_id = int(data.get('stock_id'))
    quantity = int(data.get('quantity', 0))
    if quantity <= 0:
        return jsonify({'error': 'Количество должно быть положительным'}), 400
    account = Account.query.filter_by(id=account_id, user_id=session['user_id']).first()
    stock = Stock.query.get(stock_id)
    if not account or not stock:
        return jsonify({'error': 'Счет или акция не найдены'}), 404
    buy_transactions = Transaction.query.filter_by(account_id=account_id, stock_id=stock_id, type='buy').all()
    sell_transactions = Transaction.query.filter_by(account_id=account_id, stock_id=stock_id, type='sell').all()
    total_bought = sum(t.quantity for t in buy_transactions)
    total_sold = sum(t.quantity for t in sell_transactions)
    available_quantity = total_bought - total_sold
    if available_quantity < quantity:
        return jsonify({'error': 'Недостаточно акций для продажи'}), 400
    total_revenue = quantity * stock.price
    transaction = Transaction(type='sell', amount=total_revenue, price=stock.price, quantity=quantity, account=account, stock_id=stock.id)
    account.balance += total_revenue
    db.session.add(transaction)
    db.session.commit()
    return jsonify({'success': True, 'new_balance': account.balance})

def get_accounts():
    """API для получения списка счетов пользователя"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    accounts = Account.query.filter_by(user_id=session['user_id']).all()
    return jsonify({'success': True, 'accounts': [{'id': acc.id, 'name': acc.name, 'balance': acc.balance} for acc in accounts]})

def get_stock_history_api(ticker):
    """API для получения истории цен акции"""
    try:
        from stock_api import stock_api_service
        days = request.args.get('days', 7, type=int)
        if days > 120:
            days = 120
        history = stock_api_service.get_stock_history(ticker, days)
        if history:
            return jsonify({'success': True, 'ticker': ticker, 'days': days, 'data': history})
        else:
            return jsonify({'success': False, 'ticker': ticker, 'message': 'Нет данных с MOEX', 'data': []})
    except Exception as e:
        logger.error(f"Ошибка получения истории для {ticker}: {e}")
        return jsonify({'success': False, 'error': str(e), 'data': []}), 500

def get_stock_intraday_api(ticker):
    """API для получения внутридневной истории (по умолчанию 10-мин свечи за 24 часа)"""
    try:
        from stock_api import stock_api_service
        interval = request.args.get('interval', 10, type=int)
        hours = request.args.get('hours', 24, type=int)
        if interval not in (1, 10, 60):
            interval = 10
        if hours > 72:
            hours = 72
        data = stock_api_service.get_intraday_history(ticker, interval=interval, hours=hours)
        return jsonify({'success': True, 'ticker': ticker, 'interval': interval, 'hours': hours, 'data': data})
    except Exception as e:
        logger.error(f"Ошибка intraday для {ticker}: {e}")
        return jsonify({'success': False, 'error': str(e), 'data': []}), 500

def admin_logos_page():
    """Страница обновления логотипов"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('admin_update_logos.html')

def admin_update_logos():
    """Обновление всех логотипов акций"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    try:
        from stock_api import stock_api_service
        stocks = Stock.query.all()
        updated_count = 0
        for stock in stocks:
            try:
                new_logo_url = stock_api_service._get_logo_url(stock.ticker)
                if new_logo_url:
                    stock.logo_url = new_logo_url
                    updated_count += 1
            except Exception as e:
                logger.error(f"Ошибка обновления логотипа для {stock.ticker}: {e}")
                continue
        db.session.commit()
        return jsonify({'success': True, 'message': f'Обновлено {updated_count} логотипов из {len(stocks)}', 'updated': updated_count, 'total': len(stocks)})
    except Exception as e:
        logger.error(f"Ошибка обновления логотипов: {e}")
        return jsonify({'error': str(e)}), 500

def create_account():
    """API для создания нового счета"""
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    data = request.get_json()
    account_name = data.get('name', '').strip()
    if not account_name:
        return jsonify({'error': 'Имя счета не может быть пустым'}), 400
    existing_account = Account.query.filter_by(user_id=session['user_id'], name=account_name).first()
    if existing_account:
        return jsonify({'error': 'Счет с таким именем уже существует'}), 400
    new_account = Account(name=account_name, balance=0.0, user_id=session['user_id'])
    db.session.add(new_account)
    db.session.commit()
    return jsonify({'success': True, 'account': {'id': new_account.id, 'name': new_account.name, 'balance': new_account.balance}})

def get_stock_price(ticker):
    """API для получения актуальной цены акции"""
    try:
        from stock_api import stock_api_service
        stock = Stock.query.filter_by(ticker=ticker).first()
        current_price = None
        if stock and getattr(stock, 'instrument_type', 'share') == 'bond':
            current_price = stock_api_service._get_bond_price(ticker, getattr(stock, 'face_value', None))
        else:
            current_price = stock_api_service._get_stock_price(ticker)
        if current_price and current_price > 0:
            if stock:
                stock.price = current_price
                db.session.commit()
            return jsonify({'success': True, 'ticker': ticker, 'price': current_price, 'source': 'moex_api'})
        if stock and stock.price:
            return jsonify({'success': True, 'ticker': ticker, 'price': stock.price, 'cached': True, 'source': 'database'})
        return jsonify({'success': False, 'error': 'Stock not found or no price available'}), 404
    except Exception as e:
        logger.error(f"Ошибка получения цены для {ticker}: {e}")
        stock = Stock.query.filter_by(ticker=ticker).first()
        if stock and stock.price:
            return jsonify({'success': True, 'ticker': ticker, 'price': stock.price, 'cached': True, 'error': str(e), 'source': 'database_fallback'})
        return jsonify({'success': False, 'error': str(e)}), 500

def update_all_prices():
    """API для быстрого обновления цен популярных акций"""
    try:
        from stock_api import stock_api_service
        import time
        # Гарантируем корректные типы колонок в Postgres (volume: BIGINT, turnover: DOUBLE PRECISION)
        try:
            bind = db.session.get_bind() if hasattr(db.session, 'get_bind') else db.session.bind
            if bind is not None and getattr(bind.dialect, 'name', '') .startswith('postgres'):
                try:
                    db.session.execute(db.text("ALTER TABLE stock ALTER COLUMN volume TYPE BIGINT USING volume::BIGINT"))
                except Exception:
                    db.session.rollback()
                try:
                    db.session.execute(db.text("ALTER TABLE stock ALTER COLUMN turnover TYPE DOUBLE PRECISION USING turnover::DOUBLE PRECISION"))
                except Exception:
                    db.session.rollback()
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
        except Exception:
            # Не мешаем основному потоку обновления
            try:
                db.session.rollback()
            except Exception:
                pass
        stocks = Stock.query.all()
        updated_count = 0
        failed_count = 0
        results = []
        start_time = time.time()
        share_tickers = [s.ticker for s in stocks if getattr(s, 'instrument_type', 'share') == 'share']
        bond_tickers = [s.ticker for s in stocks if getattr(s, 'instrument_type', 'share') == 'bond']
        face_values_map = {s.ticker: getattr(s, 'face_value', None) for s in stocks if getattr(s, 'instrument_type', 'share') == 'bond'}
        metrics = {}
        if share_tickers:
            # Получаем метрики торгов для акций (включая цену)
            m = stock_api_service.get_multiple_stock_trade_metrics(share_tickers, timeout=10)
            if m:
                metrics.update(m)
        if bond_tickers:
            # Для облигаций только цена
            bond_prices = stock_api_service.get_multiple_bond_prices(bond_tickers, face_values_map=face_values_map, timeout=10)
            for t, p in bond_prices.items():
                metrics[t] = {'price': p}

        for stock in stocks:
            try:
                if stock.ticker in metrics and metrics[stock.ticker].get('price'):
                    new_price = metrics[stock.ticker]['price']
                    old_price = stock.price
                    stock.price = new_price
                    # Дополнительные метрики для акций
                    data = metrics.get(stock.ticker, {})
                    if getattr(stock, 'instrument_type', 'share') == 'share':
                        if 'turnover' in data:
                            stock.turnover = data.get('turnover')
                        if 'volume' in data:
                            stock.volume = data.get('volume')
                        if 'change_pct' in data:
                            stock.change_pct = data.get('change_pct')
                    updated_count += 1
                    results.append({'ticker': stock.ticker, 'old_price': old_price, 'new_price': new_price, 'status': 'updated', 'turnover': stock.turnover, 'volume': stock.volume, 'change_pct': stock.change_pct})
                    logger.info(f"Обновлена цена {stock.ticker}: {old_price} → {new_price}")
                else:
                    failed_count += 1
                    results.append({'ticker': stock.ticker, 'status': 'failed', 'error': 'No price received'})
                    logger.warning(f"Не удалось получить цену для {stock.ticker}")
            except Exception as e:
                failed_count += 1
                results.append({'ticker': stock.ticker, 'status': 'error', 'error': str(e)})
                logger.error(f"Ошибка обновления {stock.ticker}: {e}")
        db.session.commit()
        return jsonify({'success': True, 'message': f'Обновлено: {updated_count} акций, ошибок: {failed_count}, всего: {len(stocks)}', 'updated_count': updated_count, 'failed_count': failed_count, 'total_count': len(stocks), 'results': results[:10], 'execution_time': round(time.time() - start_time, 2)})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка массового обновления цен: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def sync_bonds():
    """Синхронизация облигаций с MOEX API"""
    try:
        from stock_api import stock_api_service
        result = stock_api_service.sync_bonds_to_database()
        if result and result.get('success'):
            return jsonify({'status': 'success', 'message': f"Синхронизация облигаций завершена. Добавлено: {result['added']}, обновлено: {result['updated']}, всего бумаг: {result['total']}"})
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Не удалось получить результат'
            return jsonify({'status': 'error', 'message': f'Ошибка синхронизации облигаций: {error_msg}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Ошибка синхронизации облигаций: {str(e)}'}), 500

def get_portfolio_history():
    """API: История стоимости портфеля пользователя за N дней (по умолчанию 30),
    оценивается на основе текущих позиций и дневной истории цен."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    try:
        from stock_api import stock_api_service
        days = request.args.get('days', 30, type=int)
        if days > 120:
            days = 120
        # Считаем текущие позиции пользователя по всем счетам
        txs = Transaction.query.join(Account).filter(
            Account.user_id == session['user_id'],
            Transaction.type.in_(['buy', 'sell'])
        ).all()
        qty_by_stock = {}
        stock_map = {}
        for t in txs:
            sid = t.stock_id
            if not sid:
                continue
            st = stock_map.get(sid) or Stock.query.get(sid)
            stock_map[sid] = st
            if not st:
                continue
            q = t.quantity or 0
            if t.type == 'buy':
                qty_by_stock[sid] = qty_by_stock.get(sid, 0) + q
            elif t.type == 'sell':
                qty_by_stock[sid] = qty_by_stock.get(sid, 0) - q
        # Оставляем только положительные позиции
        qty_by_stock = {sid: q for sid, q in qty_by_stock.items() if q > 0}
        if not qty_by_stock:
            return jsonify({'success': True, 'data': []})
        # Собираем историю по каждому тикеру и агрегируем по датам
        history_map = {}
        for sid, qty in qty_by_stock.items():
            st = stock_map[sid]
            if not st:
                continue
            hist = stock_api_service.get_stock_history(st.ticker, days)
            for item in hist:
                d = item['date']
                p = float(item['price'])
                history_map[d] = history_map.get(d, 0.0) + qty * p
        # Преобразуем в отсортированный список
        items = sorted([{'date': d, 'value': round(v, 2)} for d, v in history_map.items()], key=lambda x: x['date'])
        return jsonify({'success': True, 'data': items})
    except Exception as e:
        logger.error(f"Ошибка истории портфеля: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Вспомогательные функции (вне init_routes)
def get_sector_by_ticker(ticker):
    """Определяет сектор по тикеру акции"""
    sectors = {
        # Банки
        'SBER': 'Банки', 'VTBR': 'Банки', 'TCSG': 'Банки', 'CBOM': 'Банки',
        # Нефть и газ
        'GAZP': 'Нефть и газ', 'LKOH': 'Нефть и газ', 'ROSN': 'Нефть и газ', 
        'NVTK': 'Нефть и газ', 'TATN': 'Нефть и газ', 'SNGS': 'Нефть и газ',
        # Металлургия
        'GMKN': 'Металлургия', 'RUAL': 'Металлургия', 'MAGN': 'Металлургия',
        'NLMK': 'Металлургия', 'CHMF': 'Металлургия', 'ALRS': 'Металлургия',
        'PLZL': 'Металлургия',
        # IT
        'YNDX': 'IT', 'MAIL': 'IT', 'OZON': 'IT', 'VKCO': 'IT',
        # Телеком
        'MTSS': 'Телеком', 'RTKM': 'Телеком', 'MGTS': 'Телеком',
        # Энергетика
        'FEES': 'Энергетика', 'HYDR': 'Энергетика', 'IRAO': 'Энергетика',
        'LSRG': 'Энергетика', 'MSRS': 'Энергетика',
        # Транспорт
        'AFLT': 'Транспорт', 'FESH': 'Транспорт',
        # Финансы
        'MOEX': 'Финансы', 'SPBE': 'Финансы',
        # Химия
        'PHOR': 'Химия', 'AKRN': 'Химия',
        # Недвижимость
        'PIKK': 'Недвижимость', 'LSRG': 'Недвижимость', 'ETALON': 'Недвижимость',
        # Ритейл
        'FIVE': 'Ритейл', 'MGNT': 'Ритейл', 'DIXY': 'Ритейл'
    }
    return sectors.get(ticker, 'Прочие')
