import asyncpg
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("token.env")
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_subscription(user_id: int) -> dict:
    """
    Возвращает информацию о подписке пользователя из базы данных.
    Если запись найдена, возвращает словарь с полями "active" и "end_date".
    Если записи нет, возвращает {"active": False, "end_date": None}.
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        row = await conn.fetchrow(
            "SELECT active, end_date FROM subscriptions WHERE user_id = $1", user_id
        )
        await conn.close()
        if row:
            return {"active": row["active"], "end_date": row["end_date"]}
        else:
            return {"active": False, "end_date": None}
    except Exception as e:
        print(f"Ошибка подключения к базе: {e}")
        return {"active": False, "end_date": None}

async def update_subscription(user_id: int, months: int) -> bool:
    """
    Выдает подписку пользователю, обновляя или создавая запись в базе.
    Подписка будет действительна в течение указанного количества месяцев.
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        months_str = str(months)
        await conn.execute(
            """
            INSERT INTO subscriptions (user_id, active, end_date)
            VALUES ($1, TRUE, now() + ($2 || ' months')::interval)
            ON CONFLICT (user_id) DO UPDATE 
                SET active = TRUE, end_date = now() + ($2 || ' months')::interval
            """,
            user_id, months_str
        )
        await conn.close()
        return True
    except Exception as e:
        print(f"Ошибка обновления подписки: {e}")
        return False

async def delete_subscription(user_id: int) -> bool:
    """
    Удаляет (отменяет) подписку пользователя, устанавливая active = FALSE и end_date = NULL.
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(
            """
            UPDATE subscriptions
            SET active = FALSE, end_date = NULL
            WHERE user_id = $1
            """,
            user_id
        )
        await conn.close()
        return True
    except Exception as e:
        print(f"Ошибка удаления подписки: {e}")
        return False

async def get_expired_subscriptions() -> list:
    """
    Возвращает список user_id подписок, у которых подписка активна, но end_date уже в прошлом.
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch("SELECT user_id FROM subscriptions WHERE active = TRUE AND end_date < now()")
        await conn.close()
        return [row["user_id"] for row in rows]
    except Exception as e:
        print(f"Ошибка получения истекших подписок: {e}")
        return []

# Для тестирования:
if __name__ == "__main__":
    async def test():
        print(await get_subscription(6136399442))
        print(await get_expired_subscriptions())
    asyncio.run(test())