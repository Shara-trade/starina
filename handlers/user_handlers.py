"""
Обработчики пользовательских команд и callback'ов.

Стиль: советская/ретро эстетика «Старина VPN».
"""

import logging
from datetime import datetime
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database import Database
from xui_client import XuiClient
from keyboards.inline_keyboards import (
    main_menu_keyboard,
    buy_subscription_keyboard,
    t_bank_payment_keyboard,
    my_subscription_keyboard,
    get_config_keyboard,
    no_subscription_keyboard,
    help_keyboard,
    server_selection_keyboard,
    server_picked_keyboard,
    admin_payment_confirmation_keyboard,
)
from messages import StarinaMessages as Msg

import config

logger = logging.getLogger(__name__)
router = Router()

# ─── /start ─────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def start_handler(message: Message, db: Database) -> None:
    """
    Обработчик команды /start.
    Регистрирует пользователя и показывает главное меню в советском стиле.
    """
    telegram_id = message.from_user.id
    username = message.from_user.username

    # Проверяем реферальный параметр
    referrer_id: Optional[int] = None
    if message.text and len(message.text.split()) > 1:
        ref_arg = message.text.split()[1]
        if ref_arg.startswith("ref"):
            try:
                referrer_id = int(ref_arg[3:])
            except ValueError:
                pass

    created = await db.create_user(telegram_id, username, referrer_id)

    if created:
        logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{username or telegram_id} зарегистрирован")
    else:
        logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{username or telegram_id} вернулся")

    await message.answer(
        Msg.GREETING,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )


# ─── /help ──────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Обработчик команды /help в советском стиле."""
    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{message.from_user.username or message.from_user.id} запросил помощь")
    await message.answer(Msg.HELP, parse_mode=ParseMode.MARKDOWN, reply_markup=help_keyboard())


# ─── /my_subscription ───────────────────────────────────────────────────────

@router.message(Command("my_subscription"))
async def my_subscription_handler(message: Message, db: Database) -> None:
    """Обработчик команды /my_subscription в советском стиле."""
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)

    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start", reply_markup=main_menu_keyboard())
        return

    status = user.get("subscription_status", "expired")
    expires = user.get("subscription_expires")
    traffic_limit = user.get("traffic_limit_gb", 50)
    traffic_used = user.get("traffic_used_gb", 0.0)
    server = user.get("server_name", "Германия, Франкфурт")
    xui_client = user.get("xui_client_name", "Не назначен")

    if status == "active" and expires:
        expires_dt = datetime.fromisoformat(expires)
        days_left = (expires_dt - datetime.utcnow()).days
        percent = int(traffic_used / traffic_limit * 100) if traffic_limit > 0 else 0

        text = Msg.MY_SUBSCRIPTION_ACTIVE.format(
            server=server,
            days=days_left,
            expires=Msg.format_date(expires_dt),
            used=f"{traffic_used:.1f}",
            limit=traffic_limit,
            percent=percent
        )
        await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=my_subscription_keyboard(True))
    else:
        # Подписка истекла
        days_ago = 0
        expires_formatted = "—"
        if expires:
            expires_dt = datetime.fromisoformat(expires)
            days_ago = (datetime.utcnow() - expires_dt).days
            expires_formatted = Msg.format_date(expires_dt)

        text = Msg.MY_SUBSCRIPTION_EXPIRED.format(
            expires=expires_formatted,
            days_ago=days_ago
        )
        await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=my_subscription_keyboard(False))

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{message.from_user.username or telegram_id} проверил подписку")


# ─── /buy ───────────────────────────────────────────────────────────────────

@router.message(Command("buy"))
async def buy_handler(message: Message) -> None:
    """Обработчик команды /buy в советском стиле."""
    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{message.from_user.username or message.from_user.id} открыл магазин")
    await message.answer(Msg.BUY_MENU, parse_mode=ParseMode.MARKDOWN, reply_markup=buy_subscription_keyboard())


# ─── /get_config ────────────────────────────────────────────────────────────

@router.message(Command("get_config"))
async def get_config_handler(message: Message, db: Database, xui: XuiClient) -> None:
    """Обработчик команды /get_config в советском стиле."""
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)

    if not user or user.get("subscription_status") != "active":
        await message.answer(
            Msg.GET_CONFIG_NO_ACTIVE,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=no_subscription_keyboard()
        )
        return

    client_name = user.get("xui_client_name")
    if not client_name:
        await message.answer(
            "🔑 Конфигурация v2RayTun\n\n❌ Ошибка: клиент не найден. Обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=help_keyboard()
        )
        return

    # Генерируем конфиг
    config_link = await xui.generate_v2ray_config(client_name, protocol="vless")

    if not config_link:
        await message.answer(
            "🔑 Конфигурация v2RayTun\n\n❌ Ошибка генерации конфига. Попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=help_keyboard()
        )
        return

    expires = user.get("subscription_expires", "—")
    if expires and hasattr(expires, 'isoformat'):
        expires = Msg.format_date(datetime.fromisoformat(expires))

    server = user.get("server_name", "Германия, Франкфурт")

    text = Msg.GET_CONFIG.format(
        server=server,
        expires=expires,
        v2ray_config=config_link
    )

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{message.from_user.username or telegram_id} получил конфиг")
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_config_keyboard())


# ─── /help ──────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """
    Обработчик команды /help.
    Отправляет справочную информацию.
    """
    text = (
        "<b>❓ Помощь по боту</b>\n\n"
        "<b>/start</b> — главное меню\n"
        "<b>/buy</b> — купить подписку\n"
        "<b>/my_subscription</b> — информация о подписке\n"
        "<b>/help</b> — эта справка\n\n"
        "<b>Как подключиться:</b>\n"
        "1. Купите подписку через кнопку «Купить подписку»\n"
        "2. После оплаты нажмите «Получить конфиг»\n"
        "3. Скопируйте ссылку и импортируйте в приложение v2RayTun\n\n"
        "<b>Поддержка:</b> @support"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


# ─── /my_subscription ───────────────────────────────────────────────────────

@router.message(Command("my_subscription"))
async def my_subscription_handler(message: Message, db: Database) -> None:
    """
    Обработчик команды /my_subscription.
    Показывает текущий статус подписки, трафик и срок действия.
    """
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)

    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return

    status = user.get("subscription_status", "expired")
    expires = user.get("subscription_expires")
    traffic_limit = user.get("traffic_limit_gb", 0)
    traffic_used = user.get("traffic_used_gb", 0.0)
    client_name = user.get("xui_client_name", "—")

    if status == "active" and expires:
        expires_dt = datetime.fromisoformat(expires)
        days_left = (expires_dt - datetime.utcnow()).days
        status_text = f"✅ Активна (осталось {days_left} дн.)"
    else:
        status_text = "❌ Нет активной подписки"

    traffic_left = max(0, traffic_limit - traffic_used)

    text = (
        f"<b>📋 Моя подписка</b>\n\n"
        f"Статус: {status_text}\n"
        f"Клиент: <code>{client_name}</code>\n"
        f"Трафик: {traffic_used:.2f} / {traffic_limit} ГБ\n"
        f"Осталось трафика: {traffic_left:.2f} ГБ\n"
    )

    await message.answer(text, parse_mode=ParseMode.HTML)


# ─── /buy ───────────────────────────────────────────────────────────────────

@router.message(Command("buy"))
async def buy_handler(message: Message) -> None:
    """
    Обработчик команды /buy.
    Показывает варианты покупки подписки.
    """
    text = (
        "<b>🛒 Выберите тариф:</b>\n\n"
        "• 1 месяц — 299₽\n"
        "• 3 месяца — 799₽ (экономия 98₽)\n"
        "• 6 месяцев — 1499₽ (экономия 295₽)\n\n"
        "Нажмите на нужный вариант ниже:"
    )
    await message.answer(text, reply_markup=buy_subscription_keyboard(), parse_mode=ParseMode.HTML)


# ─── Callback: buy ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "buy")
async def callback_buy(callback: CallbackQuery) -> None:
    """Показывает меню покупки подписки в советском стиле."""
    await callback.message.edit_text(
        Msg.BUY_MENU,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=buy_subscription_keyboard()
    )
    await callback.answer()


# ─── Callback: server_select (выбор сервера) ────────────────────────────────

@router.callback_query(F.data == "server_select")
async def callback_server_select(callback: CallbackQuery, db: Database) -> None:
    """Показывает список серверов для выбора."""
    servers = await db.get_all_servers()
    
    # Фильтруем только активные серверы
    active_servers = [s for s in servers if s.get("is_active", 1) and s.get("status") != "offline"]
    
    if not active_servers:
        text = """
🌍 Выберите сервер для подключения:

╔═══════════════════════════╗
║   🟡 Серверов нет 🟡     ║
╚═══════════════════════════╝

🏭 Извини, товарищ! Все серверы временно недоступны.

💡 Попробуй позже или выбери автовыбор сервера.
"""
        await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=buy_subscription_keyboard())
    else:
        await callback.message.edit_text(
            Msg.SERVER_SELECTION,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=server_selection_keyboard(active_servers)
        )
    
    await callback.answer()


# ─── Callback: server_pick_X (выбор конкретного сервера) ────────────────────

@router.callback_query(F.data.startswith("server_pick_"))
async def callback_server_pick(callback: CallbackQuery, db: Database) -> None:
    """Обрабатывает выбор конкретного сервера."""
    try:
        server_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка выбора сервера.", show_alert=True)
        return

    server = await db.get_server(server_id)
    if not server:
        await callback.answer("Сервер не найден.", show_alert=True)
        return

    server_name = server.get("name", "Unknown")
    location = server.get("location", "—")

    text = f"""
🌍 Сервер выбран!

╔═══════════════════════════╗
║   ✅ {server_name}      ║
║   📍 {location}          ║
╚═══════════════════════════╝

🏭 Теперь выбери срок подписки:
"""
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=server_picked_keyboard(server_id)
    )
    await callback.answer()


# ─── Callback: my_subscription ──────────────────────────────────────────────

@router.callback_query(F.data == "my_subscription")
async def callback_my_subscription(callback: CallbackQuery, db: Database) -> None:
    """Показывает информацию о подписке через callback."""
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)

    if not user:
        await callback.message.edit_text(
            "❌ Товарищ, сначала зарегистрируйся: /start",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
        return

    status = user.get("subscription_status", "expired")
    expires = user.get("subscription_expires")
    traffic_limit = user.get("traffic_limit_gb", 50)
    traffic_used = user.get("traffic_used_gb", 0.0)
    server = user.get("server_name", "Германия, Франкфурт")

    if status == "active" and expires:
        expires_dt = datetime.fromisoformat(expires)
        days_left = (expires_dt - datetime.utcnow()).days
        percent = int(traffic_used / traffic_limit * 100) if traffic_limit > 0 else 0

        text = Msg.MY_SUBSCRIPTION_ACTIVE.format(
            server=server,
            days=days_left,
            expires=Msg.format_date(expires_dt),
            used=f"{traffic_used:.1f}",
            limit=traffic_limit,
            percent=percent
        )
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=my_subscription_keyboard(True)
        )
    else:
        days_ago = 0
        expires_formatted = "—"
        if expires:
            expires_dt = datetime.fromisoformat(expires)
            days_ago = (datetime.utcnow() - expires_dt).days
            expires_formatted = Msg.format_date(expires_dt)

        text = Msg.MY_SUBSCRIPTION_EXPIRED.format(
            expires=expires_formatted,
            days_ago=days_ago
        )
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=my_subscription_keyboard(False)
        )

    await callback.answer()


# ─── Callback: buy_X_Y (выбор тарифа) ───────────────────────────────────────

@router.callback_query(F.data.startswith("buy_"))
async def callback_buy_select(callback: CallbackQuery, db: Database) -> None:
    """
    Обрабатывает выбор тарифа.
    Показывает реквизиты Т-Банка для ручного перевода.
    Формат callback_data: buy_<days>_<price> или buy_auto_<days>_<price> или buy_srv_<server_id>_<days>_<price>
    """
    parts = callback.data.split("_")
    
    # Определяем формат и извлекаем параметры
    if parts[1] == "auto":
        # buy_auto_<days>_<price>
        days = int(parts[2])
        price = int(parts[3])
        server_id = None
    elif parts[1] == "srv":
        # buy_srv_<server_id>_<days>_<price>
        server_id = int(parts[2])
        days = int(parts[3])
        price = int(parts[4])
    else:
        # buy_<days>_<price>
        days = int(parts[1])
        price = int(parts[2])
        server_id = None

    telegram_id = callback.from_user.id

    # Создаём запись о платеже
    payment_id = await db.add_payment(
        telegram_id=telegram_id,
        amount=float(price),
        tariff_days=days,
        currency="RUB",
        provider="t_bank",
    )

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{callback.from_user.username or telegram_id} выбрал тариф {days} дней за {price}₽")

    text = Msg.PAYMENT_DETAILS.format(
        days=days,
        price=price,
        cardholder=config.T_BANK_CARDHOLDER,
        card=config.T_BANK_CARD,
        phone=config.T_BANK_PHONE
    )

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=t_bank_payment_keyboard(str(payment_id))
    )
    await callback.answer()


# ─── Callback: get_config ───────────────────────────────────────────────────

@router.callback_query(F.data == "get_config")
async def callback_get_config(callback: CallbackQuery, db: Database, xui: XuiClient) -> None:
    """
    Отправляет пользователю v2ray:// конфигурацию в советском стиле.
    """
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)

    if not user or user.get("subscription_status") != "active":
        await callback.message.edit_text(
            Msg.GET_CONFIG_NO_ACTIVE,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=no_subscription_keyboard()
        )
        await callback.answer()
        return

    client_name = user.get("xui_client_name")
    if not client_name:
        await callback.message.edit_text(
            "🔑 Конфигурация v2RayTun\n\n❌ Ошибка: клиент не найден. Обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=help_keyboard()
        )
        await callback.answer()
        return

    # Запрашиваем конфиг у 3x-ui
    config_link = await xui.generate_v2ray_config(client_name, protocol="vless")

    if not config_link:
        await callback.message.edit_text(
            "🔑 Конфигурация v2RayTun\n\n❌ Ошибка генерации конфига. Попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=help_keyboard()
        )
        await callback.answer()
        return

    expires = user.get("subscription_expires", "—")
    if expires and not isinstance(expires, str):
        expires = Msg.format_date(expires)
    elif expires:
        try:
            expires_dt = datetime.fromisoformat(expires)
            expires = Msg.format_date(expires_dt)
        except:
            pass

    server = user.get("server_name", "Германия, Франкфурт")

    text = Msg.GET_CONFIG.format(
        server=server,
        expires=expires,
        v2ray_config=config_link
    )

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{callback.from_user.username or telegram_id} получил конфиг")
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_config_keyboard()
    )
    await callback.answer()


# ─── Callback: back_to_main ─────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery) -> None:
    """Возвращает в главное меню в советском стиле."""
    await callback.message.edit_text(
        Msg.GREETING,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


# ─── Callback: help ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery) -> None:
    """Показывает справку в советском стиле."""
    await callback.message.edit_text(
        Msg.HELP,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=help_keyboard()
    )
    await callback.answer()


# ─── Callback: i_paid_X (пользователь нажал "Я оплатил") ────────────────────

@router.callback_query(F.data.startswith("i_paid_"))
async def callback_i_paid(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    """
    Пользователь подтверждает оплату.
    """
    try:
        payment_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка заявки.", show_alert=True)
        return

    telegram_id = callback.from_user.id
    payment = await db.get_payment(payment_id)

    if not payment:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if payment.get("status") != "pending":
        await callback.answer("Эта заявка уже обработана.", show_alert=True)
        return

    # Обновляем статус
    await db.update_payment_status(payment_id, "pending_confirmation")

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [INFO] Товарищ @{callback.from_user.username or telegram_id} отправил заявку #{payment_id} на проверку")

    # Отвечаем пользователю
    await callback.message.edit_text(
        Msg.PAYMENT_PENDING,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

    # Уведомляем всех админов
    user = await db.get_user(telegram_id)
    username = user.get("username") or "—" if user else "—"
    amount = payment.get("amount", 0)
    days = payment.get("tariff_days", 0)
    created_at = payment.get("created_at", "")

    admin_text = Msg.ADMIN_NEW_PAYMENT.format(
        id=payment_id,
        telegram_id=telegram_id,
        username=username,
        amount=amount,
        days=days,
        time=created_at
    )

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_payment_confirmation_keyboard(str(payment_id)),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as exc:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {exc}")
