from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

async def build_main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📥 Получить конфиг"))
    kb.add(KeyboardButton("💳 Подписка"))
    return kb