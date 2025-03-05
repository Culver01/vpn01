import uuid
import base64


def generate_subscription_link(user_id, servers, subscription_active=True):
    if not subscription_active:
        return None
    links = []
    for server in servers:
        client_uuid = str(uuid.uuid4())
        protocol = server.get("protocol", "vless")
        address = server["address"]
        port = server["port"]
        security = server.get("security", "reality")
        query_params = f"encryption=none&type=tcp&security={security}&flow=xtls-rprx-direct"
        if "pbk" in server and server["pbk"]:
            query_params += f"&pbk={server['pbk']}"
        if "fingerprint" in server and server["fingerprint"]:
            query_params += f"&fp={server['fingerprint']}"
        if "sni" in server and server["sni"]:
            query_params += f"&sni={server['sni']}"
        if "short_id" in server and server["short_id"]:
            query_params += f"&sid={server['short_id']}"
        if "spx" in server and server["spx"]:
            query_params += f"&spx={server['spx']}"
        name = server.get("name", "Unnamed")
        link = f"{protocol}://{client_uuid}@{address}:{port}/?{query_params}#{name}"
        links.append(link)

    subscription_text = "\n".join(links)
    encoded = base64.urlsafe_b64encode(subscription_text.encode()).decode()
    return f"vless-sub://{encoded}"
