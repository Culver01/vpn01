import os
import asyncio
import logging
import uuid
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from dotenv import load_dotenv

# Импортируем наши модули
from config_generator import generate_subscription_link
from servers import servers_list
from payment import create_payment_session
from database import get_subscription

load_dotenv("token.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Получить конфиг", callback_data="get_config"),
            InlineKeyboardButton(text="Подписка", callback_data="subscription"),
            InlineKeyboardButton(text="Прочее", callback_data="other")
        ]
    ])

def done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Закрыть", callback_data="done")]
    ])

def subscription_options_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 месяц - 379₽", callback_data="buy_1"),
            InlineKeyboardButton(text="3 месяца - 999₽", callback_data="buy_3"),
            InlineKeyboardButton(text="12 месяцев - 3599₽", callback_data="buy_12")
        ],
        [InlineKeyboardButton(text="Закрыть", callback_data="done")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Пожалуйста, поделитесь номером телефона для подтверждения личности:", reply_markup=kb)

@dp.message(lambda message: message.contact is not None)
async def process_contact(message: types.Message):
    phone = message.contact.phone_number
    await message.answer(f"Спасибо, ваш номер {phone} подтвержден!", reply_markup=ReplyKeyboardRemove())
    await message.answer("Теперь вы можете использовать бота:", reply_markup=main_menu_keyboard())

@dp.callback_query(lambda call: call.data == "subscription")
async def process_subscription(call: types.CallbackQuery):
    await call.answer()
    sub_info = await get_subscription(call.from_user.id)
    if sub_info["active"]:
        text = f"Подписка активна до {sub_info['end_date']}"
        button_text = "Продлить подписку"
    else:
        text = "Подписка неактивна"
        button_text = "Купить подписку"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=button_text, callback_data="select_plan"),
            InlineKeyboardButton(text="Закрыть", callback_data="done")
        ]
    ])
    await bot.send_message(call.from_user.id, text, reply_markup=keyboard)

@dp.callback_query(lambda call: call.data == "select_plan")
async def process_select_plan(call: types.CallbackQuery):
    await call.answer()
    await bot.send_message(call.from_user.id,
                           "Выберите план подписки:",
                           reply_markup=subscription_options_keyboard())

@dp.callback_query(lambda call: call.data.startswith("buy_"))
async def process_buy_subscription(call: types.CallbackQuery):
    await call.answer()
    data = call.data  # "buy_1", "buy_3" или "buy_12"
    months = int(data.split("_")[1])
    user_id = call.from_user.id
    return_url = "https://your-domain.com/payment_success"  # Укажите реальный return URL
    try:
        payment_url = create_payment_session(user_id, months, return_url)
    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при создании платежной сессии: {str(e)}", reply_markup=done_keyboard())
        return
    await call.message.delete()
    await bot.send_message(user_id,
                           f"Для оплаты подписки на {months} месяц(ев) перейдите по ссылке:\n{payment_url}",
                           reply_markup=done_keyboard())

@dp.callback_query(lambda call: call.data == "get_config")
async def process_get_config(call: types.CallbackQuery):
    await call.answer()
    sub_info = await get_subscription(call.from_user.id)
    if sub_info["active"]:
        sub_link = generate_subscription_link(call.from_user.id, servers_list, subscription_active=True)
        await bot.send_message(
            call.from_user.id,
            f"Ваша подписочная ссылка:\n<code>{sub_link}</code>\n\nВставьте эту ссылку в приложение (например, v2rayTUN или Hiddify).",
            parse_mode="HTML",
            reply_markup=done_keyboard()
        )
    else:
        await bot.send_message(
            call.from_user.id,
            "Ваша подписка неактивна. Пожалуйста, оформите подписку, чтобы получить конфиг.",
            reply_markup=done_keyboard()
        )

@dp.callback_query(lambda call: call.data == "other")
async def process_other(call: types.CallbackQuery):
    await call.answer()
    await bot.send_message(call.from_user.id,
                           "Прочие функции: Здесь можно разместить дополнительные возможности.",
                           reply_markup=done_keyboard())

@dp.callback_query(lambda call: call.data == "done")
async def process_done(call: types.CallbackQuery):
    await call.message.delete()
    await call.answer("Сообщение удалено.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    from database import init_db
    asyncio.run(init_db())
    asyncio.run(main())
