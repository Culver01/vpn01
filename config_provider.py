import uuid
import asyncio
from config_cache_pg import get_active_config, save_config
from server_manager import add_vpn_user
from servers import servers_list


async def get_vpn_config(user_id: int) -> str:
    """
    Возвращает VPN-конфиг для пользователя.
    Если для данного user_id уже есть сохранённый конфиг в базе,
    он возвращается. Иначе генерируется новый конфиг, добавляется пользователь
    на VPN-сервер, сохраняется в базе и возвращается.

    :param user_id: Идентификатор пользователя Telegram.
    :return: Ссылка на VPN-конфиг.
    """
    # Проверяем, есть ли уже сохранённый конфиг для пользователя
    cached_config = await get_active_config(user_id)
    if cached_config:
        return cached_config

    # Если конфига нет, генерируем новый
    new_uuid = str(uuid.uuid4())
    client_email = f"user-{user_id}@example.com"
    server = servers_list[0]  # Берём первый сервер из списка. При необходимости адаптируйте логику выбора.

    # Запускаем добавление VPN-пользователя в отдельном потоке (если add_vpn_user синхронная)
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

    # Сохраняем новый конфиг в базе (PostgreSQL)
    await save_config(user_id, subscription_link)
    return subscription_link