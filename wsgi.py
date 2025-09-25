"""
WSGI файл для запуска приложения в продакшене
Используется с Gunicorn или другими WSGI серверами
"""

import os
from app import create_app

# Создаем приложение для продакшена
app = create_app('production')

if __name__ == "__main__":
    app.run()
