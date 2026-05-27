"""
Клиент для работы с API панели 3x-ui.

Документация по API 3x-ui (v2.3.0+):
- POST /login          — авторизация
- GET  /panel/api/inbounds  — список inbound'ов
- POST /panel/api/inbounds/addClient — добавление клиента
- POST /panel/api/inbounds/delClient/{id}/{clientId} — удаление клиента
"""

import logging
import uuid
from typing import Optional, Dict, Any, List

import httpx

import config

logger = logging.getLogger(__name__)


class XuiClient:
    """
    Асинхронный клиент для API 3x-ui.

    Автоматически авторизуется при первом запросе и сохраняет cookies.
    """

    def __init__(self) -> None:
        self.base_url = config.XUI_URL
        self.username = config.XUI_USER
        self.password = config.XUI_PASS
        self._client: Optional[httpx.AsyncClient] = None
        self._logged_in = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Возвращает (или создаёт) экземпляр httpx.AsyncClient."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def _ensure_login(self) -> bool:
        """
        Проверяет авторизацию и выполняет login при необходимости.

        :return: True если авторизация успешна.
        """
        if self._logged_in:
            return True

        client = await self._get_client()
        try:
            response = await client.post(
                "/login",
                data={"username": self.username, "password": self.password},
            )
            response.raise_for_status()

            # 3x-ui возвращает JSON с success=true/false
            data = response.json()
            if data.get("success"):
                self._logged_in = True
                logger.info("Успешная авторизация в 3x-ui.")
                return True
            else:
                logger.error(f"Ошибка авторизации 3x-ui: {data}")
                return False
        except Exception as exc:
            logger.error(f"Исключение при авторизации 3x-ui: {exc}")
            return False

    async def get_inbounds(self) -> List[Dict[str, Any]]:
        """
        Получает список inbound'ов из панели.

        :return: Список inbound'ов.
        """
        if not await self._ensure_login():
            return []

        client = await self._get_client()
        try:
            response = await client.get("/panel/api/inbounds")
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data.get("obj", [])
            logger.error(f"Ошибка получения inbounds: {data}")
            return []
        except Exception as exc:
            logger.error(f"Исключение при получении inbounds: {exc}")
            return []

    async def create_client(
        self,
        client_name: str,
        traffic_gb: int = config.DEFAULT_TRAFFIC_GB,
        expire_days: int = config.DEFAULT_SUBSCRIPTION_DAYS,
        inbound_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Создаёт нового клиента (пользователя) в 3x-ui.

        :param client_name: Уникальное имя клиента (email в 3x-ui).
        :param traffic_gb: Лимит трафика в ГБ.
        :param expire_days: Срок действия в днях.
        :param inbound_id: ID inbound'а (если None — берётся первый доступный).
        :return: Словарь с данными созданного клиента или None.
        """
        if not await self._ensure_login():
            return None

        # Получаем inbound'ы, если ID не указан
        if inbound_id is None:
            inbounds = await self.get_inbounds()
            if not inbounds:
                logger.error("Нет доступных inbound'ов для создания клиента.")
                return None
            inbound_id = inbounds[0].get("id")

        # Генерируем UUID для клиента (VMess/VLESS)
        client_uuid = str(uuid.uuid4())

        # Лимит трафика в байтах
        total_bytes = traffic_gb * 1024 * 1024 * 1024

        # Время истечения в мс (timestamp)
        import time
        expiry_time = int((time.time() + expire_days * 86400) * 1000)

        client_data = {
            "id": inbound_id,
            "settings": str({
                "clients": [
                    {
                        "id": client_uuid,
                        "email": client_name,
                        "totalGB": total_bytes,
                        "expiryTime": expiry_time,
                        "enable": True,
                    }
                ]
            }).replace("'", '"'),
        }

        client = await self._get_client()
        try:
            response = await client.post(
                f"/panel/api/inbounds/addClient/{inbound_id}",
                data=client_data,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                logger.info(f"Клиент {client_name} создан в 3x-ui.")
                return {
                    "uuid": client_uuid,
                    "email": client_name,
                    "inbound_id": inbound_id,
                    "expiry_time": expiry_time,
                }
            else:
                logger.error(f"Ошибка создания клиента: {data}")
                return None
        except Exception as exc:
            logger.error(f"Исключение при создании клиента: {exc}")
            return None

    async def get_client(self, client_name: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о клиенте по email (client_name).

        :param client_name: Email клиента в 3x-ui.
        :return: Данные клиента или None.
        """
        inbounds = await self.get_inbounds()
        for inbound in inbounds:
            settings = inbound.get("settings", "")
            try:
                import json
                settings_obj = json.loads(settings)
                for client in settings_obj.get("clients", []):
                    if client.get("email") == client_name:
                        return {
                            "inbound_id": inbound.get("id"),
                            "client": client,
                            "remark": inbound.get("remark"),
                            "port": inbound.get("port"),
                            "protocol": inbound.get("protocol"),
                        }
            except Exception:
                continue
        return None

    async def delete_client(self, client_name: str) -> bool:
        """
        Удаляет клиента из 3x-ui по email.

        :param client_name: Email клиента в 3x-ui.
        :return: True если удаление успешно.
        """
        client_info = await self.get_client(client_name)
        if not client_info:
            logger.warning(f"Клиент {client_name} не найден для удаления.")
            return False

        inbound_id = client_info["inbound_id"]
        client_uuid = client_info["client"].get("id")

        if not await self._ensure_login():
            return False

        client = await self._get_client()
        try:
            response = await client.post(
                f"/panel/api/inbounds/delClient/{inbound_id}/{client_uuid}",
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                logger.info(f"Клиент {client_name} удалён из 3x-ui.")
                return True
            else:
                logger.error(f"Ошибка удаления клиента: {data}")
                return False
        except Exception as exc:
            logger.error(f"Исключение при удалении клиента: {exc}")
            return False

    async def generate_v2ray_config(
        self,
        client_name: str,
        protocol: str = "vless",
    ) -> Optional[str]:
        """
        Генерирует v2ray:// ссылку для подключения.

        :param client_name: Email клиента в 3x-ui.
        :param protocol: Протокол (vmess, vless, trojan).
        :return: Ссылка v2ray:// или None.
        """
        client_info = await self.get_client(client_name)
        if not client_info:
            logger.warning(f"Клиент {client_name} не найден для генерации конфига.")
            return None

        inbound = client_info
        client = inbound["client"]
        uuid_str = client.get("id")
        remark = inbound.get("remark", "VPN")
        port = inbound.get("port")
        server_address = self.base_url.replace("https://", "").replace("http://", "").split("/")[0]

        # Простейшая генерация vless:// ссылки
        # Формат: vless://uuid@address:port?security=tls&sni=address#remark
        if protocol.lower() == "vless":
            config_link = (
                f"vless://{uuid_str}@{server_address}:{port}?"
                f"security=tls&type=tcp&sni={server_address}#{remark}"
            )
        elif protocol.lower() == "vmess":
            import base64
            import json
            vmess_obj = {
                "v": "2",
                "ps": remark,
                "add": server_address,
                "port": str(port),
                "id": uuid_str,
                "aid": "0",
                "net": "tcp",
                "type": "none",
                "host": "",
                "path": "",
                "tls": "tls",
            }
            vmess_json = json.dumps(vmess_obj)
            vmess_b64 = base64.b64encode(vmess_json.encode()).decode()
            config_link = f"vmess://{vmess_b64}"
        elif protocol.lower() == "trojan":
            config_link = (
                f"trojan://{uuid_str}@{server_address}:{port}?"
                f"security=tls&type=tcp&sni={server_address}#{remark}"
            )
        else:
            return None

        return config_link

    async def close(self) -> None:
        """Закрывает HTTP-клиент."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._logged_in = False
