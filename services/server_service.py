"""
Сервисный слой для управления VPN-серверами (3x-ui).

Включает:
    - CRUD операции с серверами в БД
    - Шифрование/дешифрование учётных данных
    - Проверку подключения к панели 3x-ui
    - Сбор статистики
"""

import json
import logging
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from cryptography.fernet import Fernet

import config

logger = logging.getLogger(__name__)


class ServerService:
    """Сервис для управления серверами 3x-ui."""

    def __init__(self, db: "Database") -> None:
        self.db = db
        self._fernet: Optional[Fernet] = None
        self._init_encryption()

    def _init_encryption(self) -> None:
        """Инициализирует Fernet для шифрования."""
        key = getattr(config, "ENCRYPTION_KEY", "")
        if not key:
            # Генерируем временный ключ, если не задан (только для разработки)
            logger.warning("ENCRYPTION_KEY не задан в config, используется временный ключ!")
            key = Fernet.generate_key().decode()
        try:
            self._fernet = Fernet(key.encode())
        except Exception:
            # Если ключ невалидный, генерируем новый
            key_bytes = Fernet.generate_key()
            self._fernet = Fernet(key_bytes)

    # ─── Encryption ───────────────────────────────────────────────────────────

    async def encrypt_text(self, text: str) -> str:
        """Шифрует текст с помощью Fernet."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        encrypted = self._fernet.encrypt(text.encode())
        return encrypted.decode()

    async def decrypt_text(self, encrypted: str) -> str:
        """Дешифрует текст."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        decrypted = self._fernet.decrypt(encrypted.encode())
        return decrypted.decode()

    # ─── Connection testing ───────────────────────────────────────────────────

    async def test_server_connection(
        self,
        url: str,
        username: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Проверяет доступность панели 3x-ui.

        :return: {"success": bool, "message": str, "inbounds_count": int}
        """
        url = url.rstrip("/")
        timeout = httpx.Timeout(15.0, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                # 1. Пробуем авторизоваться
                login_resp = await client.post(
                    f"{url}/login",
                    data={"username": username, "password": password},
                )
                login_data = login_resp.json() if login_resp.status_code == 200 else {}

                if not login_data.get("success"):
                    return {
                        "success": False,
                        "message": "Неверный логин или пароль",
                        "inbounds_count": 0,
                    }

                # 2. Пробуем получить inbounds
                inb_resp = await client.get(f"{url}/panel/api/inbounds")
                inb_data = inb_resp.json() if inb_resp.status_code == 200 else {}
                inbounds = inb_data.get("obj", []) if inb_data.get("success") else []

                return {
                    "success": True,
                    "message": "Подключение успешно",
                    "inbounds_count": len(inbounds),
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Превышено время ожидания. Сервер недоступен.",
                "inbounds_count": 0,
            }
        except httpx.ConnectError:
            return {
                "success": False,
                "message": "Не удалось подключиться к серверу. Проверьте URL.",
                "inbounds_count": 0,
            }
        except Exception as exc:
            logger.error(f"Ошибка проверки подключения к {url}: {exc}")
            return {
                "success": False,
                "message": f"Ошибка подключения: {type(exc).__name__}",
                "inbounds_count": 0,
            }

    # ─── CRUD: Add ────────────────────────────────────────────────────────────

    async def add_server(
        self,
        name: str,
        url: str,
        username: str,
        password: str,
        location: str,
        traffic_limit_gb: int,
        max_clients: int,
        created_by: int,
    ) -> Dict[str, Any]:
        """
        Добавляет новый сервер в БД.

        :return: {"success": bool, "server_id": int|None, "message": str}
        """
        # 1. Проверка существования
        existing = await self.db.get_server_by_name(name)
        if existing:
            return {
                "success": False,
                "server_id": None,
                "message": f"Сервер с именем '{name}' уже существует (ID: {existing['id']})",
            }

        # 2. Проверка подключения
        conn_test = await self.test_server_connection(url, username, password)
        if not conn_test["success"]:
            return {
                "success": False,
                "server_id": None,
                "message": conn_test["message"],
            }

        # 3. Шифруем учётные данные
        username_enc = await self.encrypt_text(username)
        password_enc = await self.encrypt_text(password)

        # 4. Сохраняем в БД
        server_id = await self.db.create_server(
            name=name,
            url=url.rstrip("/"),
            username_encrypted=username_enc,
            password_encrypted=password_enc,
            location=location,
            traffic_limit_gb=traffic_limit_gb,
            max_clients=max_clients,
            created_by=created_by,
        )

        logger.info(f"Сервер '{name}' добавлен админом {created_by} (ID: {server_id})")
        return {
            "success": True,
            "server_id": server_id,
            "message": "Сервер успешно добавлен",
        }

    # ─── CRUD: Get ────────────────────────────────────────────────────────────

    async def get_server(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Получает сервер по ID."""
        return await self.db.get_server(server_id)

    async def get_all_servers(self) -> List[Dict[str, Any]]:
        """Получает список всех серверов."""
        return await self.db.get_all_servers()

    async def get_server_stats(self, server_id: int) -> Dict[str, Any]:
        """
        Получает расширенную статистику сервера.

        :return: {"server": dict, "connection_test": dict, "usage_percent": float}
        """
        server = await self.db.get_server(server_id)
        if not server:
            return {"server": None, "connection_test": None, "usage_percent": 0.0}

        # Проверяем подключение
        try:
            username = await self.decrypt_text(server["username_encrypted"])
            password = await self.decrypt_text(server["password_encrypted"])
            conn_test = await self.test_server_connection(
                server["url"], username, password
            )
            # Обновляем статус в БД
            new_status = "online" if conn_test["success"] else "offline"
            await self.db.update_server_status(server_id, new_status)
            server["status"] = new_status
        except Exception as exc:
            logger.warning(f"Не удалось проверить сервер {server_id}: {exc}")
            conn_test = {"success": False, "message": str(exc)}

        # Процент использования клиентов
        max_c = server.get("max_clients", 1)
        current_c = server.get("current_clients", 0)
        client_percent = (current_c / max_c * 100) if max_c > 0 else 0

        # Процент использования трафика
        limit = server.get("traffic_limit_gb", 1)
        used = server.get("traffic_used_gb", 0)
        traffic_percent = (used / limit * 100) if limit > 0 else 0

        return {
            "server": server,
            "connection_test": conn_test,
            "client_percent": round(client_percent, 1),
            "traffic_percent": round(traffic_percent, 1),
        }

    # ─── CRUD: Edit ───────────────────────────────────────────────────────────

    async def edit_server_field(
        self,
        server_id: int,
        field: str,
        new_value: Any,
    ) -> Dict[str, Any]:
        """
        Редактирует конкретное поле сервера.

        :return: {"success": bool, "message": str}
        """
        server = await self.db.get_server(server_id)
        if not server:
            return {"success": False, "message": "Сервер не найден"}

        # Поля, которые можно редактировать
        allowed_fields = {
            "name", "url", "username", "password", "location",
            "traffic_limit_gb", "max_clients", "balance_weight", "is_active",
        }
        if field not in allowed_fields:
            return {"success": False, "message": f"Поле '{field}' нельзя редактировать"}

        # Шифруем sensitive поля
        if field == "username":
            new_value = await self.encrypt_text(str(new_value))
            field = "username_encrypted"
        elif field == "password":
            new_value = await self.encrypt_text(str(new_value))
            field = "password_encrypted"
        elif field in ("traffic_limit_gb", "max_clients", "balance_weight"):
            new_value = int(new_value)
        elif field == "is_active":
            new_value = 1 if new_value in (True, "1", 1, "yes", "true") else 0

        await self.db.update_server_field(server_id, field, new_value)

        # Если изменили url/username/password — проверяем подключение
        if field in ("url", "username_encrypted", "password_encrypted"):
            updated = await self.db.get_server(server_id)
            try:
                username = await self.decrypt_text(updated["username_encrypted"])
                password = await self.decrypt_text(updated["password_encrypted"])
                conn = await self.test_server_connection(updated["url"], username, password)
                status = "online" if conn["success"] else "offline"
                await self.db.update_server_status(server_id, status)
                if not conn["success"]:
                    return {
                        "success": True,
                        "message": f"Поле обновлено, но подключение не работает: {conn['message']}",
                    }
            except Exception as exc:
                return {
                    "success": True,
                    "message": f"Поле обновлено, но не удалось проверить подключение: {exc}",
                }

        logger.info(f"Поле '{field}' сервера {server_id} обновлено")
        return {"success": True, "message": "Поле успешно обновлено"}

    # ─── CRUD: Remove ─────────────────────────────────────────────────────────

    async def remove_server(self, server_id: int) -> Dict[str, Any]:
        """
        Удаляет сервер.

        :return: {"success": bool, "message": str}
        """
        server = await self.db.get_server(server_id)
        if not server:
            return {"success": False, "message": "Сервер не найден"}

        current_clients = server.get("current_clients", 0)
        if current_clients > 0:
            return {
                "success": False,
                "message": f"На сервере {current_clients} активных клиентов. Сначала удалите клиентов.",
            }

        await self.db.delete_server(server_id)
        logger.info(f"Сервер {server_id} удалён")
        return {"success": True, "message": "Сервер успешно удалён"}

    # ─── Toggle active ────────────────────────────────────────────────────────

    async def toggle_server_active(self, server_id: int) -> Dict[str, Any]:
        """Переключает флаг is_active сервера."""
        server = await self.db.get_server(server_id)
        if not server:
            return {"success": False, "message": "Сервер не найден"}

        new_state = 0 if server.get("is_active", 1) else 1
        await self.db.update_server_field(server_id, "is_active", new_state)
        status_text = "активирован" if new_state else "деактивирован"
        logger.info(f"Сервер {server_id} {status_text}")
        return {"success": True, "message": f"Сервер {status_text}", "is_active": bool(new_state)}

    # ─── Bulk operations ──────────────────────────────────────────────────────

    async def test_all_servers(self) -> List[Dict[str, Any]]:
        """Проверяет все серверы на доступность."""
        servers = await self.db.get_all_servers()
        results = []
        for srv in servers:
            sid = srv["id"]
            try:
                username = await self.decrypt_text(srv["username_encrypted"])
                password = await self.decrypt_text(srv["password_encrypted"])
                test = await self.test_server_connection(srv["url"], username, password)
                status = "online" if test["success"] else "offline"
                await self.db.update_server_status(sid, status)
                results.append({
                    "id": sid,
                    "name": srv["name"],
                    "status": status,
                    "message": test["message"],
                })
            except Exception as exc:
                await self.db.update_server_status(sid, "offline")
                results.append({
                    "id": sid,
                    "name": srv["name"],
                    "status": "offline",
                    "message": str(exc),
                })
        return results

    # ─── Export / Import ──────────────────────────────────────────────────────

    async def export_servers(self) -> List[Dict[str, Any]]:
        """Экспортирует все серверы (без зашифрованных данных)."""
        servers = await self.db.get_all_servers()
        export_list = []
        for srv in servers:
            export_list.append({
                "id": srv["id"],
                "name": srv["name"],
                "url": srv["url"],
                "location": srv["location"],
                "traffic_limit_gb": srv["traffic_limit_gb"],
                "traffic_used_gb": srv["traffic_used_gb"],
                "max_clients": srv["max_clients"],
                "current_clients": srv["current_clients"],
                "status": srv["status"],
                "is_active": srv["is_active"],
                "balance_weight": srv["balance_weight"],
                "created_at": srv["created_at"],
            })
        return export_list
