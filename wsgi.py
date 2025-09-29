"""
WSGI файл для запуска приложения в продакшене
Используется с Gunicorn или другими WSGI серверами
"""

import os
from app import create_app
from database import db

# Создаем приложение для продакшена
app = create_app('production')

# На первом деплое в Render создадим таблицы, если их ещё нет
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        # Не падаем при ошибке подключения к БД на этапе билда
        # Логи можно посмотреть в Render Dashboard
        pass

if __name__ == "__main__":
    app.run()
