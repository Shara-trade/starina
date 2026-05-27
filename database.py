"""
Модуль для работы с SQLite базой данных.

Использует aiosqlite для полной асинхронности.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import aiosqlite

import config

logger = logging.getLogger(__name__)


class Database:
    """Асинхронный класс для работы с SQLite базой данных VPN-бота."""

    def __init__(self, db_path: str = config.DB_PATH) -> None:
        self.db_path = db_path

    def _connect(self) -> aiosqlite.Connection:
        """Создаёт асинхронное подключение к БД."""
        return aiosqlite.connect(self.db_path)

    async def init_db(self) -> None:
        """
        Инициализирует базу данных: создаёт таблицы, если они не существуют.
        """
        async with self._connect() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    subscription_status TEXT DEFAULT 'expired',
                    subscription_expires DATETIME,
                    traffic_limit_gb INTEGER DEFAULT 0,
                    traffic_used_gb REAL DEFAULT 0.0,
                    xui_client_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    tariff_days INTEGER NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    status TEXT DEFAULT 'pending',
                    provider TEXT DEFAULT 't_bank',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    paid_at DATETIME
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL UNIQUE,
                    reward_paid INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        # Инициализируем таблицу серверов
        await self.init_servers_table()
        logger.info("База данных инициализирована.")

    # ─── Users ────────────────────────────────────────────────────────────────

    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        referrer_id: Optional[int] = None,
    ) -> bool:
        """
        Регистрирует нового пользователя в БД.

        :param telegram_id: ID пользователя в Telegram.
        :param username: Юзернейм пользователя.
        :param referrer_id: ID пригласившего пользователя (для реферальной системы).
        :return: True если пользователь создан, False если уже существует.
        """
        async with self._connect() as db:
            try:
                await db.execute(
                    """
                    INSERT INTO users (telegram_id, username)
                    VALUES (?, ?)
                    """,
                    (telegram_id, username),
                )
                await db.commit()

                # Если есть реферер, записываем реферала
                if referrer_id and referrer_id != telegram_id:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO referrals (referrer_id, referred_id)
                        VALUES (?, ?)
                        """,
                        (referrer_id, telegram_id),
                    )
                    await db.commit()

                logger.info(f"Пользователь {telegram_id} зарегистрирован.")
                return True
            except aiosqlite.IntegrityError:
                logger.debug(f"Пользователь {telegram_id} уже существует.")
                return False

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе по Telegram ID.

        :param telegram_id: ID пользователя в Telegram.
        :return: Словарь с данными пользователя или None.
        """
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_subscription(
        self,
        telegram_id: int,
        days: int,
        client_name: str,
        traffic_gb: int = config.DEFAULT_TRAFFIC_GB,
    ) -> None:
        """
        Активирует или продлевает подписку пользователя.

        :param telegram_id: ID пользователя в Telegram.
        :param days: Количество дней подписки.
        :param client_name: Имя клиента в 3x-ui.
        :param traffic_gb: Лимит трафика в ГБ.
        """
        expires = datetime.utcnow() + timedelta(days=days)
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE users
                SET subscription_status = 'active',
                    subscription_expires = ?,
                    traffic_limit_gb = ?,
                    xui_client_name = ?
                WHERE telegram_id = ?
                """,
                (expires.isoformat(), traffic_gb, client_name, telegram_id),
            )
            await db.commit()
        logger.info(f"Подписка пользователя {telegram_id} продлена на {days} дней.")

    async def update_traffic_used(
        self, telegram_id: int, traffic_used_gb: float
    ) -> None:
        """
        Обновляет использованный трафик пользователя.

        :param telegram_id: ID пользователя в Telegram.
        :param traffic_used_gb: Использованный трафик в ГБ.
        """
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE users
                SET traffic_used_gb = ?
                WHERE telegram_id = ?
                """,
                (traffic_used_gb, telegram_id),
            )
            await db.commit()

    async def expire_subscription(self, telegram_id: int) -> None:
        """
        Устанавливает статус подписки как 'expired'.

        :param telegram_id: ID пользователя в Telegram.
        """
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE users
                SET subscription_status = 'expired',
                    subscription_expires = NULL
                WHERE telegram_id = ?
                """,
                (telegram_id,),
            )
            await db.commit()
        logger.info(f"Подписка пользователя {telegram_id} истекла.")

    async def ban_user(self, telegram_id: int) -> None:
        """
        Блокирует пользователя (устанавливает статус 'banned').

        :param telegram_id: ID пользователя в Telegram.
        """
        async with self._connect() as db:
            await db.execute(
                """
                UPDATE users
                SET subscription_status = 'banned'
                WHERE telegram_id = ?
                """,
                (telegram_id,),
            )
            await db.commit()
        logger.info(f"Пользователь {telegram_id} заблокирован.")

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Получает список всех пользователей.

        :return: Список словарей с данными пользователей.
        """
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_active_users_count(self) -> int:
        """
        Возвращает количество пользователей со статусом 'active'.
        """
        async with self._connect() as db:
            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE subscription_status = 'active'"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_expiring_soon_users(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Возвращает пользователей, у которых подписка истекает в течение N часов.

        :param hours: Количество часов до истечения.
        :return: Список пользователей.
        """
        threshold = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM users
                WHERE subscription_status = 'active'
                  AND subscription_expires <= ?
                """,
                (threshold,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ─── Payments ─────────────────────────────────────────────────────────────

    async def add_payment(
        self,
        telegram_id: int,
        amount: float,
        tariff_days: int,
        currency: str = "RUB",
        provider: str = "t_bank",
    ) -> int:
        """
        Добавляет запись о платеже в БД.

        :param telegram_id: ID пользователя в Telegram.
        :param amount: Сумма платежа.
        :param tariff_days: Количество дней подписки.
        :param currency: Валюта платежа.
        :param provider: Платёжный провайдер.
        :return: ID созданного платежа.
        """
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO payments (telegram_id, amount, tariff_days, currency, provider)
                VALUES (?, ?, ?, ?, ?)
                """,
                (telegram_id, amount, tariff_days, currency, provider),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о платеже по ID.

        :param payment_id: ID платежа.
        :return: Словарь с данными платежа или None.
        """
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_pending_confirmation_payments(self) -> List[Dict[str, Any]]:
        """
        Возвращает платежи, ожидающие подтверждения администратором.

        :return: Список платежей со статусом 'pending_confirmation'.
        """
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM payments WHERE status = 'pending_confirmation' ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_payment_status(self, payment_id: int, status: str) -> None:
        """
        Обновляет статус платежа.

        :param payment_id: ID платежа.
        :param status: Новый статус (pending, pending_confirmation, paid, declined).
        """
        async with self._connect() as db:
            if status == "paid":
                await db.execute(
                    """
                    UPDATE payments
                    SET status = ?, paid_at = CURRENT_TIMESTAMP
                    WHERE payment_id = ?
                    """,
                    (status, payment_id),
                )
            else:
                await db.execute(
                    "UPDATE payments SET status = ? WHERE payment_id = ?",
                    (status, payment_id),
                )
            await db.commit()

    # ─── Servers (3x-ui management) ────────────────────────────────────────────

    async def init_servers_table(self) -> None:
        """Создаёт таблицу servers, если её нет."""
        async with self._connect() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    username_encrypted TEXT NOT NULL,
                    password_encrypted TEXT NOT NULL,
                    location TEXT NOT NULL,
                    traffic_limit_gb INTEGER NOT NULL,
                    traffic_used_gb REAL DEFAULT 0.0,
                    max_clients INTEGER NOT NULL,
                    current_clients INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'offline',
                    is_active INTEGER DEFAULT 1,
                    balance_weight INTEGER DEFAULT 1,
                    last_checked DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER
                )
            """)
            await db.commit()
        logger.info("Таблица servers инициализирована.")

    async def create_server(
        self,
        name: str,
        url: str,
        username_encrypted: str,
        password_encrypted: str,
        location: str,
        traffic_limit_gb: int,
        max_clients: int,
        created_by: int,
    ) -> int:
        """
        Создаёт новый сервер в БД.

        :return: ID созданного сервера.
        """
        async with self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO servers (
                    name, url, username_encrypted, password_encrypted,
                    location, traffic_limit_gb, max_clients, created_by, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'online')
                """,
                (name, url, username_encrypted, password_encrypted,
                 location, traffic_limit_gb, max_clients, created_by),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_server(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Получает сервер по ID."""
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM servers WHERE id = ?", (server_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_server_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Получает сервер по имени."""
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM servers WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_servers(self) -> List[Dict[str, Any]]:
        """Получает все серверы."""
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM servers ORDER BY id ASC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_server_field(self, server_id: int, field: str, value: Any) -> None:
        """Обновляет конкретное поле сервера."""
        async with self._connect() as db:
            await db.execute(
                f"UPDATE servers SET {field} = ?, last_checked = CURRENT_TIMESTAMP WHERE id = ?",
                (value, server_id),
            )
            await db.commit()

    async def update_server_status(self, server_id: int, status: str) -> None:
        """Обновляет статус сервера и время последней проверки."""
        async with self._connect() as db:
            await db.execute(
                "UPDATE servers SET status = ?, last_checked = CURRENT_TIMESTAMP WHERE id = ?",
                (status, server_id),
            )
            await db.commit()

    async def delete_server(self, server_id: int) -> None:
        """Удаляет сервер из БД."""
        async with self._connect() as db:
            await db.execute("DELETE FROM servers WHERE id = ?", (server_id,))
            await db.commit()
        logger.info(f"Сервер {server_id} удалён из БД.")
