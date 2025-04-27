import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from bot.handlers.main import register_main_handlers
from bot.handlers.payments import register_payment_handlers
from bot.handlers.admin import register_admin_handlers
from core.database import init_db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_main_handlers(dp)
    register_payment_handlers(dp)
    register_admin_handlers(dp)

    logging.info("Бот запущен.")
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())