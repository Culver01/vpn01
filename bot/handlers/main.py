from aiogram import types, Dispatcher
from bot.keyboards.menus import build_main_menu_keyboard
from bot.handlers.payments import start_subscription

async def cmd_start(message: types.Message):
    kb = await build_main_menu_keyboard(message.from_user.id)
    await message.answer("👋 Привет! Я VPN-бот. Чем могу помочь?", reply_markup=kb)

async def handle_main_buttons(message: types.Message):
    text = message.text.lower()
    if "получить конфиг" in text:
        await message.answer("🚧 Генерация конфигурации временно недоступна.")
    elif "подписка" in text:
        await start_subscription(message)
    else:
        await message.answer("❓ Не понял команду. Используйте меню.")

def register_main_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=["start"])
    dp.register_message_handler(handle_main_buttons, content_types=types.ContentType.TEXT)