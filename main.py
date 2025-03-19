import os
import asyncio
import logging
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from yookassa import Configuration

from server_manager import add_vpn_user, remove_vpn_user
from servers import servers_list
from database import get_subscription, update_subscription, delete_subscription, get_expired_subscriptions
from payment import create_payment_session  # Функция создания платежной сессии
from config_provider import get_vpn_config, delete_vpn_config  # Функции для кэширования VPN-конфигов

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из token.env
load_dotenv("token.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Настройка YooKassa
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Используем словарь, где для каждого chat_id хранится список message_id эфемерных сообщений
ephemeral_messages = {}  # ключ: chat_id, значение: список message_id

async def add_ephemeral(chat_id: int, message_id: int):
    if chat_id not in ephemeral_messages:
        ephemeral_messages[chat_id] = []
    ephemeral_messages[chat_id].append(message_id)

async def delete_ephemeral(chat_id: int):
    if chat_id in ephemeral_messages:
        for msg_id in ephemeral_messages[chat_id]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception as e:
                logger.error(f"Ошибка при удалении эфемерного сообщения: {e}")
        del ephemeral_messages[chat_id]

# Главное меню
def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="VPN", callback_data="get_config"),
            InlineKeyboardButton(text="Подписка", callback_data="subscription"),
            InlineKeyboardButton(text="Прочее", callback_data="other")
        ]
    ])

# Клавиатура "Закрыть"
def close_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Закрыть", callback_data="close")]
    ])

# Клавиатура для подписки
def subscription_action_keyboard(button_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=button_text, callback_data="buy_subscription"),
            InlineKeyboardButton(text="Закрыть", callback_data="close")
        ]
    ])

# Клавиатура выбора тарифа подписки
def subscription_packages_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц (490 ₽)", callback_data="package_1")],
        [InlineKeyboardButton(text="6 месяцев (2394 ₽)", callback_data="package_6")],
        [InlineKeyboardButton(text="12 месяцев (3588 ₽)", callback_data="package_12")]
    ])

# Клавиатура для раздела "Прочее"
def other_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Инструкция", callback_data="instruction")],
        [InlineKeyboardButton(text="Реферальная система", callback_data="referral")],
        [InlineKeyboardButton(text="Поддержка", callback_data="support"),
         InlineKeyboardButton(text="Закрыть", callback_data="close")]
    ])

# Обработка команды /start – выводим главное меню
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await delete_ephemeral(message.chat.id)
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())

# Обработка кнопки "VPN"
@dp.callback_query(lambda call: call.data == "get_config")
async def process_get_config(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    try:
        # Получаем сохранённый конфиг или генерируем новый, если его нет
        cached_config = await get_vpn_config(call.from_user.id)
        if cached_config:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Новая ссылка", callback_data="new_config")]
            ])
            msg = await call.message.answer(
                "Вставьте эту ссылку в Hiddify:\n"
                f"<code>{cached_config}</code>\n"
                "(Нажмите на текст ссылки, чтобы её скопировать)",
                parse_mode="HTML",
                reply_markup=kb
            )
            await add_ephemeral(call.message.chat.id, msg.message_id)
        else:
            temp_msg = await call.message.answer("Готовим вашу персональную конфигурацию...")
            await add_ephemeral(call.message.chat.id, temp_msg.message_id)

            subscription_info = await get_subscription(call.from_user.id)
            if not subscription_info.get("active"):
                await delete_ephemeral(call.message.chat.id)
                sent = await call.message.answer(
                    "Подписка не активна. Для получения конфига нажмите кнопку 'Купить подписку'.",
                    reply_markup=subscription_action_keyboard("Купить подписку")
                )
                await add_ephemeral(call.message.chat.id, sent.message_id)
                return

            new_uuid = str(uuid.uuid4())
            client_email = f"user-{call.from_user.id}@example.com"
            server = servers_list[0]
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(None, add_vpn_user, server, new_uuid, client_email)
            await delete_ephemeral(call.message.chat.id)
            if not success:
                sent = await call.message.answer("Ошибка при добавлении VPN пользователя.", reply_markup=close_keyboard())
                await add_ephemeral(call.message.chat.id, sent.message_id)
                return

            subscription_link = (
                f"vless://{new_uuid}@{server['host']}:{server['server_port']}?"
                f"type=tcp&security=reality&pbk={server['public_key']}"
                f"&fp=chrome&sni={server['sni']}&sid=&spx=%2F&flow=xtls-rprx-vision"
                f"#{server['name']}"
            )
            await save_config(call.from_user.id, subscription_link)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Новая ссылка", callback_data="new_config")]
            ])
            sent = await call.message.answer(
                "Вставьте эту ссылку в Hiddify:\n"
                f"<code>{subscription_link}</code>\n"
                "(Нажмите на текст ссылки, чтобы её скопировать)",
                parse_mode="HTML",
                reply_markup=kb
            )
            await add_ephemeral(call.message.chat.id, sent.message_id)
    except Exception as e:
        await delete_ephemeral(call.message.chat.id)
        await call.message.answer(
            f"Ошибка при получении конфигурации: {e}",
            reply_markup=close_keyboard()
        )

# Обработка кнопки "Новая ссылка" – форсированная регенерация конфигурации
@dp.callback_query(lambda call: call.data == "new_config")
async def process_new_config(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    try:
        await delete_vpn_config(call.from_user.id)
        await process_get_config(call)
    except Exception as e:
        await call.message.answer(
            f"Ошибка при генерации новой конфигурации: {e}",
            reply_markup=close_keyboard()
        )

# Обработка кнопки "Подписка"
@dp.callback_query(lambda call: call.data == "subscription")
async def process_subscription(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    subscription_info = await get_subscription(call.from_user.id)
    if subscription_info.get("active") and subscription_info.get("end_date"):
        end_date = subscription_info.get("end_date")
        if isinstance(end_date, datetime):
            end_date_str = end_date.strftime("%d.%m.%Y")
        else:
            end_date_str = str(end_date)
        text = f"Подписка активна до {end_date_str}."
        button_text = "Продлить подписку"
    else:
        text = "Подписка не активна."
        button_text = "Купить подписку"
    sent = await call.message.answer(text, reply_markup=subscription_action_keyboard(button_text))
    await add_ephemeral(call.message.chat.id, sent.message_id)

# Обработка кнопки "Прочее"
@dp.callback_query(lambda call: call.data == "other")
async def process_other(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    sent = await call.message.answer("Прочее", reply_markup=other_keyboard())
    await add_ephemeral(call.message.chat.id, sent.message_id)

@dp.callback_query(lambda call: call.data in ["instruction", "referral", "support"])
async def process_other_options(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    sent = await call.message.answer("blank",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="Закрыть", callback_data="close")]
                                     ])
                                     )
    await add_ephemeral(call.message.chat.id, sent.message_id)
    await call.answer()

# Обработка кнопки "Купить подписку" (или "Продлить подписку")
@dp.callback_query(lambda call: call.data == "buy_subscription")
async def process_buy_subscription(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    sent = await call.message.answer("Выберите тариф подписки:", reply_markup=subscription_packages_keyboard())
    await add_ephemeral(call.message.chat.id, sent.message_id)
    try:
        await call.answer()
    except Exception as e:
        logger.error(f"Ошибка при ответе на callback: {e}")

# Обработка выбора тарифа подписки
@dp.callback_query(lambda call: call.data.startswith("package_"))
async def process_package_selection(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    package = call.data.split("_")[1]
    if package == "1":
        months = 1
        amount = 490.00
    elif package == "6":
        months = 6
        amount = 2394.00
    elif package == "12":
        months = 12
        amount = 3588.00
    else:
        await call.message.answer("Неверный тариф.")
        return

    return_url = "https://t.me/rogerscriptedbot?start=payment_success"
    cancel_url = "https://t.me/rogerscriptedbot?start=payment_cancel"
    description = f"Подписка на {months} месяц(ев)"

    loop = asyncio.get_running_loop()
    try:
        payment_url = await loop.run_in_executor(None, create_payment_session, call.from_user.id, months, return_url, cancel_url)
    except Exception as e:
        logger.error(f"Ошибка создания платежной сессии: {e}")
        payment_url = None

    if payment_url:
        sent = await call.message.answer(
            f"Для оплаты перейдите по ссылке:\n{payment_url}",
            reply_markup=close_keyboard()
        )
        await add_ephemeral(call.message.chat.id, sent.message_id)
    else:
        sent = await call.message.answer("Ошибка создания платежа. Попробуйте позже.", reply_markup=close_keyboard())
        await add_ephemeral(call.message.chat.id, sent.message_id)

    try:
        await call.answer()
    except Exception as e:
        logger.error(f"Ошибка при ответе на callback: {e}")

# Обработка кнопки "Закрыть"
@dp.callback_query(lambda call: call.data == "close")
async def process_close(call: types.CallbackQuery):
    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await delete_ephemeral(call.message.chat.id)
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")
    await call.answer()

# Админ-команды для управления подписками
@dp.message(Command("subadd"))
async def cmd_subadd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет прав для выполнения этой команды.")
        return
    parts = message.text.split()
    if len(parts) == 2:
        try:
            target_id = int(parts[1])
            months = 1
        except Exception as e:
            await message.answer("Неверные аргументы. Используйте число для userid.")
            return
    elif len(parts) == 3:
        try:
            target_id = int(parts[1])
            months = int(parts[2])
        except Exception as e:
            await message.answer("Неверные аргументы. Используйте числа для userid и months.")
            return
    else:
        await message.answer("Использование: /subadd [userid] [months]. Если months не указан, по умолчанию 1 месяц.")
        return
    success = await update_subscription(target_id, months)
    if success:
        await message.answer(f"Подписка выдана пользователю {target_id} на {months} месяц(ев).")
    else:
        await message.answer("Ошибка при выдаче подписки.")

@dp.message(Command("subdel"))
async def cmd_subdel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет прав для выполнения этой команды.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /subdel [userid]")
        return
    try:
        target_id = int(parts[1])
    except Exception as e:
        await message.answer("Неверный аргумент. Используйте число для userid.")
        return
    success = await delete_subscription(target_id)
    if success:
        await message.answer(f"Подписка удалена у пользователя {target_id}.")
    else:
        await message.answer("Ошибка при удалении подписки.")

# Фоновая задача для проверки истекших подписок (каждые 12 часов)
async def check_expired_subscriptions():
    while True:
        try:
            expired_users = await get_expired_subscriptions()
            for user_id in expired_users:
                client_email = f"user-{user_id}@example.com"
                server = servers_list[0]
                result = await asyncio.get_running_loop().run_in_executor(None, remove_vpn_user, server, client_email)
                if result:
                    logger.info(f"Подписка истекла: VPN-пользователь для {user_id} удален.")
                else:
                    logger.error(f"Ошибка удаления VPN-пользователя для {user_id}.")
                await delete_subscription(user_id)
        except Exception as e:
            logger.error(f"Ошибка проверки истекших подписок: {e}")
        await asyncio.sleep(43200)  # 12 часов

async def main():
    from config_cache_pg import init_db
    await init_db()
    asyncio.create_task(check_expired_subscriptions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
