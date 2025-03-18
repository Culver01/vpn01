import os
import uuid
from yookassa import Configuration, Payment

# Загружаем параметры YooKassa из переменных окружения
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

# Цены подписок (в формате строки с двумя знаками после запятой)
SUBSCRIPTION_PRICING = {
    1: "490.00",   # 1 месяц
    6: "2394.00",  # 6 месяцев
    12: "3588.00"  # 12 месяцев
}

def create_payment_session(user_id: int, months: int, return_url: str, cancel_url: str) -> str:
    """
    Создает платежную сессию через YooKassa и возвращает URL для оплаты.

    :param user_id: Идентификатор пользователя Telegram.
    :param months: Период подписки (1, 6 или 12 месяцев).
    :param return_url: URL, на который будет перенаправлен пользователь после оплаты.
    :param cancel_url: URL для отмены (используется для совместимости, YooKassa обрабатывает только return_url).
    :return: URL для подтверждения оплаты.
    """
    price = SUBSCRIPTION_PRICING.get(months)
    if not price:
        raise ValueError("Неверное количество месяцев для подписки")

    # Формируем объект receipt согласно требованиям YooKassa.
    # Обратите внимание, что все числовые значения (например, quantity, amount.value) должны быть в виде строк с двумя знаками после запятой,
    # а также vat_code передается как строка.
    receipt = {
        "customer": {
            "email": "culver01business@icloud.com",  # Тестовый email. Подставьте реальный, если он есть.
            "phone": "+79935970230"           # Тестовый номер телефона. Подставьте реальный, если он есть.
        },
        "items": [
            {
                "description": f"Оплата подписки VPN на {months} месяц(ев)",
                "quantity": "1.00",  # Количество в виде строки с двумя знаками после запятой
                "amount": {"value": price, "currency": "RUB"},
                "vat_code": "1",     # Код НДС в виде строки (обычно "1" означает отсутствие НДС)
                "payment_mode": "full_payment",  # Режим оплаты: полная оплата
                "payment_subject": "service"       # Тип товара: услуга
            }
        ],
        "sno": "osn"  # Система налогообложения: "osn" – общая система
    }

    # Формируем payload для создания платежной сессии.
    payload = {
        "amount": {"value": price, "currency": "RUB"},
        "payment_method_data": {"type": "bank_card"},  # Явно указываем тип метода оплаты
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/rogerscriptedbot?start=payment_success"  # URL, на который пользователь будет перенаправлен после оплаты
        },
        "capture": True,
        "description": f"Оплата подписки VPN на {months} месяц(ев)",
        "client_reference_id": str(user_id),
        "receipt": receipt
    }

    # Создаем платежную сессию с уникальным idempotence-ключом
    payment = Payment.create(payload, str(uuid.uuid4()))
    return payment.confirmation.confirmation_url
