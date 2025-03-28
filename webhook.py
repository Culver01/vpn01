from flask import Flask, request, jsonify
from database import update_subscription
import os

app = Flask(__name__)

# Пример обработки вебхука для YooKassa – адаптируйте под документацию YooKassa
@app.route("/yookassa-webhook", methods=["POST"])
def yookassa_webhook():
    data = request.json
    # Обрабатываем только успешные платежи
    if data.get("event") != "payment.succeeded":
        return jsonify({"status": "ignored"}), 200

    # Извлекаем объект платежа
    payment_object = data.get("object", {})

    try:
        user_id = int(payment_object.get("client_reference_id", 0))
        metadata = payment_object.get("metadata", {})
        months = int(metadata.get("months", 1))
    except Exception as e:
        return jsonify({"status": "error", "message": f"Неверные данные: {str(e)}"}), 400

    import asyncio
    asyncio.run(update_subscription(user_id, months))
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(port=5000)
