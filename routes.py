from flask import render_template, request, jsonify, redirect, url_for, session
from database import db, User, Account, Stock, Transaction
from utils import calculate_portfolio_stats, get_top_stocks
import datetime

def init_routes(app):
    
    @app.route('/health')
    def health():
        """Health check endpoint для Render"""
        return jsonify({'status': 'ok', 'message': 'InvestBot is running'})
    
    @app.route('/')
    def index():
        current_year = datetime.datetime.now().year
        return render_template('index.html', year=current_year)
    
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
    
    @app.route('/dashboard')
    def dashboard():
        """Главная панель пользователя"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        accounts = Account.query.filter_by(user_id=user.id).all()
        
        # Получаем статистику портфеля
        portfolio_stats = calculate_portfolio_stats(user.id)
        
        # Получаем последние транзакции
        recent_transactions = Transaction.query.join(Account).filter(
            Account.user_id == user.id
        ).order_by(Transaction.timestamp.desc()).limit(10).all()
        
        # Получаем топ акций
        top_stocks = get_top_stocks(5)
        
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
            query = query.filter(
                db.or_(
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
