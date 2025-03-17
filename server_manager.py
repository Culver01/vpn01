# server_manager.py
import paramiko
import json

def add_vpn_user(server_info: dict, new_uuid: str, client_email: str) -> bool:
    """
    Добавляет нового VPN-пользователя в конфигурацию Xray через SSH.
    Если запись с таким email уже существует, она удаляется.
    Затем добавляется новый клиент, и Xray перезапускается.
    """
    try:
        print(f"🔍 Подключаемся к серверу {server_info['host']} с пользователем {server_info['username']}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server_info["host"],
            port=server_info["port"],
            username=server_info["username"],
            key_filename=server_info["private_key_path"],
            timeout=10
        )
        print("✅ SSH-подключение установлено!")
        sftp = ssh.open_sftp()
        remote_config_path = "/usr/local/etc/xray/config.json"

        with sftp.open(remote_config_path, "r") as config_file:
            config_data = json.load(config_file)
        print("📄 Загружена конфигурация Xray с сервера.")

        # Ищем inbound с протоколом "vless"
        target_inbound = None
        if "inbounds" in config_data:
            for inbound in config_data["inbounds"]:
                if inbound.get("protocol") == "vless":
                    target_inbound = inbound
                    break
        else:
            if config_data.get("protocol") == "vless":
                target_inbound = config_data

        if target_inbound is None:
            print("❌ Не найден inbound с протоколом 'vless'!")
            ssh.close()
            return False

        if "settings" not in target_inbound or "clients" not in target_inbound["settings"]:
            print("❌ Неверная структура конфига: отсутствуют 'settings/clients'!")
            ssh.close()
            return False

        clients = target_inbound["settings"]["clients"]

        # Удаляем запись с таким же email, если она существует
        new_clients = [client for client in clients if client.get("email") != client_email]
        if len(clients) != len(new_clients):
            print(f"♻ Удалены существующие записи для {client_email}.")
        target_inbound["settings"]["clients"] = new_clients

        # Добавляем нового пользователя
        new_client = {
            "id": new_uuid,
            "email": client_email,
            "flow": "xtls-rprx-vision"  # Используйте значение, соответствующее настройкам
        }
        target_inbound["settings"]["clients"].append(new_client)
        print(f"✅ Добавлен новый VPN-пользователь: {new_client}")

        # Сохраняем обновленную конфигурацию во временный файл
        temp_config_path = "/tmp/config_temp.json"
        with sftp.open(temp_config_path, "w") as temp_file:
            json.dump(config_data, temp_file, indent=4)
        print("💾 Обновленная конфигурация сохранена во временном файле.")

        sftp.close()

        # Перемещаем временный файл на место оригинала и перезапускаем Xray
        commands = [
            f"sudo mv {temp_config_path} {remote_config_path}",
            "sudo systemctl restart xray"
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error_msg = stderr.read().decode()
                print(f"❌ Команда '{cmd}' завершилась с ошибкой: {error_msg}")
                ssh.close()
                return False

        ssh.close()
        print("🚀 Xray успешно перезапущен!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при добавлении VPN-пользователя: {e}")
        return False


def remove_vpn_user(server_info: dict, client_email: str) -> bool:
    """
    Удаляет VPN-пользователя из конфигурации Xray через SSH по email.
    После удаления конфигурация сохраняется, и Xray перезапускается.
    """
    try:
        print(f"🔍 Подключаемся к серверу {server_info['host']} для удаления пользователя {client_email}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server_info["host"],
            port=server_info["port"],
            username=server_info["username"],
            key_filename=server_info["private_key_path"],
            timeout=10
        )
        print("✅ SSH-подключение установлено!")
        sftp = ssh.open_sftp()
        remote_config_path = "/usr/local/etc/xray/config.json"

        with sftp.open(remote_config_path, "r") as config_file:
            config_data = json.load(config_file)
        print("📄 Загружена конфигурация Xray с сервера.")

        # Ищем inbound с протоколом "vless"
        target_inbound = None
        if "inbounds" in config_data:
            for inbound in config_data["inbounds"]:
                if inbound.get("protocol") == "vless":
                    target_inbound = inbound
                    break
        else:
            if config_data.get("protocol") == "vless":
                target_inbound = config_data

        if target_inbound is None:
            print("❌ Не найден inbound с протоколом 'vless'!")
            ssh.close()
            return False

        if "settings" not in target_inbound or "clients" not in target_inbound["settings"]:
            print("❌ Неверная структура конфига: отсутствуют 'settings/clients'!")
            ssh.close()
            return False

        clients = target_inbound["settings"]["clients"]
        new_clients = [client for client in clients if client.get("email") != client_email]
        if len(clients) == len(new_clients):
            print(f"ℹ Клиент с email {client_email} не найден в конфигурации.")
        else:
            print(f"✅ Удалена запись для клиента с email {client_email}.")
        target_inbound["settings"]["clients"] = new_clients

        # Сохраняем обновленную конфигурацию во временный файл
        temp_config_path = "/tmp/config_temp.json"
        with sftp.open(temp_config_path, "w") as temp_file:
            json.dump(config_data, temp_file, indent=4)
        print("💾 Обновленная конфигурация сохранена во временном файле.")

        sftp.close()

        commands = [
            f"sudo mv {temp_config_path} {remote_config_path}",
            "sudo systemctl restart xray"
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error_msg = stderr.read().decode()
                print(f"❌ Команда '{cmd}' завершилась с ошибкой: {error_msg}")
                ssh.close()
                return False

        ssh.close()
        print("🚀 Xray успешно перезапущен!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при удалении VPN-пользователя: {e}")
        return False