from flask import Flask, request, jsonify
import stripe  # Если у вас есть интеграция через Stripe, но здесь используется YooKassa, так что это пример для другой системы
from database import update_subscription
import os

app = Flask(__name__)

# Пример обработки вебхука для YooKassa – адаптируйте под документацию YooKassa
@app.route("/yookassa-webhook", methods=["POST"])
def yookassa_webhook():
    # Получите и проверьте подпись, затем извлеките информацию о платеже
    data = request.json
    # Предположим, что data содержит поле client_reference_id и информацию о продлении подписки
    user_id = int(data.get("client_reference_id", 0))
    # Определите, на сколько месяцев продлевается подписка
    months = data.get("months", 1)  # пример: 1 месяц
    # Обновите подписку в базе
    # (В реальном случае нужно дополнительно проверять событие, статус платежа и т.п.)
    import asyncio
    asyncio.run(update_subscription(user_id, months))
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(port=5000)
