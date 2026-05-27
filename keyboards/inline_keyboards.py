"""
Инлайн-клавиатуры для бота СТАРИНА VPN.

Все кнопки выполнены в советской/ретро стилистике с эмодзи.
"""

from typing import List, Dict, Any

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ─── Главное меню ───────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню пользователя.
    Стиль: советская эстетика, кнопки с эмодзи.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔓 Купить подписку", callback_data="buy"),
            ],
            [
                InlineKeyboardButton(text="📊 Моя подписка", callback_data="my_subscription"),
                InlineKeyboardButton(text="🔑 Получить конфиг", callback_data="get_config"),
            ],
            [
                InlineKeyboardButton(text="📞 Помощь", callback_data="help"),
            ],
        ]
    )


# ─── Меню покупки подписки ───────────────────────────────────────────────────

def buy_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора тарифа подписки.
    Стиль: советские цены, эмодзи.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗓️ 1 день — 50₽", callback_data="buy_1_50"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 7 дней — 250₽", callback_data="buy_7_250"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 30 дней — 800₽ ⭐ ХИТ", callback_data="buy_30_800"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 90 дней — 2000₽ 💰 ВЫГОДНО", callback_data="buy_90_2000"),
            ],
            [
                InlineKeyboardButton(text="🌍 Выбрать сервер", callback_data="server_select"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="back_to_main"),
            ],
        ]
    )


def buy_without_server_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура покупки без выбора сервера (автовыбор).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗓️ 1 день — 50₽", callback_data="buy_auto_1_50"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 7 дней — 250₽", callback_data="buy_auto_7_250"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 30 дней — 800₽ ⭐ ХИТ", callback_data="buy_auto_30_800"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 90 дней — 2000₽ 💰 ВЫГОДНО", callback_data="buy_auto_90_2000"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="buy"),
            ],
        ]
    )


# ─── Выбор сервера ───────────────────────────────────────────────────────────

def server_selection_keyboard(servers: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора сервера.
    Показывает список серверов с загрузкой.
    """
    buttons = []
    
    for srv in servers:
        sid = srv.get("id")
        name = srv.get("name", "Unknown")
        location = srv.get("location", "—")
        current = srv.get("current_clients", 0)
        max_c = srv.get("max_clients", 0)
        used = srv.get("traffic_used_gb", 0)
        limit = srv.get("traffic_limit_gb", 0)
        status = srv.get("status", "offline")

        # Флаг по локации
        flag = "🌍"
        loc_lower = location.lower()
        if "москв" in loc_lower or "russia" in loc_lower or "росс" in loc_lower:
            flag = "🇷🇺"
        elif "герм" in loc_lower or "germany" in loc_lower or "frankfurt" in loc_lower:
            flag = "🇩🇪"
        elif "usa" in loc_lower or "us-" in name.lower() or "america" in loc_lower or "нью" in loc_lower:
            flag = "🇺🇸"
        elif "netherlands" in loc_lower or "neth" in loc_lower or "амстердам" in loc_lower:
            flag = "🇳🇱"
        elif "финл" in loc_lower or "finland" in loc_lower or "хельс" in loc_lower:
            flag = "🇫🇮"

        # Статус
        if status == "online":
            status_emoji = "🟢"
        elif status == "overloaded":
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"

        # Текст кнопки
        text = f"{flag} {name} — {current}/{max_c} клиентов — {status_emoji}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"server_pick_{sid}")])

    # Нижние кнопки
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить список", callback_data="server_select"),
    ])
    buttons.append([
        InlineKeyboardButton(text="← Назад", callback_data="buy"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def server_picked_keyboard(server_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура после выбора сервера: выбор тарифа.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗓️ 1 день — 50₽", callback_data=f"buy_srv_{server_id}_1_50"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 7 дней — 250₽", callback_data=f"buy_srv_{server_id}_7_250"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 30 дней — 800₽ ⭐ ХИТ", callback_data=f"buy_srv_{server_id}_30_800"),
            ],
            [
                InlineKeyboardButton(text="🗓️ 90 дней — 2000₽ 💰 ВЫГОДНО", callback_data=f"buy_srv_{server_id}_90_2000"),
            ],
            [
                InlineKeyboardButton(text="← Выбрать другой сервер", callback_data="server_select"),
            ],
        ]
    )


# ─── Выбор способа оплаты ─────────────────────────────────────────────────────

def payment_method_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора способа оплаты.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏦 Т-Банк (карты РФ)", callback_data="payment_tbank"),
            ],
            [
                InlineKeyboardButton(text="₿ CryptoBot (криптовалюта)", callback_data="payment_crypto"),
            ],
            [
                InlineKeyboardButton(text="💰 ЮKassa", callback_data="payment_yukassa"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="back_to_main"),
            ],
        ]
    )


# ─── Оплата Т-Банк ───────────────────────────────────────────────────────────

def t_bank_payment_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура после показа реквизитов Т-Банка.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"i_paid_{payment_id}"),
            ],
            [
                InlineKeyboardButton(text="💳 Другой способ оплаты", callback_data="payment_select"),
            ],
            [
                InlineKeyboardButton(text="← Назад к тарифам", callback_data="buy"),
            ],
        ]
    )


def t_bank_payment_back_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой возврата после показа реквизитов.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"i_paid_{payment_id}"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="buy"),
            ],
        ]
    )


# ─── Моя подписка ────────────────────────────────────────────────────────────

def my_subscription_keyboard(has_active: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура для страницы «Моя подписка».
    """
    if has_active:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔑 Получить конфигурацию", callback_data="get_config"),
                ],
                [
                    InlineKeyboardButton(text="💳 Продлить подписку", callback_data="buy"),
                ],
                [
                    InlineKeyboardButton(text="📞 Техподдержка", callback_data="help"),
                ],
                [
                    InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"),
                ],
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy"),
                ],
                [
                    InlineKeyboardButton(text="📊 Тарифы", callback_data="tariffs"),
                ],
                [
                    InlineKeyboardButton(text="📞 Техподдержка", callback_data="help"),
                ],
                [
                    InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"),
                ],
            ]
        )


# ─── Конфигурация v2Ray ─────────────────────────────────────────────────────

def get_config_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для страницы конфигурации.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Скопировать конфигурацию", callback_data="copy_config"),
            ],
            [
                InlineKeyboardButton(text="💾 Скачать как файл", callback_data="download_config"),
            ],
            [
                InlineKeyboardButton(text="📞 Техподдержка", callback_data="help"),
            ],
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"),
            ],
        ]
    )


def no_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для страницы без активной подписки.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy"),
            ],
            [
                InlineKeyboardButton(text="📊 Тарифы", callback_data="tariffs"),
            ],
            [
                InlineKeyboardButton(text="📞 Техподдержка", callback_data="help"),
            ],
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"),
            ],
        ]
    )


# ─── Помощь ─────────────────────────────────────────────────────────────────

def help_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для страницы помощи.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Как подключить v2RayTun", callback_data="how_to_connect"),
            ],
            [
                InlineKeyboardButton(text="📊 Тарифы", callback_data="tariffs"),
            ],
            [
                InlineKeyboardButton(text="📞 Написать в поддержку", callback_data="contact_support"),
            ],
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"),
            ],
        ]
    )


# ─── Админ-клавиатуры ────────────────────────────────────────────────────────

def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню администратора.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            ],
            [
                InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users"),
            ],
            [
                InlineKeyboardButton(text="🖥 Сервера", callback_data="admin_servers"),
            ],
            [
                InlineKeyboardButton(text="💰 Заявки на оплату", callback_data="admin_payments"),
            ],
            [
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            ],
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"),
            ],
        ]
    )


def admin_payment_confirmation_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для админа: подтвердить или отклонить платёж.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_payment_{payment_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_decline_payment_{payment_id}"),
            ],
            [
                InlineKeyboardButton(text="📞 Написать пользователю", callback_data=f"admin_contact_user_{payment_id}"),
            ],
        ]
    )


def admin_payments_list_keyboard(payments: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Клавиатура списка заявок на оплату.
    """
    buttons = []
    for p in payments:
        pid = p.get("payment_id")
        amount = p.get("amount", 0)
        days = p.get("tariff_days", 0)
        status = p.get("status", "pending")
        
        status_emoji = "⏳" if status == "pending_confirmation" else "✅" if status == "paid" else "❌"
        
        text = f"{status_emoji} #{pid} — {amount}₽ ({days} дней)"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"admin_payment_detail_{pid}")])

    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_payments"),
    ])
    buttons.append([
        InlineKeyboardButton(text="← Назад", callback_data="admin_back"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_users_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура списка пользователей (админ).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Поиск по ID", callback_data="admin_user_search"),
                InlineKeyboardButton(text="📊 Активные", callback_data="admin_users_active"),
            ],
            [
                InlineKeyboardButton(text="❌ Заблокированные", callback_data="admin_users_banned"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="admin_back"),
            ],
        ]
    )


def admin_servers_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура управления серверами (админ).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить сервер", callback_data="server_add"),
            ],
            [
                InlineKeyboardButton(text="🔄 Проверить все", callback_data="servers_check_all"),
                InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="servers_refresh"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки балансировки", callback_data="servers_balance_settings"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="admin_back"),
            ],
        ]
    )


def servers_list_keyboard(servers: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Клавиатура списка серверов для админ-панели.
    """
    buttons = []
    for srv in servers:
        sid = srv.get("id")
        name = srv.get("name", "Unknown")
        location = srv.get("location", "—")
        current = srv.get("current_clients", 0)
        max_c = srv.get("max_clients", 0)
        used = srv.get("traffic_used_gb", 0)
        limit = srv.get("traffic_limit_gb", 0)
        status = srv.get("status", "offline")
        is_active = srv.get("is_active", 1)

        # Флаг по локации
        flag = "🌍"
        loc_lower = location.lower()
        if "москв" in loc_lower or "russia" in loc_lower or "росс" in loc_lower:
            flag = "🇷🇺"
        elif "герм" in loc_lower or "germany" in loc_lower or "frankfurt" in loc_lower:
            flag = "🇩🇪"
        elif "usa" in loc_lower or "us-" in name.lower() or "america" in loc_lower or "нью" in loc_lower:
            flag = "🇺🇸"
        elif "netherlands" in loc_lower or "neth" in loc_lower or "амстердам" in loc_lower:
            flag = "🇳🇱"
        elif "финл" in loc_lower or "finland" in loc_lower or "хельс" in loc_lower:
            flag = "🇫🇮"

        status_emoji = "🟢" if status == "online" else "🔴" if status == "offline" else "🟡"
        active_emoji = "✅" if is_active else "❌"

        text = f"{flag} {name} [{current}/{max_c}] [{int(used)}/{limit}GB] {status_emoji}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"server_detail_{sid}")])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить сервер", callback_data="server_add"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="servers_refresh"),
    ])
    buttons.append([
        InlineKeyboardButton(text="← Назад", callback_data="admin_back"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def server_detail_keyboard(server_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура детального просмотра сервера (админ).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"server_edit_{server_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"server_remove_{server_id}"),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Деактивировать" if is_active else "✅ Активировать",
                    callback_data=f"server_toggle_{server_id}",
                ),
            ],
            [
                InlineKeyboardButton(text="🔄 Проверить", callback_data=f"server_test_{server_id}"),
                InlineKeyboardButton(text="← Назад", callback_data="servers_refresh"),
            ],
        ]
    )


# ─── Серверное управление FSM ────────────────────────────────────────────────

def confirm_add_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения добавления сервера."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_add_yes"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm_add_edit"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="confirm_add_cancel"),
            ],
        ]
    )


def confirm_yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура да/нет."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
                InlineKeyboardButton(text="❌ Нет", callback_data=no_data),
            ],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены операции."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_fsm")],
        ]
    )


def back_cancel_keyboard(step: str) -> InlineKeyboardMarkup:
    """Кнопки назад и отмена для многошагового ввода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="← Назад", callback_data=f"back_{step}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_fsm"),
            ],
        ]
    )


def edit_field_keyboard(server_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data=f"edit_field_{server_id}_name"),
                InlineKeyboardButton(text="🔗 URL", callback_data=f"edit_field_{server_id}_url"),
            ],
            [
                InlineKeyboardButton(text="👤 Логин", callback_data=f"edit_field_{server_id}_username"),
                InlineKeyboardButton(text="🔒 Пароль", callback_data=f"edit_field_{server_id}_password"),
            ],
            [
                InlineKeyboardButton(text="📍 Локация", callback_data=f"edit_field_{server_id}_location"),
                InlineKeyboardButton(text="📊 Трафик", callback_data=f"edit_field_{server_id}_traffic_limit_gb"),
            ],
            [
                InlineKeyboardButton(text="👥 Клиенты", callback_data=f"edit_field_{server_id}_max_clients"),
                InlineKeyboardButton(text="⚙️ Вес", callback_data=f"edit_field_{server_id}_balance_weight"),
            ],
            [
                InlineKeyboardButton(text="💾 Сохранить", callback_data=f"server_detail_{server_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"server_detail_{server_id}"),
            ],
        ]
    )


def retry_edit_cancel_keyboard(retry_data: str, edit_data: str) -> InlineKeyboardMarkup:
    """Клавиатура для ошибки подключения: повторить/изменить/отмена."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=retry_data),
                InlineKeyboardButton(text="✏️ Изменить данные", callback_data=edit_data),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_fsm"),
            ],
        ]
    )


def retry_cancel_keyboard(retry_data: str) -> InlineKeyboardMarkup:
    """Клавиатура повторить/отмена."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=retry_data),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_fsm"),
            ],
        ]
    )


# ─── Вспомогательные функции ─────────────────────────────────────────────────

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
            [
                InlineKeyboardButton(text="← Назад", callback_data="back_to_main"),
            ],
        ]
    )


def back_keyboard(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Простая кнопка назад."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Назад", callback_data=callback_data)],
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
            [
                InlineKeyboardButton(text="🖥 Сервера", callback_data="admin_servers"),
            ],
        ]
    )


# ─── Server management keyboards ────────────────────────────────────────────

def servers_list_keyboard(servers: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура списка серверов для /servers."""
    buttons = []
    for srv in servers:
        sid = srv.get("id")
        name = srv.get("name", "Unknown")
        location = srv.get("location", "—")
        current = srv.get("current_clients", 0)
        max_c = srv.get("max_clients", 0)
        used = srv.get("traffic_used_gb", 0)
        limit = srv.get("traffic_limit_gb", 0)
        status = srv.get("status", "offline")
        is_active = srv.get("is_active", 1)

        # Флаг по локации (упрощённо)
        flag = "🌍"
        if "герм" in location.lower() or "germany" in location.lower() or "frankfurt" in location.lower():
            flag = "🇩🇪"
        elif "usa" in location.lower() or "us-" in name.lower() or "america" in location.lower():
            flag = "🇺🇸"
        elif "netherlands" in location.lower() or "neth" in location.lower() or "amsterdam" in location.lower():
            flag = "🇳🇱"
        elif "франц" in location.lower() or "france" in location.lower() or "paris" in location.lower():
            flag = "🇫🇷"
        elif "англ" in location.lower() or "uk" in location.lower() or "london" in location.lower():
            flag = "🇬🇧"

        status_emoji = "🟢" if status == "online" else "🔴" if status == "offline" else "🟡"
        active_emoji = "✅" if is_active else "❌"

        # Кнопка с краткой инфой
        text = f"{flag} {name} [{current}/{max_c}] [{int(used)}/{limit}GB] {status_emoji}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"server_detail_{sid}")])

    # Нижний ряд управления
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить сервер", callback_data="server_add"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="servers_refresh"),
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Закрыть", callback_data="servers_close"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def server_detail_keyboard(server_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура детального просмотра сервера."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"server_edit_{server_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"server_remove_{server_id}"),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Деактивировать" if is_active else "✅ Активировать",
                    callback_data=f"server_toggle_{server_id}",
                ),
            ],
            [
                InlineKeyboardButton(text="🔄 Проверить", callback_data=f"server_test_{server_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="servers_refresh"),
            ],
        ]
    )


def confirm_add_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения добавления сервера."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_add_yes"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm_add_edit"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="confirm_add_cancel"),
            ],
        ]
    )


def confirm_yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура да/нет."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
                InlineKeyboardButton(text="❌ Нет", callback_data=no_data),
            ],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены операции."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_fsm")],
        ]
    )


def back_cancel_keyboard(step: str) -> InlineKeyboardMarkup:
    """Кнопки назад и отмена для многошагового ввода."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_{step}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_fsm"),
            ],
        ]
    )


def edit_field_keyboard(server_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data=f"edit_field_{server_id}_name"),
                InlineKeyboardButton(text="🔗 URL", callback_data=f"edit_field_{server_id}_url"),
            ],
            [
                InlineKeyboardButton(text="👤 Логин", callback_data=f"edit_field_{server_id}_username"),
                InlineKeyboardButton(text="🔒 Пароль", callback_data=f"edit_field_{server_id}_password"),
            ],
            [
                InlineKeyboardButton(text="📍 Локация", callback_data=f"edit_field_{server_id}_location"),
                InlineKeyboardButton(text="📊 Трафик", callback_data=f"edit_field_{server_id}_traffic_limit_gb"),
            ],
            [
                InlineKeyboardButton(text="👥 Клиенты", callback_data=f"edit_field_{server_id}_max_clients"),
                InlineKeyboardButton(text="⚙️ Вес", callback_data=f"edit_field_{server_id}_balance_weight"),
            ],
            [
                InlineKeyboardButton(text="💾 Сохранить", callback_data=f"server_detail_{server_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"server_detail_{server_id}"),
            ],
        ]
    )


def retry_edit_cancel_keyboard(retry_data: str, edit_data: str) -> InlineKeyboardMarkup:
    """Клавиатура для ошибки подключения: повторить/изменить/отмена."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=retry_data),
                InlineKeyboardButton(text="✏️ Изменить данные", callback_data=edit_data),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_fsm"),
            ],
        ]
    )


def retry_cancel_keyboard(retry_data: str) -> InlineKeyboardMarkup:
    """Клавиатура повторить/отмена."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=retry_data),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_fsm"),
            ],
        ]
    )
