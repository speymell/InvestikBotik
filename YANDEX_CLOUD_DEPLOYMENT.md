# Развертывание InvestBot на Yandex Cloud

## 🏗️ Архитектура решения

```
Internet → Application Load Balancer → Compute Cloud VM → Managed PostgreSQL
                                    ↓
                              Object Storage (статика)
```

## 📋 Необходимые сервисы Yandex Cloud

1. **Compute Cloud** - виртуальная машина Ubuntu 22.04
2. **Managed Service for PostgreSQL** - база данных
3. **Application Load Balancer** - SSL терминация и балансировка
4. **Virtual Private Cloud** - сетевая инфраструктура
5. **Certificate Manager** - SSL сертификаты
6. **Object Storage** - для статических файлов (опционально)

## 🚀 Пошаговое развертывание

### Шаг 1: Подготовка инфраструктуры

#### 1.1 Создание VPC и подсетей

```bash
# Установите Yandex Cloud CLI
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
yc init

# Создайте VPC
yc vpc network create --name investbot-network

# Создайте подсеть
yc vpc subnet create \
  --name investbot-subnet \
  --network-name investbot-network \
  --zone ru-central1-a \
  --range 10.0.0.0/24
```

#### 1.2 Создание группы безопасности

```bash
yc vpc security-group create \
  --name investbot-sg \
  --network-name investbot-network \
  --rule "direction=ingress,port=22,protocol=tcp,v4-cidrs=[0.0.0.0/0]" \
  --rule "direction=ingress,port=80,protocol=tcp,v4-cidrs=[0.0.0.0/0]" \
  --rule "direction=ingress,port=443,protocol=tcp,v4-cidrs=[0.0.0.0/0]" \
  --rule "direction=ingress,port=8000,protocol=tcp,v4-cidrs=[10.0.0.0/24]" \
  --rule "direction=egress,protocol=any,v4-cidrs=[0.0.0.0/0]"
```

### Шаг 2: Создание базы данных PostgreSQL

#### 2.1 Через веб-консоль:
1. Перейдите в **Managed Service for PostgreSQL**
2. Нажмите **Создать кластер**
3. Настройки:
   - **Имя**: `investbot-db`
   - **Окружение**: `PRODUCTION`
   - **Версия**: `15`
   - **Класс хоста**: `s2.micro` (для начала)
   - **Хранилище**: `10 GB SSD`
   - **Сеть**: `investbot-network`
   - **Группа безопасности**: `investbot-sg`

#### 2.2 Создание базы данных и пользователя:

```sql
-- Подключитесь к кластеру и выполните:
CREATE DATABASE investbot;
CREATE USER investbot_user WITH PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE investbot TO investbot_user;
```

### Шаг 3: Создание виртуальной машины

#### 3.1 Создание VM через CLI:

```bash
yc compute instance create \
  --name investbot-vm \
  --zone ru-central1-a \
  --network-interface subnet-name=investbot-subnet,nat-ip-version=ipv4,security-group-ids=[sg-id] \
  --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts,size=20GB \
  --ssh-key ~/.ssh/id_rsa.pub \
  --service-account-name default-sa \
  --memory 2GB \
  --cores 2
```

#### 3.2 Подключение к VM:

```bash
# Получите внешний IP
yc compute instance get investbot-vm

# Подключитесь по SSH
ssh ubuntu@<external-ip>
```

### Шаг 4: Настройка приложения на VM

#### 4.1 Установка зависимостей:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3 python3-pip python3-venv git nginx supervisor postgresql-client -y

# Создание пользователя для приложения
sudo adduser --system --group investbot
sudo usermod -aG www-data investbot
```

#### 4.2 Развертывание приложения:

```bash
# Переключение на пользователя investbot
sudo su - investbot

# Клонирование репозитория
git clone https://github.com/your-username/InvestikBotik.git /home/investbot/app
cd /home/investbot/app

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

#### 4.3 Настройка переменных окружения:

```bash
# Создайте файл .env
nano /home/investbot/app/.env
```

```env
# Содержимое .env файла
SECRET_KEY=your-super-secret-key-here
FLASK_ENV=production
DATABASE_URL=postgresql://investbot_user:secure_password_123@c-cluster-id.rw.mdb.yandexcloud.net:6432/investbot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
WEB_APP_URL=https://your-domain.com
```

#### 4.4 Инициализация базы данных:

```bash
cd /home/investbot/app
source venv/bin/activate

# Создание таблиц
python app.py
# Нажмите Ctrl+C после создания таблиц

# Загрузка данных об акциях
python stock_parser.py

# Создание демо данных (опционально)
python demo_data.py
```

### Шаг 5: Настройка Gunicorn и Supervisor

#### 5.1 Создание конфигурации Gunicorn:

```bash
# Создайте файл gunicorn.conf.py
nano /home/investbot/app/gunicorn.conf.py
```

```python
bind = "127.0.0.1:8000"
workers = 2
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
user = "investbot"
group = "investbot"
```

#### 5.2 Настройка Supervisor:

```bash
# Создайте конфигурацию supervisor
sudo nano /etc/supervisor/conf.d/investbot.conf
```

```ini
[program:investbot]
command=/home/investbot/app/venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
directory=/home/investbot/app
user=investbot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/investbot.log
environment=PATH="/home/investbot/app/venv/bin"
```

```bash
# Перезапуск supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start investbot
```

### Шаг 6: Настройка Nginx

```bash
# Создайте конфигурацию Nginx
sudo nano /etc/nginx/sites-available/investbot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Редирект на HTTPS (будет настроен позже)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL сертификаты (будут настроены через Certificate Manager)
    ssl_certificate /etc/ssl/certs/investbot.crt;
    ssl_certificate_key /etc/ssl/private/investbot.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/investbot/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Безопасность
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
```

```bash
# Активация сайта
sudo ln -s /etc/nginx/sites-available/investbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Шаг 7: Настройка Application Load Balancer

#### 7.1 Создание целевой группы:

```bash
yc alb target-group create investbot-tg \
  --target subnet-name=investbot-subnet,ip-address=<vm-internal-ip>
```

#### 7.2 Создание группы бэкендов:

```bash
yc alb backend-group create investbot-bg \
  --http-backend name=investbot-backend,target-group-id=<target-group-id>,port=80,weight=1
```

#### 7.3 Создание HTTP роутера:

```bash
yc alb http-router create investbot-router \
  --virtual-host name=investbot-vh,authority=your-domain.com \
  --route name=investbot-route,backend-group-id=<backend-group-id>
```

#### 7.4 Создание балансировщика:

```bash
yc alb load-balancer create investbot-alb \
  --network-name investbot-network \
  --listener name=investbot-listener,external-ipv4-endpoint,port=80,http-router-id=<router-id>
```

### Шаг 8: Настройка SSL через Certificate Manager

#### 8.1 Создание сертификата:

```bash
yc certificate-manager certificate request \
  --name investbot-cert \
  --domains your-domain.com
```

#### 8.2 Подтверждение домена:
Следуйте инструкциям в консоли для подтверждения владения доменом.

#### 8.3 Обновление балансировщика для HTTPS:

```bash
yc alb load-balancer update-listener investbot-alb \
  --listener-name investbot-listener \
  --external-ipv4-endpoint port=443 \
  --tls default-handler-name=investbot-handler,certificate-id=<cert-id>
```

### Шаг 9: Настройка автоматического обновления цен

```bash
# Добавьте задачу в crontab
sudo crontab -e -u investbot

# Добавьте строку:
0 9-18 * * 1-5 /home/investbot/app/venv/bin/python /home/investbot/app/update_prices.py
```

### Шаг 10: Настройка мониторинга

#### 10.1 Используйте Yandex Monitoring для отслеживания:
- Загрузка CPU и памяти VM
- Состояние базы данных PostgreSQL
- Метрики Application Load Balancer

#### 10.2 Настройка алертов:
```bash
# Создайте алерты для критических метрик
yc monitoring alert create \
  --name "InvestBot High CPU" \
  --description "CPU usage > 80%" \
  --condition "cpu_usage > 80"
```

## 💰 Примерная стоимость в месяц

- **Compute Cloud** (2 vCPU, 2GB RAM): ~1,500₽
- **Managed PostgreSQL** (s2.micro): ~2,000₽
- **Application Load Balancer**: ~500₽
- **Certificate Manager**: бесплатно
- **Трафик**: ~200₽

**Итого**: ~4,200₽/месяц

## 🔧 Полезные команды для управления

```bash
# Проверка статуса приложения
sudo supervisorctl status investbot

# Перезапуск приложения
sudo supervisorctl restart investbot

# Просмотр логов
sudo tail -f /var/log/investbot.log

# Обновление приложения
cd /home/investbot/app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart investbot

# Резервное копирование БД
pg_dump "postgresql://investbot_user:password@host:6432/investbot" > backup.sql
```

## 🚀 Альтернативный вариант: Serverless

Для меньших нагрузок можно использовать:
- **Cloud Functions** для API
- **Serverless Containers** для веб-интерфейса
- **YDB** вместо PostgreSQL

Это будет дешевле, но потребует рефакторинга кода.

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `sudo tail -f /var/log/investbot.log`
2. Проверьте статус сервисов: `sudo supervisorctl status`
3. Проверьте подключение к БД: `psql "postgresql://..."`
4. Проверьте группы безопасности в Yandex Cloud Console
