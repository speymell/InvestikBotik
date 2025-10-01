from flask import render_template, request, jsonify, redirect, url_for, session
from database import db, User, Account, Stock, Transaction
from utils import calculate_portfolio_stats, get_top_stocks
import datetime

def init_routes(app):
    
    @app.route('/health')
    def health():
        """Health check endpoint для Render"""
        return jsonify({'status': 'ok', 'message': 'InvestBot is running'})
    
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
    
    @app.route('/update_prices')
    def update_prices():
        """Обновить цены всех акций с MOEX"""
        try:
            import requests
            from database import Stock
            
            try:
                db.session.rollback()
            except Exception:
                pass
            
            # Получаем все тикеры из БД
            stocks = Stock.query.all()
            if not stocks:
                return jsonify({'status': 'error', 'message': 'No stocks in database'})
            
            tickers = [stock.ticker for stock in stocks]
            
            # API для получения текущих цен
            moex_url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
            
            try:
                response = requests.get(moex_url, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                securities = data.get('securities', {})
                columns = securities.get('columns', [])
                rows = securities.get('data', [])
                
                if not columns or not rows:
                    return jsonify({'status': 'error', 'message': 'No price data from MOEX'})
                
                secid_idx = columns.index('SECID') if 'SECID' in columns else 0
                prevprice_idx = columns.index('PREVPRICE') if 'PREVPRICE' in columns else -1
                
                updated_count = 0
                price_updates = {}
                
                # Создаем словарь цен из ответа MOEX
                for row in rows:
                    try:
                        ticker = row[secid_idx]
                        price = float(row[prevprice_idx]) if prevprice_idx >= 0 and prevprice_idx < len(row) and row[prevprice_idx] else None
                        
                        if ticker in tickers and price and price > 0:
                            price_updates[ticker] = price
                    except (ValueError, IndexError):
                        continue
                
                # Обновляем цены в БД
                for stock in stocks:
                    if stock.ticker in price_updates:
                        stock.price = price_updates[stock.ticker]
                        updated_count += 1
                
                try:
                    db.session.commit()
                    return jsonify({
                        'status': 'success',
                        'message': f'Updated prices for {updated_count} stocks',
                        'total_stocks': len(stocks)
                    })
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': f'Database update failed: {str(e)}'})
                    
            except requests.RequestException as e:
                return jsonify({'status': 'error', 'message': f'Failed to fetch prices: {str(e)}'})
                
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
        telegram_id = request.args.get('telegram_id')
        username = request.args.get('username')
        
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
        
        # Получаем топ акций
        top_stocks = get_top_stocks(6)
        if not top_stocks:
            top_stocks = Stock.query.filter(Stock.price > 0).order_by(Stock.price.desc()).limit(6).all()
        
        return render_template('dashboard.html', 
                             user=user, 
                             accounts=accounts, 
                             portfolio_stats=portfolio_stats,
                             recent_transactions=recent_transactions,
                             top_stocks=top_stocks)
    
    @app.route('/stocks')
    def stocks():
        """Страница со списком акций"""
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        query = Stock.query
        
        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Stock.ticker.contains(search.upper()),
                    Stock.name.contains(search)
                )
            )
        
        stocks = query.paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('stocks.html', stocks=stocks, search=search)
    
    @app.route('/stock/<ticker>')
    def stock_detail(ticker):
        """Детальная информация об акции"""
        stock = Stock.query.filter_by(ticker=ticker).first_or_404()
        
        # Получаем информацию о позициях пользователя по этой акции
        user_positions = []
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            # Получаем все транзакции покупки/продажи этой акции
            transactions = Transaction.query.join(Account).filter(
                Account.user_id == user.id,
                Transaction.stock_id == stock.id,
                Transaction.type.in_(['buy', 'sell'])
            ).order_by(Transaction.timestamp.desc()).all()
            
            # Подсчитываем текущую позицию
            total_quantity = 0
            total_cost = 0
            
            for transaction in transactions:
                if transaction.type == 'buy':
                    total_quantity += transaction.quantity
                    total_cost += transaction.quantity * transaction.price
                elif transaction.type == 'sell':
                    total_quantity -= transaction.quantity
                    total_cost -= transaction.quantity * transaction.price
            
            if total_quantity > 0:
                avg_price = total_cost / total_quantity
                current_value = total_quantity * stock.price
                profit_loss = current_value - total_cost
                profit_loss_percent = (profit_loss / total_cost) * 100 if total_cost > 0 else 0
                
                user_positions = {
                    'quantity': total_quantity,
                    'avg_price': avg_price,
                    'current_value': current_value,
                    'profit_loss': profit_loss,
                    'profit_loss_percent': profit_loss_percent
                }
        
        return render_template('stock_detail.html', 
                             stock=stock, 
                             user_positions=user_positions)
    
    @app.route('/account/<int:account_id>')
    def account_detail(account_id):
        """Детальная информация о счете"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        account = Account.query.filter_by(
            id=account_id, 
            user_id=session['user_id']
        ).first_or_404()
        
        transactions = Transaction.query.filter_by(
            account_id=account_id
        ).order_by(Transaction.timestamp.desc()).all()
        
        return render_template('account_detail.html', 
                             account=account, 
                             transactions=transactions)
    
    @app.route('/api/deposit', methods=['POST'])
    def deposit():
        """API для пополнения счета"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        data = request.get_json()
        account_id = data.get('account_id')
        amount = float(data.get('amount', 0))
        
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
    
    @app.route('/api/withdraw', methods=['POST'])
    def withdraw():
        """API для вывода средств"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        data = request.get_json()
        account_id = data.get('account_id')
        amount = float(data.get('amount', 0))
        
        if amount <= 0:
            return jsonify({'error': 'Сумма должна быть положительной'}), 400
        
        account = Account.query.filter_by(
            id=account_id, 
            user_id=session['user_id']
        ).first()
        
        if not account:
            return jsonify({'error': 'Счет не найден'}), 404
        
        if account.balance < amount:
            return jsonify({'error': 'Недостаточно средств на счете'}), 400
        
        # Создаем транзакцию вывода
        transaction = Transaction(
            type='withdrawal',
            amount=amount,
            account=account
        )
        
        # Обновляем баланс счета
        account.balance -= amount
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({'success': True, 'new_balance': account.balance})
    
    @app.route('/api/buy_stock', methods=['POST'])
    def buy_stock():
        """API для покупки акций"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        data = request.get_json()
        account_id = data.get('account_id')
        stock_id = data.get('stock_id')
        quantity = int(data.get('quantity', 0))
        
        if quantity <= 0:
            return jsonify({'error': 'Количество должно быть положительным'}), 400
        
        account = Account.query.filter_by(
            id=account_id, 
            user_id=session['user_id']
        ).first()
        
        stock = Stock.query.get(stock_id)
        
        if not account or not stock:
            return jsonify({'error': 'Счет или акция не найдены'}), 404
        
        total_cost = quantity * stock.price
        
        if account.balance < total_cost:
            return jsonify({'error': 'Недостаточно средств на счете'}), 400
        
        # Создаем транзакцию покупки
        transaction = Transaction(
            type='buy',
            amount=total_cost,
            price=stock.price,
            quantity=quantity,
            account=account,
            stock_id=stock.id
        )
        
        # Обновляем баланс счета
        account.balance -= total_cost
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({'success': True, 'new_balance': account.balance})
    
    @app.route('/api/sell_stock', methods=['POST'])
    def sell_stock():
        """API для продажи акций"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        data = request.get_json()
        account_id = data.get('account_id')
        stock_id = data.get('stock_id')
        quantity = int(data.get('quantity', 0))
        
        if quantity <= 0:
            return jsonify({'error': 'Количество должно быть положительным'}), 400
        
        account = Account.query.filter_by(
            id=account_id, 
            user_id=session['user_id']
        ).first()
        
        stock = Stock.query.get(stock_id)
        
        if not account or not stock:
            return jsonify({'error': 'Счет или акция не найдены'}), 404
        
        # Проверяем, достаточно ли акций для продажи
        buy_transactions = Transaction.query.filter_by(
            account_id=account_id,
            stock_id=stock_id,
            type='buy'
        ).all()
        
        sell_transactions = Transaction.query.filter_by(
            account_id=account_id,
            stock_id=stock_id,
            type='sell'
        ).all()
        
        total_bought = sum(t.quantity for t in buy_transactions)
        total_sold = sum(t.quantity for t in sell_transactions)
        available_quantity = total_bought - total_sold
        
        if available_quantity < quantity:
            return jsonify({'error': 'Недостаточно акций для продажи'}), 400
        
        total_revenue = quantity * stock.price
        
        # Создаем транзакцию продажи
        transaction = Transaction(
            type='sell',
            amount=total_revenue,
            price=stock.price,
            quantity=quantity,
            account=account,
            stock_id=stock.id
        )
        
        # Обновляем баланс счета
        account.balance += total_revenue
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({'success': True, 'new_balance': account.balance})
    
    @app.route('/api/stock_price/<ticker>')
    def get_stock_price(ticker):
        """API для получения актуальной цены акции"""
        try:
            import requests
            
            # Получаем цену с MOEX
            moex_url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
            
            response = requests.get(moex_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Извлекаем текущую цену
            marketdata = data.get('marketdata', {})
            columns = marketdata.get('columns', [])
            rows = marketdata.get('data', [])
            
            if columns and rows and len(rows) > 0:
                last_idx = columns.index('LAST') if 'LAST' in columns else -1
                
                if last_idx >= 0 and len(rows[0]) > last_idx and rows[0][last_idx]:
                    current_price = float(rows[0][last_idx])
                    
                    # Обновляем цену в базе данных
                    stock = Stock.query.filter_by(ticker=ticker).first()
                    if stock:
                        stock.price = current_price
                        db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'ticker': ticker,
                        'price': current_price
                    })
            
            # Если не удалось получить текущую цену, возвращаем из БД
            stock = Stock.query.filter_by(ticker=ticker).first()
            if stock:
                return jsonify({
                    'success': True,
                    'ticker': ticker,
                    'price': stock.price,
                    'cached': True
                })
            
            return jsonify({'success': False, 'error': 'Stock not found'}), 404
            
        except Exception as e:
            # В случае ошибки возвращаем цену из БД
            stock = Stock.query.filter_by(ticker=ticker).first()
            if stock:
                return jsonify({
                    'success': True,
                    'ticker': ticker,
                    'price': stock.price,
                    'cached': True,
                    'error': str(e)
                })
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
