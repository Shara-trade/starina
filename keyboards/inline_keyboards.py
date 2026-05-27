"""
Инлайн-клавиатуры для взаимодействия с ботом.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню пользователя."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy"),
            ],
            [
                InlineKeyboardButton(text="📋 Моя подписка", callback_data="my_subscription"),
                InlineKeyboardButton(text="⚙️ Получить конфиг", callback_data="get_config"),
            ],
            [
                InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            ],
        ]
    )


def buy_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора подписки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 месяц — 299₽", callback_data="buy_30_299"),
            ],
            [
                InlineKeyboardButton(text="3 месяца — 799₽", callback_data="buy_90_799"),
            ],
            [
                InlineKeyboardButton(text="6 месяцев — 1499₽", callback_data="buy_180_1499"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"),
            ],
        ]
    )


def t_bank_payment_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура после показа реквизитов Т-Банка."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"i_paid_{payment_id}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад к тарифам", callback_data="buy"),
            ],
        ]
    )


def admin_payment_confirmation_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для админа: подтвердить или отклонить платёж."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_payment_{payment_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_decline_payment_{payment_id}"),
            ],
        ]
    )


def protocol_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора протокола VPN."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="VLESS", callback_data="protocol_vless"),
                InlineKeyboardButton(text="VMess", callback_data="protocol_vmess"),
            ],
            [
                InlineKeyboardButton(text="Trojan", callback_data="protocol_trojan"),
            ],
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-панель."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            ],
            [
                InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users"),
            ],
        ]
    )
