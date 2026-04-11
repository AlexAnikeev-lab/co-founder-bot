"""
FSM состояния для управления мероприятиями (админ).
"""

from aiogram.fsm.state import State, StatesGroup


class AdminEventsStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_match_choice = State()
    waiting_for_event_date = State()

    waiting_for_edit_field = State()
    waiting_for_broadcast_message = State()
