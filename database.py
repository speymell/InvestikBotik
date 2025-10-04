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

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'deposit', 'withdrawal', 'buy', 'sell'
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=True) # price per stock
    quantity = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=True)
