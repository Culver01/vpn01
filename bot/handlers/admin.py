from aiogram import types, Dispatcher
from core.database import update_subscription, get_subscription
import os

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

def is_admin(user_id):
    return user_id == ADMIN_ID

async def admin_help(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "/give_sub user_id months — выдать подписку\n"
        "/del_sub user_id — удалить подписку\n"
        "/stats — показать число активных подписок"
    )

async def give_sub(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        _, uid, months = message.text.split()
        uid = int(uid)
        months = int(months)
        await update_subscription(uid, months)
        await message.answer(f"✅ Подписка на {months} мес выдана пользователю {uid}")
    except:
        await message.answer("⚠️ Неверный формат. Пример: /give_sub 123456 3")

async def del_sub(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        _, uid = message.text.split()
        uid = int(uid)
        await update_subscription(uid, 0)
        await message.answer(f"🗑 Подписка удалена у пользователя {uid}")
    except:
        await message.answer("⚠️ Неверный формат. Пример: /del_sub 123456")

async def show_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    from sqlalchemy import select, func
    from core.database import async_session, User
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(User.expires_at.isnot(None))
        )
        count = result.scalar()
        await message.answer(f"👥 Активных подписчиков: {count}")

def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_help, commands=["admin"])
    dp.register_message_handler(give_sub, commands=["give_sub"])
    dp.register_message_handler(del_sub, commands=["del_sub"])
    dp.register_message_handler(show_stats, commands=["stats"])