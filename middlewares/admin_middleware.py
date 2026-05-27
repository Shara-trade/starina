"""
Middleware для проверки прав администратора.

Пропускает только пользователей, чей Telegram ID есть в списке ADMIN_IDS.
"""

from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

import config


class AdminMiddleware(BaseMiddleware):
    """
    Middleware, которая блокирует доступ к обработчикам для не-админов.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Определяем user_id в зависимости от типа события
        user_id: int = 0
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id not in config.ADMIN_IDS:
            # Для Message — отправляем ответ, для Callback — показываем alert
            if isinstance(event, Message):
                await event.answer("⛔ У вас нет доступа к этой команде.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Нет доступа.", show_alert=True)
            return None

        return await handler(event, data)
