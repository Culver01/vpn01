import paramiko

host = "31.59.185.71"  # Твой IP
username = "vpnadmin"
key_path = "/Users/culver01/.ssh/id_ed25519"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, key_filename=key_path)
    print("✅ SSH-подключение успешно!")
    client.close()
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
