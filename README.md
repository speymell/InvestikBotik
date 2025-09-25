# InvestBot - Веб-сервис для отслеживания инвестиций

InvestBot - это веб-приложение для отслеживания инвестиций в российские акции с интеграцией в Telegram.

## Возможности

- 📊 Отслеживание портфеля акций
- 💰 Управление несколькими счетами
- 📈 Актуальные котировки российских акций
- 📱 Интеграция с Telegram ботом
- 💹 Расчет прибыли и убытков
- 📋 История всех транзакций

## Установка и запуск

### Требования

- Python 3.8+
- pip

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск приложения

1. Запустите приложение:
```bash
python app.py
```

2. Откройте браузер и перейдите по адресу: http://localhost:5000

### Первоначальная настройка

1. При первом запуске будет создана база данных SQLite (`investbot.db`)
2. Для загрузки данных об акциях запустите парсер:
```bash
python stock_parser.py
```

## Структура проекта

```
InvestikBotik/
├── app.py              # Главный файл приложения
├── database.py         # Модели базы данных
├── routes.py           # Маршруты и API
├── stock_parser.py     # Парсер данных об акциях
├── requirements.txt    # Зависимости
├── templates/          # HTML шаблоны
│   ├── layout.html
│   ├── index.html
│   ├── dashboard.html
│   ├── stocks.html
│   ├── stock_detail.html
│   ├── account_detail.html
│   └── login.html
└── static/            # Статические файлы (CSS, JS)
```

## API Endpoints

### Пользовательские операции
- `GET /login` - Вход через Telegram
- `GET /dashboard` - Панель пользователя
- `GET /stocks` - Список акций
- `GET /stock/<ticker>` - Детали акции
- `GET /account/<id>` - Детали счета

### API для операций
- `POST /api/deposit` - Пополнение счета
- `POST /api/withdraw` - Вывод средств
- `POST /api/buy_stock` - Покупка акций
- `POST /api/sell_stock` - Продажа акций

## Модели базы данных

### User (Пользователи)
- `id` - Уникальный идентификатор
- `telegram_id` - ID в Telegram
- `username` - Имя пользователя

### Account (Счета)
- `id` - Уникальный идентификатор
- `name` - Название счета
- `balance` - Баланс
- `user_id` - ID пользователя

### Stock (Акции)
- `id` - Уникальный идентификатор
- `ticker` - Тикер акции
- `name` - Название компании
- `price` - Текущая цена

### Transaction (Транзакции)
- `id` - Уникальный идентификатор
- `type` - Тип операции (deposit, withdrawal, buy, sell)
- `amount` - Сумма
- `price` - Цена за акцию (для buy/sell)
- `quantity` - Количество акций (для buy/sell)
- `timestamp` - Время операции
- `account_id` - ID счета
- `stock_id` - ID акции

## Интеграция с Telegram

Для работы с Telegram ботом:

1. Создайте бота через @BotFather
2. Получите токен бота
3. Настройте Web App в боте с URL вашего сервера
4. Пользователи смогут открывать приложение прямо из Telegram

Пример URL для входа: `https://yourserver.com/login?telegram_id=123456&username=user`

## Развертывание на сервере

### Для продакшена рекомендуется:

1. Использовать PostgreSQL вместо SQLite
2. Настроить переменные окружения:
   - `SECRET_KEY` - секретный ключ для сессий
   - `DATABASE_URL` - URL базы данных
3. Использовать WSGI сервер (например, Gunicorn)
4. Настроить обратный прокси (nginx)

### Пример запуска с Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Обновление данных об акциях

Для регулярного обновления котировок можно настроить cron задачу:

```bash
# Обновление каждый час в рабочие дни
0 9-18 * * 1-5 cd /path/to/project && python stock_parser.py
```

## Автор

© 2025 Polygalov V.

## Лицензия

Этот проект создан для демонстрационных целей.
