"""
Обработчики пользовательских команд и callback'ов.

Команды:
    /start      — регистрация пользователя
    /buy        — покупка подписки
    /my_subscription — информация о текущей подписке
    /help       — справка
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
    admin_payment_confirmation_keyboard,
)

import config

logger = logging.getLogger(__name__)
router = Router()

# ─── /start ─────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def start_handler(message: Message, db: Database) -> None:
    """
    Обработчик команды /start.
    Регистрирует пользователя в БД и показывает главное меню.
    """
    telegram_id = message.from_user.id
    username = message.from_user.username

    # Проверяем наличие реферального параметра (например /start ref123456)
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
        text = (
            f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
            f"Добро пожаловать в VPN-сервис.\n"
            f"Выберите действие ниже:"
        )
    else:
        text = (
            f"С возвращением, <b>{message.from_user.full_name}</b>!\n\n"
            f"Выберите действие:"
        )

    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)


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
    """Показывает меню покупки подписки."""
    text = (
        "<b>🛒 Выберите тариф:</b>\n\n"
        "• 1 месяц — 299₽\n"
        "• 3 месяца — 799₽\n"
        "• 6 месяцев — 1499₽"
    )
    await callback.message.edit_text(text, reply_markup=buy_subscription_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer()


# ─── Callback: my_subscription ──────────────────────────────────────────────

@router.callback_query(F.data == "my_subscription")
async def callback_my_subscription(callback: CallbackQuery, db: Database) -> None:
    """Показывает информацию о подписке через callback."""
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)

    if not user:
        await callback.message.edit_text("Сначала зарегистрируйтесь: /start")
        await callback.answer()
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

    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer()


# ─── Callback: buy_X_Y (выбор тарифа) ───────────────────────────────────────

@router.callback_query(F.data.startswith("buy_"))
async def callback_buy_select(callback: CallbackQuery, db: Database) -> None:
    """
    Обрабатывает выбор тарифа.
    Показывает реквизиты Т-Банка для ручного перевода.
    Формат callback_data: buy_<days>_<price>
    """
    try:
        _, days_str, price_str = callback.data.split("_")
        days = int(days_str)
        price = int(price_str)
    except ValueError:
        await callback.answer("Ошибка выбора тарифа.", show_alert=True)
        return

    telegram_id = callback.from_user.id

    # Создаём запись о платеже
    payment_id = await db.add_payment(
        telegram_id=telegram_id,
        amount=float(price),
        tariff_days=days,
        currency="RUB",
        provider="t_bank",
    )

    text = (
        f"<b>🛒 Выбран тариф: {days} дней</b>\n"
        f"Сумма к оплате: <b>{price}₽</b>\n\n"
        f"<b>💳 Реквизиты для перевода в Т-Банк:</b>\n"
        f"Получатель: <b>{config.T_BANK_CARDHOLDER}</b>\n"
        f"Номер карты: <code>{config.T_BANK_CARD}</code>\n"
        f"Телефон: <code>{config.T_BANK_PHONE}</code>\n\n"
        f"1️⃣ Переведите <b>точную сумму {price}₽</b> через приложение Т-Банка\n"
        f"2️⃣ После перевода нажмите кнопку <b>«✅ Я оплатил»</b>\n\n"
        f"<i>Администратор проверит поступление и активирует подписку вручную.</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=t_bank_payment_keyboard(str(payment_id)),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ─── Callback: get_config ───────────────────────────────────────────────────

@router.callback_query(F.data == "get_config")
async def callback_get_config(callback: CallbackQuery, db: Database, xui: XuiClient) -> None:
    """
    Отправляет пользователю v2ray:// конфигурацию.
    """
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)

    if not user or user.get("subscription_status") != "active":
        await callback.answer("У вас нет активной подписки!", show_alert=True)
        return

    client_name = user.get("xui_client_name")
    if not client_name:
        await callback.answer("Клиент не найден. Обратитесь в поддержку.", show_alert=True)
        return

    # Запрашиваем конфиг у 3x-ui
    config_link = await xui.generate_v2ray_config(client_name, protocol="vless")

    if not config_link:
        await callback.answer("Ошибка генерации конфига. Попробуйте позже.", show_alert=True)
        return

    text = (
        f"<b>⚙️ Ваша конфигурация v2RayTun</b>\n\n"
        f"<code>{config_link}</code>\n\n"
        f"Нажмите на ссылку выше, чтобы скопировать, "
        f"или импортируйте напрямую в приложение v2RayTun."
    )

    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer()


# ─── Callback: back_to_main ─────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery) -> None:
    """Возвращает в главное меню."""
    text = f"С возвращением, <b>{callback.from_user.full_name}</b>!\n\nВыберите действие:"
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer()


# ─── Callback: help ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery) -> None:
    """Показывает справку через callback."""
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
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
    await callback.answer()


# ─── Callback: i_paid (пользователь нажал "Я оплатил") ──────────────────────

@router.callback_query(F.data.startswith("i_paid_"))
async def callback_i_paid(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    """
    Пользователь подтверждает, что совершил перевод.
    Меняем статус заявки и отправляем уведомление админам.
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

    # Отвечаем пользователю
    await callback.message.edit_text(
        "<b>⏳ Заявка отправлена на проверку</b>\n\n"
        "Администратор проверит поступление средств и активирует подписку.\n"
        "Обычно это занимает от нескольких минут до часа.\n\n"
        "Вы получите уведомление, когда всё будет готово.",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()

    # Уведомляем всех админов
    user = await db.get_user(telegram_id)
    username = user.get("username") or "—" if user else "—"
    amount = payment.get("amount", 0)
    days = payment.get("tariff_days", 0)

    admin_text = (
        f"<b>💰 Новая заявка на оплату!</b>\n\n"
        f"Пользователь: <code>{telegram_id}</code> (@{username})\n"
        f"Сумма: <b>{amount}₽</b>\n"
        f"Тариф: <b>{days} дней</b>\n"
        f"ID заявки: <code>{payment_id}</code>\n\n"
        f"Проверьте поступление средств на Т-Банк и подтвердите."
    )

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_payment_confirmation_keyboard(str(payment_id)),
                parse_mode=ParseMode.HTML,
            )
        except Exception as exc:
            logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {exc}")
