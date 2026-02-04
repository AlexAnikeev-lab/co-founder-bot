"""
Состояния для прохождения тестов
"""

from aiogram.fsm.state import State, StatesGroup


class TestStates(StatesGroup):
    """Состояния прохождения теста"""
    viewing_test_info = State()
    answering_question = State()
    viewing_explanation = State()
    viewing_results = State()
