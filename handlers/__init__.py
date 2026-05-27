"""
Пакет обработчиков (handlers) для aiogram.
"""

from . import user_handlers
from . import admin_handlers
from . import server_handlers

__all__ = ["user_handlers", "admin_handlers", "server_handlers"]
