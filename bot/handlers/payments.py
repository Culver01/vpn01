from aiogram import types, Dispatcher
from aiogram.types import LabeledPrice, ContentType
from core.database import update_subscription
from bot.keyboards.menus import build_main_menu_keyboard

SUBSCRIPTION_OPTIONS = {
    1: {"label": "1 месяц", "price": 2000},
    6: {"label": "6 месяцев", "price": 23940},
    12: {"label": "12 месяцев", "price": 35880},
}

PAYMENT_PROVIDER_TOKEN = "REPLACE_WITH_PROVIDER_TOKEN"

async def start_subscription(message: types.Message):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for months, option in SUBSCRIPTION_OPTIONS.items():
        btn = types.InlineKeyboardButton(
            text=f"{option['label']} — {option['price'] / 100:.2f}₽",
            callback_data=f"buy_{months}"
        )
        kb.add(btn)
    await message.answer("Выберите вариант подписки:", reply_markup=kb)

async def invoice_handler(callback_query: types.CallbackQuery):
    months = int(callback_query.data.split("_")[1])
    option = SUBSCRIPTION_OPTIONS[months]
    prices = [LabeledPrice(label=option["label"], amount=option["price"])]
    await callback_query.message.answer_invoice(
        title="Подписка VPN",
        description=f"Доступ к VPN на {months} мес.",
        payload=f"subscription_{months}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="vpn-sub",
    )

async def successful_payment_handler(message: types.Message):
    user_id = message.from_user.id
    months = 1  # fallback
    await update_subscription(user_id, months)
    kb = await build_main_menu_keyboard(user_id)
    await message.answer("✅ Подписка активирована!", reply_markup=kb)

def register_payment_handlers(dp: Dispatcher):
    dp.register_message_handler(start_subscription, commands=["subscribe"])
    dp.register_callback_query_handler(invoice_handler, lambda c: c.data.startswith("buy_"))
    dp.register_message_handler(successful_payment_handler, content_types=ContentType.SUCCESSFUL_PAYMENT)