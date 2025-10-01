"""
Простой Telegram бот для InvestBot
Для работы требуется установить: pip install python-telegram-bot

Инструкция по настройке:
1. Создайте бота через @BotFather
2. Получите токен бота
3. Замените YOUR_BOT_TOKEN на ваш токен
4. Запустите скрипт: python telegram_bot.py
"""

import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем настройки из переменных окружения
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEB_APP_URL = os.environ.get('WEB_APP_URL', 'http://localhost:5000')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Создаем кнопку для открытия веб-приложения
    keyboard = [
        [InlineKeyboardButton(
            "📊 Открыть InvestBot", 
            web_app=WebAppInfo(url=WEB_APP_URL)
        )],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🤖 Добро пожаловать в InvestBot, {user.first_name}!

📈 InvestBot - это ваш персональный помощник для отслеживания инвестиций в российские акции.

✨ Возможности:
• 📊 Отслеживание портфеля акций
• 💰 Управление несколькими счетами  
• 📈 Актуальные котировки
• 💹 Расчет прибыли и убытков
• 📋 История транзакций

Нажмите кнопку ниже, чтобы открыть приложение:
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Справка по командам бота"""
    help_text = """
📖 Доступные команды:

/start - Начать работу с ботом
/app или /webapp - Открыть приложение (с кнопкой Web App)
/portfolio - Быстрый просмотр портфеля
/help - Справка по командам

⚠️ ВАЖНО для авторизации:
Используйте команду /app или кнопку "📊 Открыть InvestBot".
НЕ открывайте через обычную ссылку!

💡 Если не работает - попробуйте демо-режим
    """
    
    await update.message.reply_text(help_text)

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Быстрый просмотр портфеля"""
    user = update.effective_user
    
    # В реальном приложении здесь был бы запрос к базе данных
    # Пока что отправляем заглушку
    
    keyboard = [
        [InlineKeyboardButton(
            "📊 Подробный просмотр", 
            web_app=WebAppInfo(url=WEB_APP_URL)
        )]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    portfolio_text = """
📊 Ваш портфель:

💰 Свободные средства: 25,000 ₽
📈 Инвестировано: 50,000 ₽
💹 Текущая стоимость: 52,500 ₽
📊 Прибыль: +2,500 ₽ (+5.0%)

Для подробной информации откройте приложение:
    """
    
    await update.message.reply_text(
        portfolio_text,
        reply_markup=reply_markup
    )

async def webapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет кнопку для открытия Web App"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton(
            "🚀 Открыть приложение", 
            web_app=WebAppInfo(url=WEB_APP_URL)
        )],
        [InlineKeyboardButton(
            "🧪 Тест (минимальный)", 
            web_app=WebAppInfo(url=f"{WEB_APP_URL}/test_telegram")
        )]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"🚀 Основное приложение - полный функционал\n"
        f"🧪 Тест - минимальная проверка Telegram Web App\n\n"
        f"⚠️ Важно: используйте кнопки Web App выше!",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await help_command(update, context)

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Ошибка: Необходимо указать токен бота!")
        print("1. Создайте бота через @BotFather")
        print("2. Создайте файл .env и укажите TELEGRAM_BOT_TOKEN=ваш_токен")
        print("3. Или установите переменную окружения TELEGRAM_BOT_TOKEN")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("app", webapp_command))
    application.add_handler(CommandHandler("webapp", webapp_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    print("🤖 InvestBot запущен!")
    print("Для остановки нажмите Ctrl+C")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
