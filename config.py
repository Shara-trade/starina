"""
Конфигурация бота VPN.

Все чувствительные данные загружаются из переменных окружения (.env).
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


# ─── Telegram Bot ───────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")

# ─── 3x-ui Panel ────────────────────────────────────────────────────────────
XUI_URL: str = os.getenv("XUI_URL", "").rstrip("/")  # убираем trailing slash
XUI_USER: str = os.getenv("XUI_USER", "admin")
XUI_PASS: str = os.getenv("XUI_PASS", "")

if not XUI_URL or not XUI_PASS:
    raise ValueError("XUI_URL и XUI_PASS должны быть заданы в .env")

# ─── Admin ──────────────────────────────────────────────────────────────────
# Список Telegram ID администраторов (через запятую в .env)
_ADMIN_IDS_RAW: str = os.getenv("ADMIN_ID", "")
ADMIN_IDS: list[int] = [
    int(x.strip())
    for x in _ADMIN_IDS_RAW.split(",")
    if x.strip().isdigit()
]

if not ADMIN_IDS:
    raise ValueError("ADMIN_ID не задан в .env")

# ─── Database ───────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "vpn_bot.db")

# ─── Encryption ─────────────────────────────────────────────────────────────
# Fernet-ключ для шифрования паролей серверов (32 байта, base64)
# Сгенерировать: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# ─── T-Bank (Tinkoff) requisites ────────────────────────────────────────────
# Для ручного приёма переводов: бот покажет реквизиты, пользователь переведёт
# в приложении банка, админ подтвердит поступление вручную.
T_BANK_PHONE: str = os.getenv("T_BANK_PHONE", "")
T_BANK_CARD: str = os.getenv("T_BANK_CARD", "")
T_BANK_CARDHOLDER: str = os.getenv("T_BANK_CARDHOLDER", "")

if not T_BANK_PHONE or not T_BANK_CARD:
    raise ValueError("T_BANK_PHONE и T_BANK_CARD должны быть заданы в .env")

# ─── Subscription defaults ──────────────────────────────────────────────────
DEFAULT_TRAFFIC_GB: int = int(os.getenv("DEFAULT_TRAFFIC_GB", "100"))
DEFAULT_SUBSCRIPTION_DAYS: int = int(os.getenv("DEFAULT_SUBSCRIPTION_DAYS", "30"))

# ─── Logging ────────────────────────────────────────────────────────────────
LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
