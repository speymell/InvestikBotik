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
    
    # Для PostgreSQL используем psycopg3
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif _db_url.startswith('postgresql://') and '+psycopg' not in _db_url:
        _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    SQLALCHEMY_DATABASE_URI = _db_url
    
    # Настройки для PostgreSQL (применяются только если используется PostgreSQL)
    if 'postgresql' in _db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 10
            }
        }

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    _db_url = os.environ.get('DATABASE_URL') or 'sqlite:///investbot.db'
    
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif _db_url.startswith('postgresql://') and '+psycopg' not in _db_url:
        _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    SQLALCHEMY_DATABASE_URI = _db_url
    
    # Настройки для PostgreSQL
    if 'postgresql' in _db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 10
            }
        }

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
