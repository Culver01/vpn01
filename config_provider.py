import uuid
import asyncio
from config_cache_pg import get_active_config, save_config, pool, init_db
from server_manager import add_vpn_user
from servers import servers_list

async def ensure_pool():
    """
    Проверяет, инициализирован ли пул подключений.
    Если нет, инициализирует его.
    """
    from config_cache_pg import pool, init_db
    if pool is None:
        await init_db()

async def get_vpn_config(user_id: int) -> str:
    """
    Возвращает VPN-конфиг для пользователя.
    Если для данного user_id уже есть сохранённый конфиг, он возвращается.
    Иначе генерируется новый конфиг, добавляется пользователь на VPN-сервер,
    сохраняется в базе и возвращается.
    """
    await ensure_pool()
    cached = await get_active_config(user_id)
    if cached:
        return cached

    new_uuid = str(uuid.uuid4())
    client_email = f"user-{user_id}@example.com"
    server = servers_list[0]  # Выбираем первый сервер; можно доработать логику выбора

    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, add_vpn_user, server, new_uuid, client_email)
    if not success:
        raise Exception("Ошибка при добавлении VPN пользователя")

    subscription_link = (
        f"vless://{new_uuid}@{server['host']}:{server['server_port']}?"
        f"type=tcp&security=reality&pbk={server['public_key']}"
        f"&fp=chrome&sni={server['sni']}&sid=&spx=%2F&flow=xtls-rprx-vision"
        f"#{server['name']}"
    )
    await save_config(user_id, subscription_link)
    return subscription_link

async def delete_vpn_config(user_id: int):
    """
    Удаляет сохранённую VPN-конфигурацию для данного пользователя из базы данных.
    Это используется для принудительной регенерации новой конфигурации.
    """
    await ensure_pool()
    from config_cache_pg import pool
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM public.vpn_configs WHERE user_id = $1", user_id)
