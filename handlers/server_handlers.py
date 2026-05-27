"""
Обработчики команд управления серверами (3x-ui).

FSM-based мультишаговая система для добавления/редактирования серверов.
Доступно только администраторам.
"""

import json
import logging
from typing import Dict, Any

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputFile
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State

from database import Database
from keyboards.inline_keyboards import (
    servers_list_keyboard,
    server_detail_keyboard,
    confirm_add_keyboard,
    confirm_yes_no_keyboard,
    cancel_keyboard,
    back_cancel_keyboard,
    edit_field_keyboard,
    retry_edit_cancel_keyboard,
    retry_cancel_keyboard,
)
from services.server_service import ServerService
from states import ServerAddState, ServerEditState
from middlewares.admin_middleware import AdminMiddleware

logger = logging.getLogger(__name__)
router = Router()

# Применяем AdminMiddleware
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_flag(location: str, name: str = "") -> str:
    """Возвращает эмодзи-флаг по локации/имени."""
    loc_lower = location.lower()
    name_lower = name.lower()
    if "герм" in loc_lower or "germany" in loc_lower or "frankfurt" in loc_lower or "de," in loc_lower:
        return "🇩🇪"
    if "usa" in loc_lower or "us-" in name_lower or "america" in loc_lower or "соединен" in loc_lower:
        return "🇺🇸"
    if "netherlands" in loc_lower or "neth" in loc_lower or "amsterdam" in loc_lower or "голланд" in loc_lower:
        return "🇳🇱"
    if "франц" in loc_lower or "france" in loc_lower or "paris" in loc_lower:
        return "🇫🇷"
    if "англ" in loc_lower or "uk" in loc_lower or "london" in loc_lower or "британия" in loc_lower:
        return "🇬🇧"
    if "швейц" in loc_lower or "switzerland" in loc_lower or "zurich" in loc_lower:
        return "🇨🇭"
    if "япон" in loc_lower or "japan" in loc_lower or "tokyo" in loc_lower:
        return "🇯🇵"
    if "сингап" in loc_lower or "singapore" in loc_lower:
        return "🇸🇬"
    if "австрал" in loc_lower or "australia" in loc_lower:
        return "🇦🇺"
    if "канад" in loc_lower or "canada" in loc_lower:
        return "🇨🇦"
    if "швец" in loc_lower or "sweden" in loc_lower:
        return "🇸🇪"
    if "финлянд" in loc_lower or "finland" in loc_lower:
        return "🇫🇮"
    if "норвеж" in loc_lower or "norway" in loc_lower:
        return "🇳🇴"
    if "польш" in loc_lower or "poland" in loc_lower:
        return "🇵🇱"
    if "испан" in loc_lower or "spain" in loc_lower:
        return "🇪🇸"
    if "итали" in loc_lower or "italy" in loc_lower:
        return "🇮🇹"
    if "турци" in loc_lower or "turkey" in loc_lower:
        return "🇹🇷"
    if "дубай" in loc_lower or "uae" in loc_lower:
        return "🇦🇪"
    return "🌍"


# ─── /servers ────────────────────────────────────────────────────────────────

@router.message(Command("servers"))
async def cmd_servers(message: Message, db: Database) -> None:
    """Показывает список всех серверов."""
    servers = await db.get_all_servers()
    if not servers:
        text = (
            "🖥 <b>Управление серверами</b>\n\n"
            "Серверов пока нет.\n"
            "Используйте /add_server для добавления первого сервера."
        )
        await message.answer(text, reply_markup=servers_list_keyboard([]), parse_mode=ParseMode.HTML)
        return

    text = f"🖥 <b>Управление серверами</b> — {len(servers)} сервер(ов)\n\nВыберите сервер для просмотра:"
    await message.answer(text, reply_markup=servers_list_keyboard(servers), parse_mode=ParseMode.HTML)


# ─── /add_server ─────────────────────────────────────────────────────────────

@router.message(Command("add_server"))
async def cmd_add_server(message: Message, state: FSMContext) -> None:
    """Начинает мультишаговый диалог добавления сервера (шаг 1/8)."""
    text = (
        "🔧 <b>Добавление нового сервера</b>\n\n"
        "📝 <i>Шаг 1/8:</i> Введите имя сервера\n"
        "Пример: <code>Germany-1</code>, <code>US-North</code>, <code>NL-Amsterdam</code>\n\n"
        "Ответьте в этом же чате."
    )
    await message.answer(text, reply_markup=cancel_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.name)


# ─── FSM: Шаг 1 — Имя ───────────────────────────────────────────────────────

@router.message(ServerAddState.name)
async def fsm_add_name(message: Message, state: FSMContext) -> None:
    """Принимает имя сервера и переходит к шагу 2."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "⚠️ Имя слишком короткое (минимум 2 символа). Попробуйте снова:",
            reply_markup=cancel_keyboard(),
        )
        return

    if len(name) > 50:
        await message.answer(
            "⚠️ Имя слишком длинное (максимум 50 символов). Попробуйте снова:",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(name=name)

    text = (
        f"✅ Имя: <b>{name}</b>\n\n"
        "📝 <i>Шаг 2/8:</i> Введите URL панели 3x-ui\n"
        "Пример: <code>https://panel.myvpn.com</code>\n\n"
        "<i>Важно: URL должен начинаться с https://</i>"
    )
    await message.answer(text, reply_markup=back_cancel_keyboard("name"), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.url)


# ─── FSM: Шаг 2 — URL ───────────────────────────────────────────────────────

@router.message(ServerAddState.url)
async def fsm_add_url(message: Message, state: FSMContext) -> None:
    """Принимает URL и переходит к шагу 3."""
    url = message.text.strip()

    if not url.startswith(("http://", "https://")):
        await message.answer(
            "⚠️ URL должен начинаться с <code>http://</code> или <code>https://</code>\n"
            "Попробуйте снова:",
            reply_markup=back_cancel_keyboard("url"),
            parse_mode=ParseMode.HTML,
        )
        return

    await state.update_data(url=url)

    data = await state.get_data()
    text = (
        f"✅ Имя: <b>{data.get('name')}</b>\n"
        f"✅ URL: <code>{url}</code>\n\n"
        "📝 <i>Шаг 3/8:</i> Введите логин от панели 3x-ui\n"
        "Пример: <code>admin</code>"
    )
    await message.answer(text, reply_markup=back_cancel_keyboard("url"), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.username)


# ─── FSM: Шаг 3 — Username ──────────────────────────────────────────────────

@router.message(ServerAddState.username)
async def fsm_add_username(message: Message, state: FSMContext) -> None:
    """Принимает логин и переходит к шагу 4."""
    username = message.text.strip()

    if len(username) < 1:
        await message.answer(
            "⚠️ Логин не может быть пустым. Попробуйте снова:",
            reply_markup=back_cancel_keyboard("username"),
        )
        return

    await state.update_data(username=username)

    data = await state.get_data()
    text = (
        f"✅ Имя: <b>{data.get('name')}</b>\n"
        f"✅ URL: <code>{data.get('url')}</code>\n"
        f"✅ Логин: <code>{username}</code>\n\n"
        "📝 <i>Шаг 4/8:</i> Введите пароль от панели 3x-ui"
    )
    await message.answer(text, reply_markup=back_cancel_keyboard("username"), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.password)


# ─── FSM: Шаг 4 — Password ──────────────────────────────────────────────────

@router.message(ServerAddState.password)
async def fsm_add_password(message: Message, state: FSMContext) -> None:
    """Принимает пароль и переходит к шагу 5."""
    password = message.text.strip()

    if len(password) < 1:
        await message.answer(
            "⚠️ Пароль не может быть пустым. Попробуйте снова:",
            reply_markup=back_cancel_keyboard("password"),
        )
        return

    await state.update_data(password=password)

    data = await state.get_data()
    text = (
        f"✅ Имя: <b>{data.get('name')}</b>\n"
        f"✅ URL: <code>{data.get('url')}</code>\n"
        f"✅ Логин: <code>{data.get('username')}</code>\n"
        f"✅ Пароль: <code>{'•' * min(len(password), 12)}</code>\n\n"
        "📝 <i>Шаг 5/8:</i> Введите локацию (страна/город)\n"
        "Пример: <code>ФРГ, Франкфурт</code> или <code>Germany, Frankfurt</code>"
    )
    await message.answer(text, reply_markup=back_cancel_keyboard("password"), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.location)


# ─── FSM: Шаг 5 — Location ──────────────────────────────────────────────────

@router.message(ServerAddState.location)
async def fsm_add_location(message: Message, state: FSMContext) -> None:
    """Принимает локацию и переходит к шагу 6."""
    location = message.text.strip()

    if len(location) < 2:
        await message.answer(
            "⚠️ Локация слишком короткая. Попробуйте снова:",
            reply_markup=back_cancel_keyboard("location"),
        )
        return

    await state.update_data(location=location)

    data = await state.get_data()
    text = (
        f"✅ Имя: <b>{data.get('name')}</b>\n"
        f"✅ URL: <code>{data.get('url')}</code>\n"
        f"✅ Логин: <code>{data.get('username')}</code>\n"
        f"✅ Локация: <b>{location}</b>\n\n"
        "📝 <i>Шаг 6/8:</i> Введите общий лимит трафика (ГБ)\n"
        "Пример: <code>500</code> (500 ГБ)"
    )
    await message.answer(text, reply_markup=back_cancel_keyboard("location"), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.traffic_limit_gb)


# ─── FSM: Шаг 6 — Traffic Limit ────────────────────────────────────────────

@router.message(ServerAddState.traffic_limit_gb)
async def fsm_add_traffic(message: Message, state: FSMContext) -> None:
    """Принимает лимит трафика и переходит к шагу 7."""
    text_raw = message.text.strip()

    try:
        traffic_gb = int(text_raw)
        if traffic_gb < 1:
            raise ValueError("Must be > 0")
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Введите целое число (например: <code>500</code>)\n"
            "Не пишите словами, только цифры!",
            reply_markup=back_cancel_keyboard("traffic"),
            parse_mode=ParseMode.HTML,
        )
        return

    await state.update_data(traffic_limit_gb=traffic_gb)

    data = await state.get_data()
    text = (
        f"✅ Имя: <b>{data.get('name')}</b>\n"
        f"✅ URL: <code>{data.get('url')}</code>\n"
        f"✅ Логин: <code>{data.get('username')}</code>\n"
        f"✅ Локация: <b>{data.get('location')}</b>\n"
        f"✅ Лимит трафика: <b>{traffic_gb} ГБ</b>\n\n"
        "📝 <i>Шаг 7/8:</i> Введите максимальное количество клиентов\n"
        "Пример: <code>100</code>"
    )
    await message.answer(text, reply_markup=back_cancel_keyboard("traffic"), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.max_clients)


# ─── FSM: Шаг 7 — Max Clients ──────────────────────────────────────────────

@router.message(ServerAddState.max_clients)
async def fsm_add_max_clients(message: Message, state: FSMContext) -> None:
    """Принимает макс. клиентов и переходит к шагу 8 (подтверждение)."""
    text_raw = message.text.strip()

    try:
        max_clients = int(text_raw)
        if max_clients < 1:
            raise ValueError("Must be > 0")
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Введите целое число (например: <code>100</code>)\n"
            "Не пишите словами, только цифры!",
            reply_markup=back_cancel_keyboard("max_clients"),
            parse_mode=ParseMode.HTML,
        )
        return

    await state.update_data(max_clients=max_clients)

    data = await state.get_data()
    text = (
        "📋 <b>Проверьте данные перед добавлением:</b>\n\n"
        f"🏷 <b>Имя:</b> {data.get('name')}\n"
        f"🔗 <b>URL:</b> <code>{data.get('url')}</code>\n"
        f"👤 <b>Логин:</b> <code>{data.get('username')}</code>\n"
        f"🔒 <b>Пароль:</b> <code>{'•' * 12}</code>\n"
        f"📍 <b>Локация:</b> {data.get('location')}\n"
        f"📊 <b>Лимит трафика:</b> {data.get('traffic_limit_gb')} ГБ\n"
        f"👥 <b>Макс. клиентов:</b> {max_clients}\n\n"
        "⚠️ Бот проверит подключение к серверу перед добавлением."
    )
    await message.answer(
        text,
        reply_markup=confirm_add_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(ServerAddState.confirm)


# ─── FSM: Шаг 8 — Confirm ───────────────────────────────────────────────────

@router.callback_query(F.data == "confirm_add_yes", ServerAddState.confirm)
async def fsm_confirm_add_yes(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Подтверждение — добавляет сервер в БД."""
    await callback.answer()
    data = await state.get_data()

    service = ServerService(db)
    result = await service.add_server(
        name=data["name"],
        url=data["url"],
        username=data["username"],
        password=data["password"],
        location=data["location"],
        traffic_limit_gb=int(data["traffic_limit_gb"]),
        max_clients=int(data["max_clients"]),
        created_by=callback.from_user.id,
    )

    if result["success"]:
        srv_id = result["server_id"]
        flag = _get_flag(data["location"], data["name"])
        text = (
            "✅ <b>Сервер успешно добавлен!</b>\n\n"
            f"📊 <b>ID сервера:</b> {srv_id}\n"
            f"🌍 <b>Название:</b> {flag} {data['name']}\n"
            f"📍 <b>Локация:</b> {data['location']}\n"
            f"👥 <b>Клиентов:</b> 0/{data['max_clients']}\n"
            f"📊 <b>Трафик:</b> 0/{data['traffic_limit_gb']} GB\n"
            f"🟢 <b>Статус:</b> Онлайн\n\n"
            "Сервер активен и готов к работе!"
        )
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
        logger.info(f"Админ {callback.from_user.id} добавил сервер {srv_id}")
    else:
        text = (
            f"❌ <b>Ошибка добавления сервера</b>\n\n"
            f"Причина: {result['message']}\n\n"
            "Проверьте данные и попробуйте снова: /add_server"
        )
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML)

    await state.clear()


@router.callback_query(F.data == "confirm_add_edit", ServerAddState.confirm)
async def fsm_confirm_add_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет изменить данные — начинаем заново."""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "✏️ Добавление отменено. Введите /add_server для начала заново.",
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "confirm_add_cancel", ServerAddState.confirm)
async def fsm_confirm_add_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена добавления сервера."""
    await callback.answer("❌ Отменено")
    await state.clear()
    await callback.message.edit_text("❌ Добавление сервера отменено.", parse_mode=ParseMode.HTML)


# ─── Back / Cancel FSM ───────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_fsm")
async def callback_cancel_fsm(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена текущей FSM операции."""
    current_state = await state.get_state()
    if current_state is None:
        await callback.answer("Нет активной операции")
        return

    await state.clear()
    await callback.answer("❌ Отменено")
    await callback.message.edit_text("❌ Операция отменена.", parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("back_"))
async def callback_back_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к предыдущему шагу."""
    step = callback.data.split("_")[1]

    step_map: Dict[str, State] = {
        "name": ServerAddState.name,
        "url": ServerAddState.url,
        "username": ServerAddState.username,
        "password": ServerAddState.password,
        "location": ServerAddState.location,
        "traffic": ServerAddState.traffic_limit_gb,
        "max_clients": ServerAddState.max_clients,
    }

    if step in step_map:
        await state.set_state(step_map[step])
        await callback.answer()
        step_names: Dict[str, str] = {
            "name": "1/8: Имя сервера",
            "url": "2/8: URL панели",
            "username": "3/8: Логин",
            "password": "4/8: Пароль",
            "location": "5/8: Локация",
            "traffic": "6/8: Лимит трафика",
            "max_clients": "7/8: Макс. клиентов",
        }
        await callback.message.edit_text(
            f"⬅️ Назад к шагу {step_names[step]}\nВведите значение заново:",
            parse_mode=ParseMode.HTML,
        )
    else:
        await callback.answer("Неизвестный шаг")


# ─── Server List Refresh ─────────────────────────────────────────────────────

@router.callback_query(F.data == "servers_refresh")
async def callback_servers_refresh(callback: CallbackQuery, db: Database) -> None:
    """Обновление списка серверов."""
    servers = await db.get_all_servers()
    text = f"🖥 <b>Управление серверами</b> — {len(servers)} сервер(ов)\n\nВыберите сервер:"
    await callback.message.edit_text(text, reply_markup=servers_list_keyboard(servers), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "servers_close")
async def callback_servers_close(callback: CallbackQuery) -> None:
    """Закрытие меню серверов."""
    await callback.message.delete()
    await callback.answer()


# ─── Server Detail ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("server_detail_"))
async def callback_server_detail(callback: CallbackQuery, db: Database) -> None:
    """Показывает детальную информацию о сервере."""
    try:
        server_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID сервера", show_alert=True)
        return

    service = ServerService(db)
    stats = await service.get_server_stats(server_id)

    if not stats.get("server"):
        await callback.answer("Сервер не найден", show_alert=True)
        return

    srv = stats["server"]
    flag = _get_flag(srv.get("location", ""), srv.get("name", ""))
    status_emoji = "🟢" if srv.get("status") == "online" else "🔴" if srv.get("status") == "offline" else "🟡"
    active_text = "Активен ✅" if srv.get("is_active") else "Деактивирован ❌"

    text = (
        f"{flag} <b>{srv.get('name')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> {srv['id']}\n"
        f"🔗 <b>URL:</b> <code>{srv['url']}</code>\n"
        f"📍 <b>Локация:</b> {srv.get('location')}\n"
        f"👥 <b>Клиенты:</b> {srv.get('current_clients', 0)}/{srv.get('max_clients')} "
        f"({stats.get('client_percent', 0):.1f}%)\n"
        f"📊 <b>Трафик:</b> {srv.get('traffic_used_gb', 0):.1f}/{srv.get('traffic_limit_gb')} GB "
        f"({stats.get('traffic_percent', 0):.1f}%)\n"
        f"⚙️ <b>Вес балансировки:</b> {srv.get('balance_weight', 1)}\n"
        f"🔴 <b>Статус:</b> {status_emoji} {srv.get('status', 'offline').capitalize()}\n"
        f"📌 <b>{active_text}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕐 <b>Последняя проверка:</b> {srv.get('last_checked') or '—'}\n"
        f"📅 <b>Добавлен:</b> {srv.get('created_at')}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=server_detail_keyboard(server_id, bool(srv.get("is_active"))),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# ─── Add Server Button ───────────────────────────────────────────────────────

@router.callback_query(F.data == "server_add")
async def callback_server_add(callback: CallbackQuery, state: FSMContext) -> None:
    """Кнопка 'Добавить сервер' в списке."""
    await callback.answer()

    # Отменяем любую активную FSM
    await state.clear()

    text = (
        "🔧 <b>Добавление нового сервера</b>\n\n"
        "📝 <i>Шаг 1/8:</i> Введите имя сервера\n"
        "Пример: <code>Germany-1</code>, <code>US-North</code>, <code>NL-Amsterdam</code>\n\n"
        "Ответьте в этом же чате."
    )
    await callback.message.answer(text, reply_markup=cancel_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(ServerAddState.name)


# ─── Toggle Server Active ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("server_toggle_"))
async def callback_server_toggle(callback: CallbackQuery, db: Database) -> None:
    """Активация/деактивация сервера."""
    try:
        server_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID", show_alert=True)
        return

    service = ServerService(db)
    result = await service.toggle_server_active(server_id)

    if result["success"]:
        is_active = result.get("is_active", True)
        await callback.answer(f"✅ {'Активирован' if is_active else 'Деактивирован'}")
        # Обновляем сообщение с деталями
        await callback_server_detail(callback, db)
    else:
        await callback.answer(f"❌ {result['message']}", show_alert=True)


# ─── Remove Server ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("server_remove_"))
async def callback_server_remove(callback: CallbackQuery, db: Database) -> None:
    """Запрос подтверждения удаления сервера."""
    try:
        server_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID", show_alert=True)
        return

    server = await db.get_server(server_id)
    if not server:
        await callback.answer("Сервер не найден", show_alert=True)
        return

    current_clients = server.get("current_clients", 0)
    if current_clients > 0:
        await callback.answer(
            f"❌ На сервере {current_clients} клиентов! Сначала удалите клиентов.",
            show_alert=True,
        )
        return

    text = (
        f"⚠️ <b>Подтвердите удаление сервера</b>\n\n"
        f"Вы уверены, что хотите удалить сервер <b>{server['name']}</b> (ID: {server_id})?\n\n"
        "❗ Это действие нельзя отменить!"
    )
    await callback.message.edit_text(
        text,
        reply_markup=confirm_yes_no_keyboard(
            f"remove_confirm_{server_id}",
            f"server_detail_{server_id}",
        ),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_confirm_"))
async def callback_remove_confirm(callback: CallbackQuery, db: Database) -> None:
    """Подтверждение удаления сервера."""
    try:
        server_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID", show_alert=True)
        return

    service = ServerService(db)
    result = await service.remove_server(server_id)

    if result["success"]:
        await callback.answer("✅ Сервер удалён")
        # Возвращаемся к списку
        servers = await db.get_all_servers()
        text = f"🖥 <b>Управление серверами</b> — {len(servers)} сервер(ов)\n\nВыберите сервер:"
        await callback.message.edit_text(text, reply_markup=servers_list_keyboard(servers), parse_mode=ParseMode.HTML)
    else:
        await callback.answer(f"❌ {result['message']}", show_alert=True)


# ─── Edit Server ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("server_edit_"))
async def callback_server_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования сервера — выбор поля."""
    try:
        server_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID", show_alert=True)
        return

    await state.update_data(edit_server_id=server_id)
    await state.set_state(ServerEditState.edit_field)

    text = (
        f"✏️ <b>Редактирование сервера</b>\n\n"
        "Выберите поле для редактирования:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=edit_field_keyboard(server_id),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field_"))
async def callback_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор конкретного поля для редактирования."""
    parts = callback.data.split("_")
    try:
        server_id = int(parts[2])
        field = parts[3]
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных", show_alert=True)
        return

    field_names: Dict[str, str] = {
        "name": "Имя сервера",
        "url": "URL панели",
        "username": "Логин",
        "password": "Пароль",
        "location": "Локация",
        "traffic_limit_gb": "Лимит трафика (ГБ)",
        "max_clients": "Макс. клиентов",
        "balance_weight": "Вес балансировки",
    }

    field_examples: Dict[str, str] = {
        "name": "Germany-1",
        "url": "https://panel.myvpn.com",
        "username": "admin",
        "password": "новый_пароль",
        "location": "ФРГ, Франкфурт",
        "traffic_limit_gb": "500",
        "max_clients": "100",
        "balance_weight": "2",
    }

    await state.update_data(edit_field=field, edit_server_id=server_id)
    await state.set_state(ServerEditState.new_value)

    field_name = field_names.get(field, field)
    example = field_examples.get(field, "")

    text = (
        f"✏️ <b>Редактирование поля:</b> {field_name}\n\n"
        f"Введите новое значение:\n"
        f"{f'Пример: <code>{example}</code>' if example else ''}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=back_cancel_keyboard(f"field_{field}"),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message(ServerEditState.new_value)
async def fsm_edit_new_value(message: Message, state: FSMContext, db: Database) -> None:
    """Получение нового значения для редактируемого поля."""
    data = await state.get_data()
    field = data.get("edit_field")
    server_id = data.get("edit_server_id")
    new_value = message.text.strip()

    # Валидация
    if field in ("traffic_limit_gb", "max_clients", "balance_weight"):
        try:
            int(new_value)
        except ValueError:
            await message.answer(
                "⚠️ Неверный формат. Введите целое число:",
                reply_markup=back_cancel_keyboard(f"field_{field}"),
                parse_mode=ParseMode.HTML,
            )
            return

    service = ServerService(db)
    result = await service.edit_server_field(server_id, field, new_value)

    if result["success"]:
        await message.answer(f"✅ {result['message']}", parse_mode=ParseMode.HTML)
        # Показываем детали сервера
        stats = await service.get_server_stats(server_id)
        srv = stats["server"]
        if srv:
            flag = _get_flag(srv.get("location", ""), srv.get("name", ""))
            status_emoji = "🟢" if srv.get("status") == "online" else "🔴"
            text = (
                f"{flag} <b>{srv['name']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 <b>ID:</b> {srv['id']}\n"
                f"🔗 <b>URL:</b> <code>{srv['url']}</code>\n"
                f"📍 <b>Локация:</b> {srv.get('location')}\n"
                f"👥 <b>Клиенты:</b> {srv.get('current_clients', 0)}/{srv.get('max_clients')}\n"
                f"📊 <b>Трафик:</b> {srv.get('traffic_used_gb', 0):.1f}/{srv.get('traffic_limit_gb')} GB\n"
                f"🔴 <b>Статус:</b> {status_emoji} {srv.get('status', 'offline').capitalize()}"
            )
            await message.answer(
                text,
                reply_markup=server_detail_keyboard(server_id, bool(srv.get("is_active"))),
                parse_mode=ParseMode.HTML,
            )
    else:
        await message.answer(f"❌ {result['message']}", parse_mode=ParseMode.HTML)

    await state.clear()


# ─── Test Server ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("server_test_"))
async def callback_server_test(callback: CallbackQuery, db: Database) -> None:
    """Проверка подключения к серверу."""
    try:
        server_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID", show_alert=True)
        return

    await callback.answer("⏳ Проверка...")
    await callback.message.edit_text("🔄 Проверка подключения к серверу...")

    service = ServerService(db)
    stats = await service.get_server_stats(server_id)

    srv = stats.get("server")
    if not srv:
        await callback.message.edit_text("❌ Сервер не найден.")
        return

    conn = stats.get("connection_test", {})
    status_emoji = "✅" if conn.get("success") else "❌"
    status_text = "Онлайн" if conn.get("success") else "Оффлайн"

    text = (
        f"{status_emoji} <b>Результат проверки:</b>\n\n"
        f"🌍 Сервер: <b>{srv['name']}</b>\n"
        f"🔗 URL: <code>{srv['url']}</code>\n"
        f"📊 Статус: <b>{status_text}</b>\n"
        f"💬 Сообщение: {conn.get('message', '—')}\n"
        f"📡 Inbounds: {conn.get('inbounds_count', '?')}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=server_detail_keyboard(server_id, bool(srv.get("is_active"))),
        parse_mode=ParseMode.HTML,
    )


# ─── Bulk commands ───────────────────────────────────────────────────────────

@router.message(Command("test_all_servers"))
async def cmd_test_all_servers(message: Message, db: Database) -> None:
    """Проверка всех серверов."""
    await message.answer("🔄 Проверяю все серверы...")

    service = ServerService(db)
    results = await service.test_all_servers()

    if not results:
        await message.answer("❌ Серверов нет.")
        return

    online = sum(1 for r in results if r["status"] == "online")
    offline = sum(1 for r in results if r["status"] == "offline")

    lines = [f"🔍 <b>Результаты проверки ({len(results)} серверов)</b>\n"]
    lines.append(f"🟢 Онлайн: {online} | 🔴 Оффлайн: {offline}\n")

    for r in results:
        emoji = "🟢" if r["status"] == "online" else "🔴"
        lines.append(f"{emoji} <b>{r['name']}</b>: {r['message']}")

    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("export_servers"))
async def cmd_export_servers(message: Message, db: Database) -> None:
    """Экспорт списка серверов в JSON."""
    service = ServerService(db)
    servers = await service.export_servers()

    if not servers:
        await message.answer("❌ Нет серверов для экспорта.")
        return

    json_data = json.dumps(servers, ensure_ascii=False, indent=2)

    # Сохраняем во временный файл
    filename = "servers_export.json"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(json_data)

    await message.answer_document(
        InputFile(filename),
        caption=f"📦 Экспорт серверов ({len(servers)} шт.)",
    )

    # Удаляем временный файл
    import os
    os.remove(filename)
