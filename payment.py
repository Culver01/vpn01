import os
import uuid
from yookassa import Configuration, Payment
from dotenv import load_dotenv

# Загружаем переменные окружения из token.env
load_dotenv("token.env")

# Настройка YooKassa: значения берутся из token.env
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")  # Например, ZSVOZSVOZSVO
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")  # Например, ZSVOZSVOZSVO

# Цены подписок (в формате строки с двумя десятичными знаками)
SUBSCRIPTION_PRICING = {
    1: "490.00",  # 1 месяц
    6: "2394.00",  # 6 месяцев
    12: "3588.00"  # 12 месяцев
}


def create_payment_session(user_id: int, months: int, return_url: str, cancel_url: str) -> str:
    """
    Создает платежную сессию через YooKassa и возвращает URL для оплаты.

    :param user_id: Идентификатор пользователя Telegram.
    :param months: Период подписки (1, 6 или 12 месяцев).
    :param return_url: URL, на который будет перенаправлен пользователь после оплаты.
                       Обычно это глубокая ссылка вида:
                       https://t.me/your_bot_username?start=payment_success
    :param cancel_url: URL для отмены оплаты (можно использовать глубокую ссылку с другим параметром, например, payment_cancel).
    :return: URL платежной сессии.
    """
    price = SUBSCRIPTION_PRICING.get(months)
    if not price:
        raise ValueError("Неверное количество месяцев для подписки")

    # Формируем объект receipt согласно требованиям YooKassa:
    receipt = {
        "customer": {
            # Обязательно укажите хотя бы один контакт: email или phone.
            "email": "example@example.com"  # Тестовый email. Замените на реальные данные, если они есть.
            # Если нужен телефон, можно добавить: "phone": "+79000000000"
        },
        "items": [
            {
                "description": f"Оплата подписки VPN на {months} месяц(ев)",
                "quantity": "1.00",  # Количество в виде строки с двумя знаками после запятой
                "amount": {"value": price, "currency": "RUB"},
                "vat_code": "1",  # Код НДС в виде строки; уточните значение согласно вашей налоговой системе
                "payment_mode": "full_payment",  # Режим оплаты – полная оплата
                "payment_subject": "service"  # Тип услуги – сервис
            }
        ],
        "sno": "osn"  # Система налогообложения: "osn" означает общую систему
    }

    payload = {
        "amount": {"value": price, "currency": "RUB"},
        "payment_method_data": {"type": "bank_card"},
        "confirmation": {
            "type": "redirect",
            "return_url": return_url  # Глубокая ссылка для возврата в бота
        },
        "capture": True,
        "description": f"Оплата подписки VPN на {months} месяц(ев)",
        "client_reference_id": str(user_id),
        "receipt": receipt
    }

    payment = Payment.create(payload, str(uuid.uuid4()))
    return payment.confirmation.confirmation_url
