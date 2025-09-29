import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    # Поддержка обоих форматов URL для Postgres (postgres:// и postgresql://)
    _db_url = os.environ.get('DATABASE_URL') or 'sqlite:///investbot.db'
    if _db_url.startswith('postgres://'):
        # SQLAlchemy ожидает postgresql:// или postgresql+psycopg2://
        _db_url = _db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif _db_url.startswith('postgresql://') and '+psycopg2' not in _db_url:
        _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    _db_url = os.environ.get('DATABASE_URL') or 'sqlite:///investbot.db'
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif _db_url.startswith('postgresql://') and '+psycopg2' not in _db_url:
        _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url

class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
