"""
Обработчики административных команд.

Стиль: советская/ретро эстетика «Старина VPN».

Доступны только пользователям, чей Telegram ID указан в ADMIN_IDS.
"""

import logging
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database import Database
from xui_client import XuiClient
from keyboards.inline_keyboards import (
    admin_menu_keyboard,
    admin_payment_confirmation_keyboard,
    admin_payments_list_keyboard,
    admin_users_keyboard,
    admin_servers_keyboard,
    servers_list_keyboard,
    server_detail_keyboard,
)
from messages import StarinaMessages as Msg

logger = logging.getLogger(__name__)
router = Router()

# Применяем AdminMiddleware ко всем обработчикам этого роутера
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


# ─── /admin ─────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_handler(message: Message) -> None:
    """
    Обработчик команды /admin.
    Показывает панель администратора в советском стиле.
    """
    admin_text = """
🏭 Админ-панель — СТАРИНА VPN

╔═══════════════════════════╗
║   🛡️ СТАРИНА VPN 🛡️     ║
║    Панель управления     ║
╚═══════════════════════════╝

🏭 Добро пожаловать, товарищ администратор!

Выбери действие:
"""
    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [ADMIN] Товарищ @{message.from_user.username or message.from_user.id} открыл админ-панель")
    await message.answer(admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_keyboard())


# ─── /add_subscription ──────────────────────────────────────────────────────

@router.message(Command("add_subscription"))
async def add_subscription_handler(message: Message, db: Database, xui: XuiClient) -> None:
    """
    Добавляет или продлевает подписку пользователю.
    Формат: /add_subscription <telegram_id> <days>
    """
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            """
🏭 Использование команды:

╔═══════════════════════════╗
║   📋 Справка по команде   ║
╚═══════════════════════════╝

<code>/add_subscription &lt;telegram_id&gt; &lt;days&gt;</code>

🏭 Пример:
<code>/add_subscription 123456789 30</code>

Это продлит подписку товарища на 30 дней.
""",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        target_id = int(args[1])
        days = int(args[2])
    except ValueError:
        await message.answer("❌ Неверные аргументы. ID и дни должны быть числами.")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден.")
        return

    # Создаём или обновляем клиента в 3x-ui
    client_name = user.get("xui_client_name") or f"user_{target_id}_admin"
    client_data = await xui.create_client(
        client_name=client_name,
        traffic_gb=100,
        expire_days=days,
    )

    if not client_data and not user.get("xui_client_name"):
        await message.answer("❌ Ошибка создания клиента в 3x-ui.")
        return

    await db.update_subscription(target_id, days=days, client_name=client_name, traffic_gb=100)

    await message.answer(
        f"""
✅ Подписка активирована, товарищ!

╔═══════════════════════════╗
║   🛡️ СТАРИНА VPN 🛡️     ║
║   ✅ Подписка активирована!║
╚═══════════════════════════╝

🏭 Пользователь: <code>{target_id}</code>
📅 Срок: <b>{days}</b> дней
🔑 Статус: ✅ Активна

🏭 Твой трафик под защитой!
""",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [ADMIN] Админ {message.from_user.id} продлил подписку {target_id} на {days} дней.")


# ─── /ban ───────────────────────────────────────────────────────────────────

@router.message(Command("ban"))
async def ban_handler(message: Message, db: Database, xui: XuiClient) -> None:
    """
    Блокирует пользователя и удаляет его из 3x-ui.
    Формат: /ban <telegram_id>
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            """
🏭 Использование команды:

╔═══════════════════════════╗
║   📋 Справка по команде   ║
╚═══════════════════════════╝

<code>/ban &lt;telegram_id&gt;</code>

🏭 Пример:
<code>/ban 123456789</code>

Это заблокирует товарища.
""",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный ID пользователя.")
        return

    user = await db.get_user(target_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден.")
        return

    # Удаляем клиента из 3x-ui
    client_name = user.get("xui_client_name")
    if client_name:
        await xui.delete_client(client_name)

    # Баним в БД
    await db.ban_user(target_id)

    await message.answer(
        f"""
🚫 Пользователь заблокирован!

╔═══════════════════════════╗
║   🚫 Доступ закрыт       ║
╚═══════════════════════════╝

🏭 Пользователь: <code>{target_id}</code>
🔑 Статус: ❌ Заблокирован

🏭 На заводе строго с дисциплиной!
""",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [ADMIN] Админ {message.from_user.id} забанил пользователя {target_id}.")


# ─── /payments ──────────────────────────────────────────────────────────────

@router.message(Command("payments"))
async def payments_handler(message: Message, db: Database) -> None:
    """
    Показывает список заявок на подтверждение оплаты в советском стиле.
    Формат: /payments
    """
    payments = await db.get_pending_confirmation_payments()
    if not payments:
        await message.answer(
            """
💰 Заявки на оплату — СТАРИНА VPN

╔═══════════════════════════╗
║   ✅ Заявок нет 🟢       ║
╚═══════════════════════════╝

🏭 Все заявки обработаны, товарищ!

Отличная работа на заводе!
""",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_menu_keyboard()
        )
        return

    text = """
💰 Заявки на оплату — СТАРИНА VPN

╔═══════════════════════════╗
║   💰 Ожидают проверки    ║
╚═══════════════════════════╝

"""
    for payment in payments:
        pid = payment.get("payment_id")
        tid = payment.get("telegram_id")
        amount = payment.get("amount")
        days = payment.get("tariff_days")
        created = payment.get("created_at", "—")
        text += f"• #{pid} — {amount}₽ ({days} дн.) — {tid}\n"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_payments_list_keyboard(payments))
    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [ADMIN] Админ проверил заявки ({len(payments)} ожидают)")


# ─── /confirm_payment ───────────────────────────────────────────────────────

async def _process_payment_confirmation(
    payment_id: int,
    db: Database,
    xui: XuiClient,
    bot: Bot,
    admin_id: int,
) -> str:
    """
    Внутренняя функция подтверждения платежа.
    Возвращает текст результата в советском стиле.
    """
    payment = await db.get_payment(payment_id)
    if not payment:
        return "❌ Заявка не найдена."

    if payment.get("status") != "pending_confirmation":
        return "❌ Заявка уже обработана."

    telegram_id = payment.get("telegram_id")
    days = payment.get("tariff_days", 30)
    amount = payment.get("amount", 0)

    user = await db.get_user(telegram_id)
    if not user:
        return f"❌ Пользователь {telegram_id} не найден."

    # Создаём клиента в 3x-ui
    client_name = user.get("xui_client_name") or f"user_{telegram_id}_{payment_id}"
    client_data = await xui.create_client(
        client_name=client_name,
        traffic_gb=100,
        expire_days=days,
    )

    if not client_data and not user.get("xui_client_name"):
        return "❌ Ошибка создания клиента в 3x-ui."

    # Активируем подписку
    await db.update_subscription(telegram_id, days=days, client_name=client_name, traffic_gb=100)
    await db.update_payment_status(payment_id, "paid")

    # Уведомляем пользователя в советском стиле
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=f"""
✅ Оплата принята, товарищ!

╔═══════════════════════════╗
║   🛡️ СТАРИНА VPN 🛡️     ║
║  Подписка активирована!  ║
╚═══════════════════════════╝

🏭 Срок: {days} дней
📅 Действует до: смотри в /my_subscription
📊 Трафик: 50 GB
🔑 Статус: ✅ Активна

🏭 Твой трафик под защитой, как на заводе!
""",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        logger.warning(f"Не удалось уведомить пользователя {telegram_id}: {exc}")

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [ADMIN] Админ {admin_id} подтвердил платёж #{payment_id} для {telegram_id} ({amount}₽)")
    return f"✅ Заявка #{payment_id} подтверждена. Подписка активирована."


@router.message(Command("confirm_payment"))
async def confirm_payment_handler(message: Message, db: Database, xui: XuiClient, bot: Bot) -> None:
    """
    Подтверждает заявку на оплату и активирует подписку.
    Формат: /confirm_payment <payment_id>
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            """
🏭 Использование команды:

╔═══════════════════════════╗
║   📋 Справка по команде   ║
╚═══════════════════════════╝

<code>/confirm_payment &lt;payment_id&gt;</code>

🏭 Пример:
<code>/confirm_payment 123</code>

Это подтвердит заявку и активирует подписку.
""",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        payment_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID заявки должен быть числом.")
        return

    result = await _process_payment_confirmation(payment_id, db, xui, bot, message.from_user.id)
    await message.answer(result, parse_mode=ParseMode.MARKDOWN)


# ─── /decline_payment ───────────────────────────────────────────────────────

@router.message(Command("decline_payment"))
async def decline_payment_handler(message: Message, db: Database, bot: Bot) -> None:
    """
    Отклоняет заявку на оплату в советском стиле.
    Формат: /decline_payment <payment_id>
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            """
🏭 Использование команды:

╔═══════════════════════════╗
║   📋 Справка по команде   ║
╚═══════════════════════════╝

<code>/decline_payment &lt;payment_id&gt;</code>

🏭 Пример:
<code>/decline_payment 123</code>

Это отклонит заявку на оплату.
""",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        payment_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID заявки должен быть числом.")
        return

    payment = await db.get_payment(payment_id)
    if not payment:
        await message.answer("❌ Заявка не найдена.")
        return

    if payment.get("status") != "pending_confirmation":
        await message.answer("❌ Заявка уже обработана.")
        return

    telegram_id = payment.get("telegram_id")
    await db.update_payment_status(payment_id, "declined")

    # Уведомляем пользователя в советском стиле
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text="""
❌ Оплата не подтверждена, товарищ!

╔═══════════════════════════╗
║     ❌ Ошибка оплаты     ║
╚═══════════════════════════╝

🏭 Администратор не обнаружил поступления средств.

📋 *Проверь:*
🔹 Баланс на счёте
🔹 Указана ли точная сумма
🔹 Номер карты получателя

💡 Если перевод совершён — обратись в поддержку!
""",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        logger.warning(f"Не удалось уведомить пользователя {telegram_id}: {exc}")

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [ADMIN] Админ {message.from_user.id} отклонил платёж #{payment_id}")
    await message.answer(f"🚫 Заявка #{payment_id} отклонена.", parse_mode=ParseMode.MARKDOWN)


# ─── Callback: admin_confirm_payment ────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_confirm_payment_"))
async def callback_admin_confirm_payment(
    callback: CallbackQuery, db: Database, xui: XuiClient, bot: Bot
) -> None:
    """Подтверждение платежа через инлайн-кнопку в советском стиле."""
    try:
        payment_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("Ошибка заявки.", show_alert=True)
        return

    result = await _process_payment_confirmation(
        payment_id, db, xui, bot, callback.from_user.id
    )
    await callback.message.edit_text(
        f"""
✅ Заявка обработана!

╔═══════════════════════════╗
║   🛡️ СТАРИНА VPN 🛡️      ║
║   ✅ Подтверждено!       ║
╚═══════════════════════════╝

🏭 {result}

<i>Обработано админом @{callback.from_user.username or callback.from_user.id}</i>
""",
        parse_mode=ParseMode.MARKDOWN,
    )
    await callback.answer("✅ Подтверждено")


# ─── Callback: admin_decline_payment ────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_decline_payment_"))
async def callback_admin_decline_payment(
    callback: CallbackQuery, db: Database, bot: Bot
) -> None:
    """Отклонение платежа через инлайн-кнопку в советском стиле."""
    try:
        payment_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("Ошибка заявки.", show_alert=True)
        return

    payment = await db.get_payment(payment_id)
    if not payment or payment.get("status") != "pending_confirmation":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    telegram_id = payment.get("telegram_id")
    await db.update_payment_status(payment_id, "declined")

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text="""
❌ Оплата не подтверждена, товарищ!

╔═══════════════════════════╗
║     ❌ Ошибка оплаты     ║
╚═══════════════════════════╝

🏭 Администратор не обнаружил поступления средств.

📋 *Проверь:*
🔹 Баланс на счёте
🔹 Указана ли точная сумма
🔹 Номер карты получателя

💡 Если перевод совершён — обратись в поддержку!
""",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        logger.warning(f"Не удалось уведомить пользователя {telegram_id}: {exc}")

    logger.info(f"[{datetime.now():%Y-%m-%d %H:%M}] [ADMIN] Админ {callback.from_user.id} отклонил платёж #{payment_id}")
    await callback.message.edit_text(
        f"""
🚫 Заявка #{payment_id} отклонена.

╔═══════════════════════════╗
║   🚫 Отклонено           ║
╚═══════════════════════════╝

<i>Обработано админом @{callback.from_user.username or callback.from_user.id}</i>
""",
        parse_mode=ParseMode.MARKDOWN,
    )
    await callback.answer("🚫 Отклонено")


# ─── Callback: admin_back ───────────────────────────────────────────────────

@router.callback_query(F.data == "admin_back")
async def callback_admin_back(callback: CallbackQuery) -> None:
    """Возврат в админ-меню."""
    await callback.message.edit_text(
        """
🏭 Админ-панель — СТАРИНА VPN

╔═══════════════════════════╗
║   🛡️ СТАРИНА VPN 🛡️      ║
║    Панель управления      ║
╚═══════════════════════════╝

🏭 Добро пожаловать, товарищ администратор!

Выбери действие:
""",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_menu_keyboard()
    )
    await callback.answer()


# ─── Callback: admin_stats ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery, db: Database) -> None:
    """Показывает статистику в советском стиле."""
    all_users = await db.get_all_users()
    active_count = await db.get_active_users_count()
    total_users = len(all_users)
    expired_count = sum(1 for u in all_users if u.get("subscription_status") == "expired")
    
    # Подсчёт платежей
    async with db._connect() as conn:
        conn.row_factory = lambda d, r: r[0]
        async with conn.execute("SELECT COUNT(*) FROM payments WHERE status = 'paid'") as cursor:
            total_payments = (await cursor.fetchone()) or 0
        async with conn.execute("SELECT SUM(amount) FROM payments WHERE status = 'paid'") as cursor:
            total_amount = (await cursor.fetchone()) or 0

    # Статистика серверов
    servers = await db.get_all_servers()
    online_servers = sum(1 for s in servers if s.get("status") == "online")
    offline_servers = sum(1 for s in servers if s.get("status") == "offline")

    text = Msg.ADMIN_STATS.format(
        total_users=total_users,
        active_users=active_count,
        expired_users=expired_count,
        total_servers=len(servers),
        online_servers=online_servers,
        offline_servers=offline_servers,
        total_payments=total_payments,
        total_amount=int(total_amount or 0)
    )

    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_menu_keyboard())
    await callback.answer()


# ─── Callback: admin_users ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery, db: Database) -> None:
    """Показывает список пользователей в советском стиле."""
    all_users = await db.get_all_users()
    
    text = Msg.ADMIN_USERS_LIST.format(count=len(all_users))
    
    for user in all_users[:20]:  # Показываем первых 20
        tid = user.get("telegram_id")
        uname = user.get("username") or "—"
        status = user.get("subscription_status", "—")
        status_emoji = "✅" if status == "active" else "❌" if status == "banned" else "⏳"
        text += f"\n{status_emoji} <code>{tid}</code> (@{uname}) — {status}"

    if len(all_users) > 20:
        text += f"\n\n... и ещё {len(all_users) - 20} пользователей"

    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_users_keyboard())
    await callback.answer()


# ─── Callback: admin_payments ────────────────────────────────────────────────

@router.callback_query(F.data == "admin_payments")
async def callback_admin_payments(callback: CallbackQuery, db: Database) -> None:
    """Показывает список заявок на оплату в советском стиле."""
    payments = await db.get_pending_confirmation_payments()
    
    if not payments:
        await callback.message.edit_text(
            """
💰 Заявки на оплату — СТАРИНА VPN

╔═══════════════════════════╗
║    ✅ Заявок нет 🟢      ║
╚═══════════════════════════╝

🏭 Все заявки обработаны, товарищ!
""",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_menu_keyboard()
        )
    else:
        text = """
💰 Заявки на оплату — СТАРИНА VPN

╔═══════════════════════════╗
║   💰 Ожидают проверки    ║
╚═══════════════════════════╝
"""
        for payment in payments:
            pid = payment.get("payment_id")
            tid = payment.get("telegram_id")
            amount = payment.get("amount")
            days = payment.get("tariff_days")
            text += f"\n⏳ #{pid} — {amount}₽ ({days} дн.) — <code>{tid}</code>"

        await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_payments_list_keyboard(payments))

    await callback.answer()


# ─── Callback: admin_servers ────────────────────────────────────────────────

@router.callback_query(F.data == "admin_servers")
async def callback_admin_servers(callback: CallbackQuery, db: Database) -> None:
    """Показывает список серверов в советском стиле."""
    servers = await db.get_all_servers()
    
    total_clients = sum(s.get("current_clients", 0) for s in servers)
    max_clients = sum(s.get("max_clients", 0) for s in servers)
    percent = int(total_clients / max_clients * 100) if max_clients > 0 else 0
    
    text = Msg.ADMIN_SERVERS.format(
        total_servers=len(servers),
        total_clients=total_clients,
        max_clients=max_clients,
        percent=percent
    )

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=servers_list_keyboard(servers)
    )
    await callback.answer()
