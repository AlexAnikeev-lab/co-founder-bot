"""
Состояния для прохождения тестов
"""

from aiogram.fsm.state import State, StatesGroup


class TestStates(StatesGroup):
    """Состояния прохождения теста"""
    selecting_test = State()  # Выбор теста
    answering_question = State()  # Ответ на вопрос
    answering_scale = State()  # Ответ на вопрос со шкалой 1-5
