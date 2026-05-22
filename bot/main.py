# bot/main.py
"""Главный файл бота — запуск и планировщик уведомлений."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
from car_tracker.db import Database
from bot.handlers import start, set_filter, my_filter, stop_filter, handle_message
from bot.checker import check_new_deals
from telegram.ext import MessageHandler, filters

db = Database()

def main():
    """Запуск бота."""
    TOKEN = os.getenv("BOT_TOKEN", "8983260451:AAEeYDg4SnvqDFW9Vzdix7ibOMhB_WQZf04")
    
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("filter", set_filter))
    app.add_handler(CommandHandler("myfilter", my_filter))
    app.add_handler(CommandHandler("stopfilter", stop_filter))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Планировщик: проверка каждые 15 минут
    job_queue = app.job_queue
    job_queue.run_repeating(
        check_new_deals,
        interval=900,  # 15 минут в секундах
        first=10,      # Первый запуск через 10 секунд
    )
    
    print("🤖 Bot işə düşdü!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()