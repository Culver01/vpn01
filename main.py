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
from payment import create_payment_session
from config_provider import get_vpn_config, delete_vpn_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv("token.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения списка ID эфемерных сообщений для каждого чата
ephemeral_messages = {}  # key: chat_id, value: list of message_id

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
                if "message to delete not found" in str(e):
                    continue
                logger.error(f"Ошибка при удалении эфемерного сообщения: {e}")
        del ephemeral_messages[chat_id]

def get_welcome_menu() -> (str, InlineKeyboardMarkup):
    """Возвращает текст и клавиатуру приветственного меню для пользователей без подписки."""
    text = (
        "Привет. Это NEOR.\n\n"
        "Здесь вы получаете доступ к защищённым VPN-серверам.\n"
        "Без рекламы, логов и лишних слов.\n\n"
        "Подключение занимает меньше минуты.\n"
        "Нужен только Hiddify и наш конфиг."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Что это такое", callback_data="info")],
        [InlineKeyboardButton(text="Подключиться", callback_data="buy_subscription")]
    ])
    return text, keyboard

def get_info_menu() -> (str, InlineKeyboardMarkup):
    """Возвращает базовое информационное меню."""
    text = (
        "NEOR — это VPN-сервера, к которым вы подключаетесь через Hiddify.\n\n"
        "Мы не используем учётки, не собираем данные и не показываем рекламу.\n"
        "Вы просто получаете конфиг. И подключаетесь.\n\n"
        "Надёжно. Тихо. Быстро."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подробнее", callback_data="info_detailed"),
         InlineKeyboardButton(text="Тарифы", callback_data="buy_subscription")]
    ])
    return text, keyboard

def get_info_detailed_menu() -> (str, InlineKeyboardMarkup):
    """Возвращает подробное информационное меню с кнопкой [Назад], возвращающей к базовому информационному меню."""
    text = (
        "NEOR это:\n"
        "— Серверы в Европе\n"
        "— Высокая скорость и стабильность\n"
        "— Современные технологии обхода блокировок\n"
        "— Подключение до 8 устройств\n"
        "— Неограниченный трафик\n"
        "— Без трекеров и логов"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="info"),
         InlineKeyboardButton(text="Тарифы", callback_data="buy_subscription")]
    ])
    return text, keyboard

# Асинхронная функция для динамического формирования главного меню.
# Если у пользователя нет активной подписки, кнопка "Подписка" заменяется на "Активация".
async def build_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    subscription_info = await get_subscription(user_id)
    if subscription_info.get("active"):
        subscription_button = InlineKeyboardButton(text="Подписка", callback_data="subscription")
    else:
        subscription_button = InlineKeyboardButton(text="Подключить", callback_data="activation")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="VPN", callback_data="get_config"),
         subscription_button,
         InlineKeyboardButton(text="Прочее", callback_data="other")]
    ])

def close_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Закрыть", callback_data="close")]
    ])

def subscription_action_keyboard(button_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, callback_data="buy_subscription"),
         InlineKeyboardButton(text="Закрыть", callback_data="close")]
    ])

# Обновлённая клавиатура для выбора тарифного плана подписки.
# Изменены тексты кнопок на:
# "1 месяц (490 руб/мес)", "6 месяцев (399 руб/мес)", "12 месяцев (299 руб/мес)"
def subscription_packages_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц (20 руб/мес)", callback_data="package_1")],
        [InlineKeyboardButton(text="6 месяцев (399 руб/мес)", callback_data="package_6")],
        [InlineKeyboardButton(text="12 месяцев (299 руб/мес)", callback_data="package_12")]
    ])

def other_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Инструкция", callback_data="instruction")],
        [InlineKeyboardButton(text="Реферальная система", callback_data="referral")],
        [InlineKeyboardButton(text="Поддержка", callback_data="support"),
         InlineKeyboardButton(text="Закрыть", callback_data="close")]
    ])

# Клавиатура для окна VPN при отсутствии подписки.
# Содержит кнопки "Планы" и "Преимущества" (без кнопки "назад")
def vpn_no_subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Тарифы", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="Почему стоит выбрать нас?", callback_data="advantages")]
    ])

# Клавиатура с единственной кнопкой "назад", которая возвращает в VPN-окно
def vpn_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="назад", callback_data="back_to_vpn")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await delete_ephemeral(message.chat.id)
    subscription_info = await get_subscription(message.from_user.id)
    if subscription_info and subscription_info.get("active"):
        kb = await build_main_menu_keyboard(message.from_user.id)
        await message.answer("Главное меню:", reply_markup=kb)
    else:
        text, keyboard = get_welcome_menu()
        await message.answer(text, reply_markup=keyboard)

@dp.callback_query(lambda call: call.data == "info")
async def process_info(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    text, keyboard = get_info_menu()
    sent = await call.message.answer(text, reply_markup=keyboard)
    await add_ephemeral(call.message.chat.id, sent.message_id)
    await call.answer()

@dp.callback_query(lambda call: call.data == "info_detailed")
async def process_info_detailed(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    text, keyboard = get_info_detailed_menu()
    sent = await call.message.answer(text, reply_markup=keyboard)
    await add_ephemeral(call.message.chat.id, sent.message_id)
    await call.answer()

@dp.callback_query(lambda call: call.data == "activation")
async def process_activation(call: types.CallbackQuery):
    """
    Обработчик кнопки "Активация".
    При нажатии сразу выводит меню выбора тарифного плана с текстом "Выберите план".
    """
    await delete_ephemeral(call.message.chat.id)
    sent = await call.message.answer("Выберите план", reply_markup=subscription_packages_keyboard())
    await add_ephemeral(call.message.chat.id, sent.message_id)
    await call.answer()

@dp.callback_query(lambda call: call.data == "get_config")
async def process_get_config(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    try:
        # Проверяем статус подписки
        subscription_info = await get_subscription(call.from_user.id)
        # Если подписка не активна, выводим подробное сообщение о VPN с обновлённой клавиатурой
        if not subscription_info.get("active"):
            vpn_text = (
                "VPN — это простой способ обходить любые блокировки в интернете и свободно открывать заблокированные сайты и приложения, "
                "которые стали недоступны в России. Он защищает вас от слежки, скрывая ваше реальное местоположение и личные данные. "
                "С VPN вы снова получаете доступ к привычным сервисам, соцсетям и новостным сайтам, не боясь, что за вами следят или контролируют ваш трафик.\n\n"
                "Подключите VPN сейчас и верните себе свободу и безопасность в интернете!"
            )
            sent = await call.message.answer(vpn_text, reply_markup=vpn_no_subscription_keyboard())
            await add_ephemeral(call.message.chat.id, sent.message_id)
            return

        # Если подписка активна, продолжаем обычную обработку запроса
        cached_config = await get_vpn_config(call.from_user.id)
        if cached_config:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Новая ссылка", callback_data="new_config_confirm"),
                 InlineKeyboardButton(text="Закрыть", callback_data="close")]
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
                [InlineKeyboardButton(text="Новая ссылка", callback_data="new_config_confirm"),
                 InlineKeyboardButton(text="Закрыть", callback_data="close")]
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

@dp.callback_query(lambda call: call.data == "advantages")
async def process_advantages(call: types.CallbackQuery):
    """
    Обработчик кнопки "Преимущества".
    Выводит сообщение с информацией о преимуществах VPN и клавиатуру с кнопкой "назад",
    которая возвращает пользователя в предыдущее VPN-окно.
    """
    await delete_ephemeral(call.message.chat.id)
    sent = await call.message.answer("Тут будут преимущества", reply_markup=vpn_back_keyboard())
    await add_ephemeral(call.message.chat.id, sent.message_id)
    await call.answer()

@dp.callback_query(lambda call: call.data == "back_to_vpn")
async def process_back_to_vpn(call: types.CallbackQuery):
    """
    Обработчик кнопки "назад" в меню преимуществ.
    Возвращает пользователя в окно с информацией о VPN.
    """
    await delete_ephemeral(call.message.chat.id)
    vpn_text = (
        "VPN — это простой способ обходить любые блокировки в интернете и свободно открывать заблокированные сайты и приложения, "
        "которые стали недоступны в России. Он защищает вас от слежки, скрывая ваше реальное местоположение и личные данные. "
        "С VPN вы снова получаете доступ к привычным сервисам, соцсетям и новостным сайтам, не боясь, что за вами следят или контролируют ваш трафик.\n\n"
        "Подключите VPN сейчас и верните себе свободу и безопасность в интернете!"
    )
    sent = await call.message.answer(vpn_text, reply_markup=vpn_no_subscription_keyboard())
    await add_ephemeral(call.message.chat.id, sent.message_id)
    await call.answer()

@dp.callback_query(lambda call: call.data == "new_config_confirm")
async def confirm_prompt(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="confirm_new_config"),
         InlineKeyboardButton(text="Назад", callback_data="cancel_new_config")]
    ])
    msg = await call.message.answer(
        "После генерации новой ссылки предыдущая ссылка перестанет работать. Вы уверены, что хотите создать новую ссылку?",
        reply_markup=kb
    )
    await add_ephemeral(call.message.chat.id, msg.message_id)
    await call.answer()

@dp.callback_query(lambda call: call.data == "confirm_new_config")
async def process_confirm_new_config(call: types.CallbackQuery):
    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения подтверждения: {e}")
    msg = await call.message.answer("Готовим вашу персональную ссылку...")
    await add_ephemeral(call.message.chat.id, msg.message_id)
    try:
        await delete_vpn_config(call.from_user.id)
        new_config = await get_vpn_config(call.from_user.id)
        new_text = (
            "Вставьте эту ссылку в Hiddify:\n"
            f"<code>{new_config}</code>\n"
            "(Нажмите на текст ссылки, чтобы её скопировать)"
        )
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=msg.message_id,
            text=new_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Новая ссылка", callback_data="new_config_confirm"),
                 InlineKeyboardButton(text="Закрыть", callback_data="close")]
            ])
        )
    except Exception as e:
        await call.message.answer(
            f"Ошибка при генерации новой конфигурации: {e}",
            reply_markup=close_keyboard()
        )
    await call.answer()

@dp.callback_query(lambda call: call.data == "cancel_new_config")
async def process_cancel_new_config(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    await process_get_config(call)
    await call.answer()

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

@dp.callback_query(lambda call: call.data == "buy_subscription")
async def process_buy_subscription(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    sent = await call.message.answer("Выберите план", reply_markup=subscription_packages_keyboard())
    await add_ephemeral(call.message.chat.id, sent.message_id)
    try:
        await call.answer()
    except Exception as e:
        logger.error(f"Ошибка при ответе на callback: {e}")

@dp.callback_query(lambda call: call.data.startswith("package_"))
async def process_package_selection(call: types.CallbackQuery):
    await delete_ephemeral(call.message.chat.id)
    package = call.data.split("_")[1]
    if package == "1":
        months = 1
        amount = 20.00
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

@dp.callback_query(lambda call: call.data == "close")
async def process_close(call: types.CallbackQuery):
    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await delete_ephemeral(call.message.chat.id)
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")
    await call.answer()

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
        try:
            await delete_ephemeral(target_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении эфемерного меню для пользователя {target_id}: {e}")
        kb = await build_main_menu_keyboard(target_id)
        try:
            await bot.send_message(target_id, "Ваше главное меню обновлено:", reply_markup=kb)
        except Exception as e:
            logger.error(f"Ошибка при отправке обновленного главного меню для пользователя {target_id}: {e}")
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
        try:
            await delete_ephemeral(target_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении эфемерного меню для пользователя {target_id}: {e}")
        kb = await build_main_menu_keyboard(target_id)
        try:
            await bot.send_message(target_id, "Ваше главное меню обновлено:", reply_markup=kb)
        except Exception as e:
            logger.error(f"Ошибка при отправке обновленного главного меню для пользователя {target_id}: {e}")
    else:
        await message.answer("Ошибка при удалении подписки.")

@dp.message(Command("clearhistory"))
async def cmd_clearhistory(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет прав для выполнения этой команды.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /clearhistory [userid]")
        return
    try:
        target_id = int(parts[1])
    except Exception as e:
        await message.answer("Неверный аргумент. Используйте число для userid.")
        return
    # Удаляем данные подписки пользователя
    await delete_subscription(target_id)
    # Удаляем VPN конфигурацию, если она существует
    try:
        await delete_vpn_config(target_id)
    except Exception as e:
        logger.error(f"Ошибка при удалении конфигурации VPN для пользователя {target_id}: {e}")
    # Удаляем эфемерные сообщения, если есть
    try:
        await delete_ephemeral(target_id)
    except Exception as e:
        logger.error(f"Ошибка при удалении эфемерного меню для пользователя {target_id}: {e}")
    await message.answer(f"История пользователя {target_id} очищена.")

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
