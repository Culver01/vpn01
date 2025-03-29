import os
import uuid
import asyncio
import logging
from yookassa import Configuration, Payment
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from database import update_subscription  # Функция должна быть реализована в database.py

# Загружаем переменные окружения из token.env
load_dotenv("token.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка YooKassa: значения берутся из token.env
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")  # Пример: ZSVOZSVOZSVO
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")  # Пример: ZSVOZSVOZSVO

# Цены подписок (в формате строки с двумя десятичными знаками)
SUBSCRIPTION_PRICING = {
    1: "20.00",   # 1 месяц
    6: "2394.00", # 6 месяцев
    12: "3588.00" # 12 месяцев
}

def create_payment_session(user_id: int, months: int, return_url: str, cancel_url: str) -> str:
    """
    Создает платежную сессию через YooKassa и возвращает URL для оплаты.
    """
    price = SUBSCRIPTION_PRICING.get(months)
    if not price:
        raise ValueError("Неверное количество месяцев для подписки")

    # Формируем объект receipt согласно требованиям YooKassa:
    receipt = {
        "customer": {
            # Обязательно укажите хотя бы один контакт: email или phone.
            "email": "example@example.com"  # Тестовый email. Замените на реальные данные, если они есть.
        },
        "items": [
            {
                "description": f"Оплата подписки VPN на {months} месяц(ев)",
                "quantity": "1.00",
                "amount": {"value": price, "currency": "RUB"},
                "vat_code": "1",
                "payment_mode": "full_payment",
                "payment_subject": "service"
            }
        ],
        "sno": "osn"
    }

    payload = {
        "amount": {"value": price, "currency": "RUB"},
        "payment_method_data": {"type": "bank_card"},
        "confirmation": {
            "type": "redirect",
            "return_url": return_url,
            "cancel_url": cancel_url
        },
        "capture": True,
        "description": f"Оплата подписки VPN на {months} месяц(ев)",
        "client_reference_id": str(user_id),
        "receipt": receipt,
        "metadata": {"months": months}
    }

    payment = Payment.create(payload, str(uuid.uuid4()))
    return payment.confirmation.confirmation_url


# Flask-приложение для обработки webhook-уведомлений от YooKassa
app = Flask(__name__)

@app.route('/yookassa/webhook', methods=['POST'])
def yookassa_webhook():
    data = request.get_json()
    logger.info("Получен webhook от YooKassa: %s", data)
    event = data.get("event")
    if event == "payment.succeeded":
        try:
            payment_obj = data.get("object", {})
            user_id = int(payment_obj.get("client_reference_id"))
            months = int(payment_obj.get("metadata", {}).get("months", 0))
            if months <= 0:
                logger.error("Некорректное количество месяцев в metadata")
                return jsonify({"status": "error", "message": "Некорректные данные"}), 400

            # Используем asyncio.run для асинхронного обновления подписки
            result = asyncio.run(update_subscription(user_id, months))

            if result:
                logger.info(f"Подписка обновлена для пользователя {user_id} на {months} месяцев")
                return jsonify({"status": "success"}), 200
            else:
                logger.error(f"Ошибка обновления подписки для пользователя {user_id}")
                return jsonify({"status": "error"}), 500
        except Exception as e:
            logger.exception("Ошибка обработки webhook")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        logger.warning("Получено неподдерживаемое событие: %s", event)
        return jsonify({"status": "ignored"}), 200

if __name__ == '__main__':
    app.run(port=8000)
