"""
Точка входа в VPN-бота.

Инициализирует:
    - логирование
    - базу данных
    - HTTP-клиент 3x-ui
    - диспетчер aiogram
    - роутеры (handlers)

Запускает поллинг обновлений от Telegram.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import Database
from xui_client import XuiClient
from handlers import user_handlers, admin_handlers, server_handlers


# ─── Logging setup ──────────────────────────────────────────────────────────

def setup_logging() -> None:
    """
    Настраивает логирование в файл и консоль.
    """
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


# ─── Dependency injection via middleware ────────────────────────────────────

class DependenciesMiddleware:
    """
    Middleware для передачи зависимостей (db, xui) в хендлеры через data.
    """

    def __init__(self, db: Database, xui: XuiClient) -> None:
        self.db = db
        self.xui = xui

    async def __call__(self, handler, event, data):
        data["db"] = self.db
        data["xui"] = self.xui
        return await handler(event, data)


# ─── Background tasks ───────────────────────────────────────────────────────

async def notify_expiring_subscriptions(bot: Bot, db: Database) -> None:
    """
    Фоновая задача: отправляет уведомления за 24 часа до истечения подписки.
    Запускается раз в час.
    """
    while True:
        try:
            users = await db.get_expiring_soon_users(hours=24)
            for user in users:
                telegram_id = user.get("telegram_id")
                if not telegram_id:
                    continue
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=(
                            "⚠️ <b>Внимание!</b>\n\n"
                            "Ваша подписка истекает менее чем через <b>24 часа</b>.\n"
                            "Не забудьте продлить, чтобы не потерять доступ.\n\n"
                            "/buy — продлить подписку"
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                    logging.getLogger(__name__).info(
                        f"Уведомление об истечении отправлено {telegram_id}"
                    )
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        f"Не удалось отправить уведомление {telegram_id}: {exc}"
                    )
        except Exception as exc:
            logging.getLogger(__name__).error(f"Ошибка в фоновой задаче: {exc}")

        # Ждём 1 час
        await asyncio.sleep(3600)


# ─── Main ───────────────────────────────────────────────────────────────────

async def main() -> None:
    """
    Главная асинхронная функция запуска бота.
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск VPN-бота...")

    # Инициализация БД
    db = Database()
    await db.init_db()

    # Инициализация клиента 3x-ui
    xui = XuiClient()

    # Создаём бота и диспетчер
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Подключаем FSM storage для мультишаговых диалогов
    dp.fsm.storage = MemoryStorage()

    # Подключаем middleware с зависимостями
    deps_middleware = DependenciesMiddleware(db, xui)
    dp.message.middleware(deps_middleware)
    dp.callback_query.middleware(deps_middleware)

    # Регистрируем роутеры
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(server_handlers.router)

    # Запускаем фоновую задачу уведомлений
    asyncio.create_task(notify_expiring_subscriptions(bot, db))

    logger.info("Бот запущен. Ожидание сообщений...")

    try:
        # Удаляем webhook (если был) и запускаем поллинг
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await xui.close()
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
