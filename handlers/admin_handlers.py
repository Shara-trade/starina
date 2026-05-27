"""
Обработчики административных команд.

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
from keyboards.inline_keyboards import admin_keyboard, admin_payment_confirmation_keyboard
from middlewares.admin_middleware import AdminMiddleware

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
    Показывает панель администратора.
    """
    text = (
        "<b>🔐 Админ-панель</b>\n\n"
        "Выберите действие:"
    )
    await message.answer(text, reply_markup=admin_keyboard(), parse_mode=ParseMode.HTML)


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
            "<b>Использование:</b>\n"
            "<code>/add_subscription &lt;telegram_id&gt; &lt;days&gt;</code>",
            parse_mode=ParseMode.HTML,
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
        f"✅ Подписка для пользователя <code>{target_id}</code> продлена на <b>{days}</b> дней.",
        parse_mode=ParseMode.HTML,
    )
    logger.info(f"Админ {message.from_user.id} продлил подписку {target_id} на {days} дней.")


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
            "<b>Использование:</b>\n"
            "<code>/ban &lt;telegram_id&gt;</code>",
            parse_mode=ParseMode.HTML,
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
        f"🚫 Пользователь <code>{target_id}</code> заблокирован.",
        parse_mode=ParseMode.HTML,
    )
    logger.info(f"Админ {message.from_user.id} забанил пользователя {target_id}.")


# ─── /payments ──────────────────────────────────────────────────────────────

@router.message(Command("payments"))
async def payments_handler(message: Message, db: Database) -> None:
    """
    Показывает список заявок на подтверждение оплаты.
    Формат: /payments
    """
    payments = await db.get_pending_confirmation_payments()
    if not payments:
        await message.answer("<b>Нет заявок, ожидающих подтверждения.</b>", parse_mode=ParseMode.HTML)
        return

    lines = ["<b>💰 Заявки на подтверждение:</b>\n"]
    for payment in payments:
        pid = payment.get("payment_id")
        tid = payment.get("telegram_id")
        amount = payment.get("amount")
        days = payment.get("tariff_days")
        created = payment.get("created_at", "—")
        lines.append(
            f"• ID: <code>{pid}</code> | User: <code>{tid}</code> | "
            f"{amount}₽ | {days} дн. | {created}"
        )

    text = "\n".join(lines)
    text += "\n\nДля подтверждения: <code>/confirm_payment &lt;id&gt;</code>\n"
    text += "Для отклонения: <code>/decline_payment &lt;id&gt;</code>"

    await message.answer(text, parse_mode=ParseMode.HTML)


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
    Возвращает текст результата.
    """
    payment = await db.get_payment(payment_id)
    if not payment:
        return "❌ Заявка не найдена."

    if payment.get("status") != "pending_confirmation":
        return "❌ Заявка уже обработана."

    telegram_id = payment.get("telegram_id")
    days = payment.get("tariff_days", 30)

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

    # Уведомляем пользователя
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=(
                f"<b>✅ Оплата подтверждена!</b>\n\n"
                f"Ваша подписка активирована на <b>{days}</b> дней.\n"
                f"Нажмите /my_subscription или «Получить конфиг» в меню."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.warning(f"Не удалось уведомить пользователя {telegram_id}: {exc}")

    logger.info(f"Админ {admin_id} подтвердил платёж {payment_id} для {telegram_id}.")
    return f"✅ Заявка <code>{payment_id}</code> подтверждена. Подписка активирована."


@router.message(Command("confirm_payment"))
async def confirm_payment_handler(message: Message, db: Database, xui: XuiClient, bot: Bot) -> None:
    """
    Подтверждает заявку на оплату и активирует подписку.
    Формат: /confirm_payment <payment_id>
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "<b>Использование:</b>\n<code>/confirm_payment &lt;payment_id&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        payment_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID заявки должен быть числом.")
        return

    result = await _process_payment_confirmation(payment_id, db, xui, bot, message.from_user.id)
    await message.answer(result, parse_mode=ParseMode.HTML)


# ─── /decline_payment ───────────────────────────────────────────────────────

@router.message(Command("decline_payment"))
async def decline_payment_handler(message: Message, db: Database, bot: Bot) -> None:
    """
    Отклоняет заявку на оплату.
    Формат: /decline_payment <payment_id>
    """
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "<b>Использование:</b>\n<code>/decline_payment &lt;payment_id&gt;</code>",
            parse_mode=ParseMode.HTML,
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

    # Уведомляем пользователя
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=(
                "<b>❌ Оплата не подтверждена</b>\n\n"
                "Администратор не обнаружил поступления средств.\n"
                "Если вы совершили перевод, обратитесь в поддержку."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.warning(f"Не удалось уведомить пользователя {telegram_id}: {exc}")

    logger.info(f"Админ {message.from_user.id} отклонил платёж {payment_id}.")
    await message.answer(f"🚫 Заявка <code>{payment_id}</code> отклонена.", parse_mode=ParseMode.HTML)


# ─── Callback: admin_confirm_payment ────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_confirm_payment_"))
async def callback_admin_confirm_payment(
    callback: CallbackQuery, db: Database, xui: XuiClient, bot: Bot
) -> None:
    """Подтверждение платежа через инлайн-кнопку."""
    try:
        payment_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("Ошибка заявки.", show_alert=True)
        return

    result = await _process_payment_confirmation(
        payment_id, db, xui, bot, callback.from_user.id
    )
    await callback.message.edit_text(
        f"{result}\n\n<i>Обработано админом {callback.from_user.id}</i>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Подтверждено")


# ─── Callback: admin_decline_payment ────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_decline_payment_"))
async def callback_admin_decline_payment(
    callback: CallbackQuery, db: Database, bot: Bot
) -> None:
    """Отклонение платежа через инлайн-кнопку."""
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
            text=(
                "<b>❌ Оплата не подтверждена</b>\n\n"
                "Администратор не обнаружил поступления средств.\n"
                "Если вы совершили перевод, обратитесь в поддержку."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.warning(f"Не удалось уведомить пользователя {telegram_id}: {exc}")

    logger.info(f"Админ {callback.from_user.id} отклонил платёж {payment_id}.")
    await callback.message.edit_text(
        f"🚫 Заявка <code>{payment_id}</code> отклонена.\n\n"
        f"<i>Обработано админом {callback.from_user.id}</i>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Отклонено")


# ─── Callback: admin_stats ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery, db: Database) -> None:
    """Показывает статистику по пользователям."""
    all_users = await db.get_all_users()
    active_count = await db.get_active_users_count()
    total_users = len(all_users)
    expired_count = sum(1 for u in all_users if u.get("subscription_status") == "expired")

    # Подсчёт "дохода" — сумма всех подтверждённых платежей
    # Для простоты считаем по фиксированным ценам или можно доработать
    text = (
        f"<b>📊 Статистика</b>\n\n"
        f"Всего пользователей: <b>{total_users}</b>\n"
        f"Активных подписок: <b>{active_count}</b>\n"
        f"Истекших подписок: <b>{expired_count}</b>\n"
    )

    await callback.message.edit_text(text, reply_markup=admin_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer()


# ─── Callback: admin_users ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery, db: Database) -> None:
    """Показывает список пользователей (первые 10)."""
    all_users = await db.get_all_users()
    lines = ["<b>👥 Последние пользователи:</b>\n"]

    for user in all_users[:10]:
        tid = user.get("telegram_id")
        uname = user.get("username") or "—"
        status = user.get("subscription_status", "—")
        lines.append(f"• <code>{tid}</code> (@{uname}) — {status}")

    text = "\n".join(lines) if len(lines) > 1 else "Пользователей пока нет."

    await callback.message.edit_text(text, reply_markup=admin_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer()
