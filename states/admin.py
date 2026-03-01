"""
Состояния для админ-панели (поиск, рассылка)
"""

from aiogram.fsm.state import State, StatesGroup


class AdminSearchStates(StatesGroup):
    waiting_for_search_query = State()


class AdminBroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()


class AdminWriteToUserStates(StatesGroup):
    """Админ вводит сообщение для отправки конкретному пользователю."""
    waiting_for_message = State()
