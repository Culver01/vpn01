import os
import asyncpg
from datetime import datetime

# Глобальный пул подключений
pool = None

async def init_db():
    """
    Инициализирует пул подключений к PostgreSQL, используя DATABASE_URL,
    и создаёт таблицу public.vpn_configs, если она ещё не существует.
    """
    global pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL не задан в переменных окружения.")
    pool = await asyncpg.create_pool(database_url)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS public.vpn_configs (
                user_id BIGINT PRIMARY KEY,
                subscription_link TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

async def get_active_config(user_id: int) -> str:
    """
    Возвращает сохранённую ссылку (subscription_link) для данного user_id, если она существует.
    """
    global pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT subscription_link FROM public.vpn_configs WHERE user_id = $1", user_id)
    if row:
        return row["subscription_link"]
    return None

async def save_config(user_id: int, subscription_link: str):
    """
    Сохраняет или обновляет VPN-конфигурацию для пользователя.
    """
    global pool
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO public.vpn_configs (user_id, subscription_link, created_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET subscription_link = EXCLUDED.subscription_link, created_at = NOW();
        """, user_id, subscription_link)