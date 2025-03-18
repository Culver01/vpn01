import os
import uuid
from yookassa import Configuration, Payment

# Загружаем параметры YooKassa из переменных окружения
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

# Цены подписок (с двумя знаками после запятой)
SUBSCRIPTION_PRICING = {
    1: "490.00",   # 1 месяц
    6: "2394.00",  # 6 месяцев
    12: "3588.00"  # 12 месяцев
}

def create_payment_session(user_id: int, months: int, return_url: str, cancel_url: str) -> str:
    """
    Создает платежную сессию через YooKassa и возвращает URL для оплаты.

    :param user_id: Идентификатор пользователя Telegram.
    :param months: Количество месяцев подписки (1, 6, 12).
    :param return_url: URL, на который будет перенаправлен пользователь после оплаты.
    :param cancel_url: URL для отмены (используется для совместимости).
    :return: URL платежной сессии.
    """
    price = SUBSCRIPTION_PRICING.get(months)
    if not price:
        raise ValueError("Неверное количество месяцев для подписки")

    receipt = {
        "customer": {
            "email": "example@example.com"
        },
        "items": [
            {
                "description": f"Оплата подписки VPN на {months} месяц(ев)",
                "quantity": "1.00",
                "amount": {"value": price, "currency": "RUB"},
                "vat_code": 1,  # без НДС – указываем 1 как число
                "payment_mode": "full_payment",
                "payment_subject": "service"
            }
        ]
    }

    payload = {
        "amount": {"value": price, "currency": "RUB"},
        "payment_method_data": {"type": "bank_card"},
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": f"Оплата подписки VPN на {months} месяц(ев)",
        "client_reference_id": str(user_id),
        "receipt": receipt
    }

    # Создаем платежную сессию с уникальным idempotence-ключом (в виде строки)
    payment = Payment.create(payload, str(uuid.uuid4()))
    return payment.confirmation.confirmation_url
