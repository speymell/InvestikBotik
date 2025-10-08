from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(80), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    accounts = db.relationship('Account', backref='user', lazy=True)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='account', lazy=True)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, default=0.0)
    logo_url = db.Column(db.String(255), nullable=True)
    sector = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    instrument_type = db.Column(db.String(20), nullable=False, default='share')
    face_value = db.Column(db.Float, nullable=True)
    # Новые метрики торгов
    turnover = db.Column(db.Float, nullable=True)  # оборот за день (в валюте котировок, обычно рубли)
    volume = db.Column(db.BigInteger, nullable=True)  # количество бумаг за день (BIGINT для Postgres)
    change_pct = db.Column(db.Float, nullable=True)  # изменение цены за день, %
    # Купонные/дивидендные метаданные (в основном для облигаций)
    coupon_value = db.Column(db.Float, nullable=True)      # Сумма купона на 1 бумагу (в валюте бумаги)
    coupon_percent = db.Column(db.Float, nullable=True)    # Купонная ставка, % годовых (если доступно)
    coupon_period = db.Column(db.Integer, nullable=True)   # Периодичность купонов (в днях)
    accrued_int = db.Column(db.Float, nullable=True)       # НКД (накопленный купонный доход)
    next_coupon_date = db.Column(db.Date, nullable=True)   # Дата следующего купона
    maturity_date = db.Column(db.Date, nullable=True)      # Дата погашения
    lot_size = db.Column(db.Integer, nullable=True)        # Размер лота
    currency = db.Column(db.String(12), nullable=True)     # Валюта котировок (обычно SUR)
    isin = db.Column(db.String(36), nullable=True)         # ISIN

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'deposit', 'withdrawal', 'buy', 'sell'
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=True) # price per stock
    quantity = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=True)
    # Relationship to access stock from transaction in templates
    stock = db.relationship('Stock', backref='transactions', lazy=True)

# Избранное (Watchlist)
class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    # Уникальная пара (user, stock)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'stock_id', name='uq_watchlist_user_stock'),
    )
    stock = db.relationship('Stock', lazy=True)

# Алерты по цене
class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'above' | 'below'
    price = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    last_triggered_at = db.Column(db.DateTime, nullable=True)
    stock = db.relationship('Stock', lazy=True)

# Денежные потоки (купоны, дивиденды)
class CashFlow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'coupon' | 'dividend'
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=True)
    ticker = db.Column(db.String(20), nullable=True)
    currency = db.Column(db.String(12), nullable=True)
    record_date = db.Column(db.Date, nullable=True)   # дата фиксации/дата купона
    pay_date = db.Column(db.Date, nullable=True)      # дата выплаты (если отличается)
    amount_per_security = db.Column(db.Float, nullable=True)
    quantity_at_record = db.Column(db.Integer, nullable=True)
    gross_amount = db.Column(db.Float, nullable=True)
    net_amount = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    # Быстрые связи
    stock = db.relationship('Stock', lazy=True)
    account = db.relationship('Account', lazy=True)
