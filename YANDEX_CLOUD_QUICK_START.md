# 🚀 Быстрый запуск InvestBot на Yandex Cloud

## Минимальная конфигурация для тестирования

Если вы хотите быстро развернуть приложение для тестирования, используйте этот упрощенный подход:

### Вариант 1: Одна VM + SQLite (самый простой)

#### 1. Создайте VM через веб-консоль:
- **Compute Cloud** → **Создать ВМ**
- **Образ**: Ubuntu 22.04 LTS
- **vCPU**: 2, **RAM**: 2 ГБ, **Диск**: 20 ГБ
- **Публичный IP**: Да
- **SSH ключ**: Загрузите свой публичный ключ

#### 2. Подключитесь и разверните:

```bash
# Подключение к VM
ssh ubuntu@<external-ip>

# Установка зависимостей
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git nginx -y

# Клонирование проекта
git clone <your-repo-url> investbot
cd investbot

# Настройка Python окружения
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Создание .env файла
cp .env.example .env
nano .env  # Отредактируйте настройки
```

#### 3. Запуск приложения:

```bash
# Инициализация БД и загрузка данных
python app.py &  # Запустите и остановите Ctrl+C после создания БД
python stock_parser.py
python demo_data.py

# Запуск в продакшене
nohup python -m gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app &
```

#### 4. Настройка Nginx:

```bash
sudo nano /etc/nginx/sites-available/default
```

```nginx
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /home/ubuntu/investbot/static;
    }
}
```

```bash
sudo systemctl reload nginx
```

**Готово!** Приложение доступно по IP адресу VM.

---

### Вариант 2: VM + Managed PostgreSQL (рекомендуемый)

#### 1. Создайте PostgreSQL кластер:
- **Managed Service for PostgreSQL**
- **Класс**: s2.micro
- **Хранилище**: 10 ГБ
- **Публичный доступ**: Да (для упрощения)

#### 2. Создайте VM (как в варианте 1)

#### 3. Обновите .env файл:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
DATABASE_URL=postgresql://user:password@c-xxxxx.rw.mdb.yandexcloud.net:6432/investbot
TELEGRAM_BOT_TOKEN=your-bot-token
WEB_APP_URL=http://your-vm-ip
```

#### 4. Запустите приложение (как в варианте 1)

---

### Вариант 3: Serverless (для экспериментов)

Если хотите попробовать serverless подход:

#### 1. Используйте **Serverless Containers**:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "wsgi:app"]
```

#### 2. Создайте контейнер:

```bash
# Соберите образ
docker build -t investbot .

# Загрузите в Container Registry
yc container registry create --name investbot-registry
docker tag investbot cr.yandex/your-registry-id/investbot:latest
docker push cr.yandex/your-registry-id/investbot:latest
```

#### 3. Создайте Serverless Container:

```bash
yc serverless container create --name investbot-container
yc serverless container revision deploy \
  --container-name investbot-container \
  --image cr.yandex/your-registry-id/investbot:latest \
  --memory 1GB \
  --execution-timeout 30s
```

---

## 💡 Рекомендации по выбору варианта:

### Вариант 1 (VM + SQLite) - для тестирования
**Плюсы:**
- Быстрая настройка
- Низкая стоимость (~1,500₽/мес)
- Простота управления

**Минусы:**
- Не подходит для продакшена
- Нет резервного копирования
- Ограниченная производительность

### Вариант 2 (VM + PostgreSQL) - рекомендуемый
**Плюсы:**
- Надежная БД с резервным копированием
- Хорошая производительность
- Готовность к продакшену

**Минусы:**
- Выше стоимость (~4,000₽/мес)
- Чуть сложнее настройка

### Вариант 3 (Serverless) - для экспериментов
**Плюсы:**
- Автомасштабирование
- Оплата по использованию
- Высокая доступность

**Минусы:**
- Требует рефакторинга кода
- Холодный старт
- Ограничения по времени выполнения

---

## 🔧 Быстрые команды для управления:

```bash
# Проверка статуса приложения
ps aux | grep gunicorn

# Перезапуск приложения
pkill -f gunicorn
nohup python -m gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app &

# Просмотр логов
tail -f nohup.out

# Обновление цен акций
cd /home/ubuntu/investbot
source venv/bin/activate
python update_prices.py

# Создание резервной копии (для SQLite)
cp investbot.db investbot_backup_$(date +%Y%m%d).db
```

---

## 🎯 Следующие шаги после развертывания:

1. **Настройте домен** (если нужен)
2. **Получите SSL сертификат** (Let's Encrypt или Certificate Manager)
3. **Настройте мониторинг** в Yandex Monitoring
4. **Создайте Telegram бота** и настройте интеграцию
5. **Настройте автоматическое обновление цен** (cron)
6. **Настройте резервное копирование**

Начните с Варианта 1 для быстрого тестирования, затем переходите к Варианту 2 для продакшена!
