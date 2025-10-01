# Исправление ошибки 404 на Render

## Проблема
После обновления кода на Render появляется ошибка "Not Found" на всех страницах, кроме `/health`.

## Возможные причины

1. **Render не перезапустился** после push изменений
2. **Проблема с импортами** или инициализацией маршрутов
3. **Ошибка при рендеринге шаблонов**

## Решение

### Шаг 1: Закоммитить и запушить изменения

```bash
git add .
git commit -m "Fix routes and add error handling"
git push
```

### Шаг 2: Принудительный перезапуск на Render

1. Зайдите на https://dashboard.render.com
2. Откройте ваш сервис **investikbotik**
3. Нажмите **"Manual Deploy"** → **"Clear build cache & deploy"**
4. Дождитесь завершения деплоя (5-10 минут)

### Шаг 3: Проверка

После деплоя проверьте:

1. **Health check**: https://investikbotik.onrender.com/health
   - Должен вернуть: `{"status":"ok","message":"InvestBot is running"}`

2. **Test endpoint**: https://investikbotik.onrender.com/test
   - Должен вернуть: `{"status":"ok","message":"Routes are working"}`

3. **Главная страница**: https://investikbotik.onrender.com/
   - Должна открыться главная страница с кнопкой "Попробовать демо"

### Шаг 4: Если проблема сохраняется

Проверьте логи на Render:

1. На странице сервиса нажмите **"Logs"**
2. Найдите ошибки (ERROR, Exception, Traceback)
3. Скопируйте текст ошибки

Возможные ошибки:

#### Ошибка импорта utils
```
ImportError: cannot import name 'calculate_portfolio_stats' from 'utils'
```

**Решение**: Проверьте, что файл `utils.py` загружен на Render

#### Ошибка БД
```
sqlalchemy.exc.OperationalError: no such column: stock.logo_url
```

**Решение**: Запустите миграцию:
```
https://investikbotik.onrender.com/migrate
```

#### Ошибка шаблона
```
jinja2.exceptions.TemplateNotFound: index.html
```

**Решение**: Убедитесь, что папка `templates/` загружена в git

### Шаг 5: Альтернативное решение

Если ничего не помогает, откатитесь к предыдущей версии:

```bash
# Посмотрите историю коммитов
git log --oneline

# Откатитесь к последнему рабочему коммиту
git reset --hard <commit-hash>

# Принудительно запушьте
git push -f origin main
```

## Быстрая проверка локально

Запустите приложение локально, чтобы убедиться, что все работает:

```bash
# Активируйте виртуальное окружение (если есть)
# venv\Scripts\activate  (Windows)
# source venv/bin/activate  (Linux/Mac)

# Запустите приложение
python app.py

# Откройте браузер
http://localhost:5000
```

Если локально все работает, проблема точно на стороне Render.

## Дополнительная диагностика

### Проверка wsgi.py

Убедитесь, что `wsgi.py` правильно импортирует приложение:

```python
from app import create_app

app = create_app('production')
```

### Проверка render.yaml

Убедитесь, что в `render.yaml` правильно указан WSGI:

```yaml
services:
  - type: web
    name: investikbotik
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app
```

### Проверка requirements.txt

Убедитесь, что все зависимости установлены:

```txt
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
requests==2.32.3
gunicorn==23.0.0
python-telegram-bot==21.6
python-dotenv==1.0.1
```

## Контакты

Если проблема не решается, сохраните:
- Скриншот ошибки
- Логи из Render
- Вывод команды `git log --oneline -5`

---

© 2025 Polygalov V.
