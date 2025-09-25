# Руководство по развертыванию InvestBot

## Быстрый старт (разработка)

1. **Клонируйте репозиторий и установите зависимости:**
```bash
git clone <repository-url>
cd InvestikBotik
pip install -r requirements.txt
```

2. **Настройте переменные окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл
```

3. **Инициализируйте базу данных:**
```bash
python app.py  # Создаст базу данных автоматически
```

4. **Загрузите данные об акциях:**
```bash
python stock_parser.py
```

5. **Создайте демо данные (опционально):**
```bash
python demo_data.py
```

6. **Запустите приложение:**
```bash
python app.py
```

Приложение будет доступно по адресу: http://localhost:5000

## Развертывание на сервере

### 1. Подготовка сервера (Ubuntu/Debian)

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Python и необходимые пакеты
sudo apt install python3 python3-pip python3-venv nginx supervisor -y

# Создайте пользователя для приложения
sudo adduser investbot
sudo usermod -aG www-data investbot
```

### 2. Настройка приложения

```bash
# Переключитесь на пользователя investbot
sudo su - investbot

# Клонируйте репозиторий
git clone <repository-url> /home/investbot/InvestikBotik
cd /home/investbot/InvestikBotik

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Настройте переменные окружения
cp .env.example .env
nano .env  # Отредактируйте файл
```

### 3. Настройка базы данных (PostgreSQL)

```bash
# Установите PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Создайте базу данных
sudo -u postgres psql
CREATE DATABASE investbot;
CREATE USER investbot WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE investbot TO investbot;
\q

# Обновите DATABASE_URL в .env
DATABASE_URL=postgresql://investbot:your_password@localhost/investbot
```

### 4. Настройка Gunicorn

Создайте файл `/home/investbot/InvestikBotik/gunicorn.conf.py`:

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
```

### 5. Настройка Supervisor

Создайте файл `/etc/supervisor/conf.d/investbot.conf`:

```ini
[program:investbot]
command=/home/investbot/InvestikBotik/venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
directory=/home/investbot/InvestikBotik
user=investbot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/investbot.log
```

```bash
# Перезапустите supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start investbot
```

### 6. Настройка Nginx

Создайте файл `/etc/nginx/sites-available/investbot`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/investbot/InvestikBotik/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Активируйте сайт
sudo ln -s /etc/nginx/sites-available/investbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Настройка SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### 8. Настройка автоматического обновления цен

Добавьте в crontab:

```bash
crontab -e
# Добавьте строку для обновления цен каждый час в рабочие дни
0 9-18 * * 1-5 /home/investbot/InvestikBotik/venv/bin/python /home/investbot/InvestikBotik/update_prices.py
```

## Настройка Telegram бота

1. **Создайте бота через @BotFather**
2. **Получите токен и добавьте в .env:**
```
TELEGRAM_BOT_TOKEN=your_bot_token
```

3. **Настройте Web App в боте:**
   - Отправьте команду `/setmenubutton` в @BotFather
   - Выберите вашего бота
   - Установите кнопку меню с URL: `https://your-domain.com`

4. **Запустите бота:**
```bash
python telegram_bot.py
```

## Мониторинг и логи

```bash
# Просмотр логов приложения
sudo tail -f /var/log/investbot.log

# Статус приложения
sudo supervisorctl status investbot

# Перезапуск приложения
sudo supervisorctl restart investbot

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Резервное копирование

Создайте скрипт для резервного копирования базы данных:

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump investbot > /home/investbot/backups/investbot_$DATE.sql
find /home/investbot/backups -name "*.sql" -mtime +7 -delete
```

Добавьте в crontab для ежедневного бэкапа:
```
0 2 * * * /home/investbot/backup.sh
```

## Обновление приложения

```bash
cd /home/investbot/InvestikBotik
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart investbot
```
