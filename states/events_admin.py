"""
FSM состояния для управления мероприятиями (админ).
"""

from aiogram.fsm.state import State, StatesGroup


class AdminEventsStates(StatesGroup):
    waiting_for_banner = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_datetime = State()

    waiting_for_edit_field = State()

