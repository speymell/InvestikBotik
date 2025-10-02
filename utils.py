from database import db, User, Account, Stock, Transaction
from sqlalchemy import func

def calculate_portfolio_stats(user_id):
    """Расчет статистики портфеля пользователя"""
    user = User.query.get(user_id)
    if not user:
        return None
    
    accounts = Account.query.filter_by(user_id=user_id).all()
    
    portfolio_stats = {
        'total_balance': 0,
        'total_invested': 0,
        'total_current_value': 0,
        'total_profit_loss': 0,
        'total_profit_loss_percent': 0,
        'positions': [],
        'accounts_stats': []
    }
    
    for account in accounts:
        account_stats = calculate_account_stats(account.id)
        portfolio_stats['accounts_stats'].append(account_stats)
        
        portfolio_stats['total_balance'] += account.balance
        portfolio_stats['total_invested'] += account_stats['total_invested']
        portfolio_stats['total_current_value'] += account_stats['total_current_value']
        
        # Объединяем позиции по акциям
        for position in account_stats['positions']:
            existing_position = next(
                (p for p in portfolio_stats['positions'] if p['stock_id'] == position['stock_id']), 
                None
            )
            
            if existing_position:
                existing_position['quantity'] += position['quantity']
                existing_position['total_cost'] += position['total_cost']
                existing_position['current_value'] += position['current_value']
                existing_position['avg_price'] = existing_position['total_cost'] / existing_position['quantity']
                existing_position['profit_loss'] = existing_position['current_value'] - existing_position['total_cost']
                existing_position['profit_loss_percent'] = (existing_position['profit_loss'] / existing_position['total_cost']) * 100 if existing_position['total_cost'] > 0 else 0
            else:
                portfolio_stats['positions'].append(position.copy())
    
    # Общая прибыль/убыток
    portfolio_stats['total_profit_loss'] = portfolio_stats['total_current_value'] - portfolio_stats['total_invested']
    portfolio_stats['total_profit_loss_percent'] = (portfolio_stats['total_profit_loss'] / portfolio_stats['total_invested']) * 100 if portfolio_stats['total_invested'] > 0 else 0
    
    return portfolio_stats

def calculate_account_stats(account_id):
    """Расчет статистики по конкретному счету"""
    account = Account.query.get(account_id)
    if not account:
        return None
    
    # Получаем все транзакции покупки и продажи
    transactions = Transaction.query.filter_by(
        account_id=account_id
    ).filter(
        Transaction.type.in_(['buy', 'sell'])
    ).all()
    
    # Группируем по акциям
    stock_positions = {}
    
    for transaction in transactions:
        stock_id = transaction.stock_id
        
        if stock_id not in stock_positions:
            # Получаем объект акции из базы данных
            from database import Stock
            stock = Stock.query.get(stock_id)
            stock_positions[stock_id] = {
                'stock_id': stock_id,
                'stock': stock,
                'quantity': 0,
                'total_cost': 0
            }
        
        if transaction.type == 'buy':
            stock_positions[stock_id]['quantity'] += transaction.quantity
            stock_positions[stock_id]['total_cost'] += transaction.quantity * transaction.price
        elif transaction.type == 'sell':
            stock_positions[stock_id]['quantity'] -= transaction.quantity
            stock_positions[stock_id]['total_cost'] -= transaction.quantity * transaction.price
    
    # Убираем позиции с нулевым количеством и рассчитываем статистику
    active_positions = []
    total_invested = 0
    total_current_value = 0
    
    for stock_id, position in stock_positions.items():
        if position['quantity'] > 0:
            position['avg_price'] = position['total_cost'] / position['quantity']
            position['current_value'] = position['quantity'] * position['stock'].price
            position['profit_loss'] = position['current_value'] - position['total_cost']
            position['profit_loss_percent'] = (position['profit_loss'] / position['total_cost']) * 100 if position['total_cost'] > 0 else 0
            
            active_positions.append(position)
            total_invested += position['total_cost']
            total_current_value += position['current_value']
    
    return {
        'account': account,
        'positions': active_positions,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_profit_loss': total_current_value - total_invested,
        'total_profit_loss_percent': ((total_current_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0
    }

def get_top_stocks(limit=10):
    """Получить топ акций по объему торгов или другим критериям"""
    # Пока что просто возвращаем акции с самыми высокими ценами
    return Stock.query.filter(Stock.price > 0).order_by(Stock.price.desc()).limit(limit).all()

def get_user_watchlist(user_id):
    """Получить список отслеживаемых акций пользователя"""
    # В будущем можно добавить таблицу для избранных акций
    # Пока что возвращаем акции, которыми торговал пользователь
    user_stocks = db.session.query(Stock).join(Transaction).join(Account).filter(
        Account.user_id == user_id
    ).distinct().all()
    
    return user_stocks

def format_currency(amount):
    """Форматирование суммы в рублях"""
    return f"{amount:,.2f} ₽"

def format_percent(percent):
    """Форматирование процентов"""
    return f"{percent:+.2f}%"
