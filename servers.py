# servers.py

servers_list = [
    {
        "name": "VPN Амстердам",
        "host": "31.59.185.71",              # IP-адрес VPN-сервера
        "port": 22,                         # SSH-порт
        "username": "vpnadmin",             # Пользователь для SSH-подключения
        "private_key_path": "/Users/culver01/.ssh/id_ed25519",  # Локальный путь к вашему SSH-ключу

        # Параметры Xray (REALITY)
        "protocol": "vless",
        "server_port": 443,                 # Порт, на котором работает Xray для VPN
        "uuid": "2c6c47b2-c59b-48be-9be3-d00f5d26676a",  # Значение по умолчанию; при выдаче конфига генерируется новый UUID
        "public_key": "5PdTds3eZ-Jciy9cSGYPI752LTypKpA52qutmqmVz2M",  # Публичный ключ для REALITY
        "sni": "cloudflare.com",            # SNI (например, cloudflare.com)
        "short_id": "",                     # Если используется, иначе оставьте пустым
        "fingerprint": "chrome",            # Fingerprint, имитирующий клиент Chrome
    }
]