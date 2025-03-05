import os
import asyncpg
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id BIGINT PRIMARY KEY,
                active BOOLEAN DEFAULT FALSE,
                end_date TIMESTAMP
            )
        """)

async def get_subscription(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT active, end_date FROM subscriptions WHERE user_id = $1", user_id)
        if row:
            return {"active": row["active"], "end_date": row["end_date"]}
        else:
            return {"active": False, "end_date": None}

async def update_subscription(user_id: int, months: int):
    now = datetime.now()
    sub = await get_subscription(user_id)
    if sub["active"] and sub["end_date"] and sub["end_date"] > now:
        new_end = sub["end_date"] + timedelta(days=30 * months)
    else:
        new_end = now + timedelta(days=30 * months)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO subscriptions (user_id, active, end_date)
            VALUES ($1, TRUE, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET active = TRUE, end_date = $2
        """, user_id, new_end)
    return new_end
