import uuid
from yookassa import Configuration, Payment
import os

Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

# Цены подписок в формате строки с двумя знаками после запятой
SUBSCRIPTION_PRICING = {
    1: "379.00",
    3: "999.00",
    12: "3599.00"
}


def create_payment_session(user_id: int, months: int, return_url: str) -> str:
    amount = SUBSCRIPTION_PRICING.get(months)
    if not amount:
        raise ValueError("Неверное количество месяцев подписки")

    payment = Payment.create({
        "amount": {
            "value": amount,
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": f"Оплата подписки VPN на {months} месяц(ев)",
        "client_reference_id": str(user_id)
    }, uuid.uuid4())

    return payment.confirmation.confirmation_url
