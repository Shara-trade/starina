"""
FSM состояния для мультишаговых диалогов управления серверами.

Использует aiogram 3.x Finite State Machine.
"""

from aiogram.fsm.state import State, StatesGroup


class ServerAddState(StatesGroup):
    """Состояния для добавления нового сервера."""

    name = State()
    url = State()
    username = State()
    password = State()
    location = State()
    traffic_limit_gb = State()
    max_clients = State()
    confirm = State()


class ServerEditState(StatesGroup):
    """Состояния для редактирования сервера."""

    select_server = State()
    edit_field = State()
    new_value = State()
    confirm = State()
