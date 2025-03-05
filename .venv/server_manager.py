import json
import paramiko


def update_server_config(server_ip, ssh_username, ssh_key_path, client_uuid, client_email):
    """
    Добавляет нового клиента (с client_uuid) в конфигурацию сервера Xray
    и перезагружает сервис.

    Параметры:
    - server_ip: IP-адрес VPN-сервера.
    - ssh_username: имя пользователя для SSH-подключения.
    - ssh_key_path: путь к приватному ключу для аутентификации.
    - client_uuid: сгенерированный UUID для нового клиента.
    - client_email: email или идентификатор клиента (для логирования в конфиге).

    В этом примере предполагается, что конфигурация сервера находится по пути:
    /etc/xray/config.json, а список клиентов – в
    config["inbounds"][0]["settings"]["clients"]
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username=ssh_username, key_filename=ssh_key_path)

        sftp = ssh.open_sftp()
        # Читаем конфигурационный файл
        remote_config_path = "/etc/xray/config.json"
        with sftp.file(remote_config_path, 'r') as remote_file:
            config_data = json.load(remote_file)

        # Создаем объект нового клиента
        new_client = {
            "id": client_uuid,
            "flow": "xtls-rprx-direct",
            "level": 0,
            "email": client_email
        }

        # Добавляем клиента в список (предполагаем, что клиенты находятся в первом inbound)
        config_data["inbounds"][0]["settings"]["clients"].append(new_client)

        # Записываем обновленную конфигурацию во временный файл
        temp_config_path = "/tmp/config.json"
        with sftp.file(temp_config_path, 'w') as temp_file:
            json.dump(config_data, temp_file, indent=4)

        sftp.close()

        # Перемещаем обновленный файл на место оригинального и перезагружаем Xray
        commands = [
            f"sudo mv {temp_config_path} {remote_config_path}",
            "sudo systemctl reload xray"
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode()
                raise Exception(f"Команда '{cmd}' завершилась с ошибкой: {error}")

        ssh.close()
        return True
    except Exception as e:
        print("Ошибка при обновлении конфигурации сервера:", e)
        return False
