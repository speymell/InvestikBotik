from app import app
from database import db, User, Account, Stock, Transaction
import random

def create_demo_data():
    """Создание демонстрационных данных"""
    with app.app_context():
        # Проверяем, есть ли уже демо пользователь
        demo_user = User.query.filter_by(username='demo_user').first()
        
        if demo_user:
            print("Демо пользователь уже существует")
            return
        
        # Создаем демо пользователя
        demo_user = User(
            telegram_id='123456789',
            username='demo_user'
        )
        db.session.add(demo_user)
        db.session.flush()  # Получаем ID пользователя
        
        # Создаем основной счет
        main_account = Account(
            name='Основной счет',
            balance=50000.0,
            user_id=demo_user.id
        )
        db.session.add(main_account)
        
        # Создаем дополнительный счет
        second_account = Account(
            name='Инвестиционный счет',
            balance=25000.0,
            user_id=demo_user.id
        )
        db.session.add(second_account)
        db.session.flush()
        
        # Получаем несколько акций для демонстрации
        stocks = Stock.query.filter(Stock.price > 0).limit(10).all()
        
        if not stocks:
            print("Нет акций в базе данных. Запустите сначала stock_parser.py")
            return
        
        # Создаем транзакции пополнения
        deposit1 = Transaction(
            type='deposit',
            amount=50000.0,
            account_id=main_account.id
        )
        db.session.add(deposit1)
        
        deposit2 = Transaction(
            type='deposit',
            amount=25000.0,
            account_id=second_account.id
        )
        db.session.add(deposit2)
        
        # Создаем несколько покупок акций
        for i, stock in enumerate(stocks[:5]):
            if stock.price > 0:
                quantity = random.randint(10, 100)
                total_cost = quantity * stock.price
                
                # Выбираем счет (чередуем)
                account = main_account if i % 2 == 0 else second_account
                
                if account.balance >= total_cost:
                    # Создаем транзакцию покупки
                    buy_transaction = Transaction(
                        type='buy',
                        amount=total_cost,
                        price=stock.price,
                        quantity=quantity,
                        account_id=account.id,
                        stock_id=stock.id
                    )
                    db.session.add(buy_transaction)
                    
                    # Обновляем баланс счета
                    account.balance -= total_cost
        
        # Создаем несколько продаж (для демонстрации прибыли/убытков)
        for i, stock in enumerate(stocks[2:4]):  # Продаем 2 акции
            if stock.price > 0:
                # Проверяем, есть ли у нас эти акции
                buy_transactions = Transaction.query.filter_by(
                    stock_id=stock.id,
                    type='buy'
                ).all()
                
                if buy_transactions:
                    total_bought = sum(t.quantity for t in buy_transactions)
                    sell_quantity = min(total_bought // 2, 20)  # Продаем половину или максимум 20
                    
                    if sell_quantity > 0:
                        # Имитируем изменение цены (±20%)
                        new_price = stock.price * random.uniform(0.8, 1.2)
                        total_revenue = sell_quantity * new_price
                        
                        account = main_account if i % 2 == 0 else second_account
                        
                        sell_transaction = Transaction(
                            type='sell',
                            amount=total_revenue,
                            price=new_price,
                            quantity=sell_quantity,
                            account_id=account.id,
                            stock_id=stock.id
                        )
                        db.session.add(sell_transaction)
                        
                        # Обновляем баланс счета
                        account.balance += total_revenue
        
        try:
            db.session.commit()
            print("Демонстрационные данные успешно созданы!")
            print(f"Пользователь: {demo_user.username}")
            print(f"Telegram ID: {demo_user.telegram_id}")
            print("Для входа используйте URL: http://localhost:5000/login?telegram_id=123456789&username=demo_user")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при создании демо данных: {e}")

if __name__ == "__main__":
    create_demo_data()
