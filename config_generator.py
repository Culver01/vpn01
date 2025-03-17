import uuid


def generate_subscription_link(user_id: int, servers: list, client_uuid_map: dict = None,
                               subscription_active: bool = True) -> str:
    """
    Генерирует подписочную ссылку для VPN клиента в формате обычного текста.

    Для каждого сервера создается отдельная ссылка в формате VLESS:
      vless://<client_uuid>@<server_ip>:<port>/?type=tcp&security=reality&pbk=<public_key>&fp=<fingerprint>&sni=<sni>&sid=<short_id>&spx=%2F#<remark>

    Итоговая подписочная ссылка представляет собой набор отдельных ссылок, разделенных переводами строки.
    Если subscription_active = False, возвращается None.
    """
    if not subscription_active:
        return None

    links = []
    for server in servers:
        protocol = server.get("protocol", "vless")
        address = server.get("address")
        port = server.get("port")
        security = server.get("security", "reality")
        # Формируем параметры запроса
        query_params = f"encryption=none&type=tcp&security={security}&flow=xtls-rprx-direct"
        if server.get("pbk"):
            query_params += f"&pbk={server['pbk']}"
        if server.get("fingerprint"):
            query_params += f"&fp={server['fingerprint']}"
        if server.get("sni"):
            query_params += f"&sni={server['sni']}"
        if server.get("short_id"):
            query_params += f"&sid={server['short_id']}"
        if server.get("spx"):
            query_params += f"&spx={server['spx']}"
        remark = server.get("name", "Unnamed")
        # Если для сервера уже сгенерирован UUID, используем его, иначе генерируем новый
        if client_uuid_map and server.get("name") in client_uuid_map:
            client_uuid = client_uuid_map[server.get("name")]
        else:
            client_uuid = str(uuid.uuid4())
        link = f"{protocol}://{client_uuid}@{address}:{port}/?{query_params}#{remark}"
        links.append(link)

    subscription_text = "\n".join(links)
    return subscription_text
