"""
Клавиатуры для тестов
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.common import get_back_button


def get_test_answer_keyboard(answers: list[str], question_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с вариантами ответов на вопрос теста"""
    builder = InlineKeyboardBuilder()
    
    for idx, answer in enumerate(answers):
        builder.add(InlineKeyboardButton(
            text=answer,
            callback_data=f"test_answer:{question_id}:{idx}"
        ))
    
    builder.add(get_back_button("back_to_test_info"))
    builder.adjust(1)
    return builder.as_markup()


def get_test_explanation_keyboard(question_id: int, is_last: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура после ответа на вопрос"""
    builder = InlineKeyboardBuilder()
    
    if is_last:
        builder.add(InlineKeyboardButton(text="✅ Завершить тест", callback_data=f"finish_test:{question_id}"))
    else:
        builder.add(InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data=f"next_question:{question_id}"))
    
    builder.add(InlineKeyboardButton(text="📖 Пояснение", callback_data=f"explanation:{question_id}"))
    builder.add(get_back_button("back_to_test"))
    builder.adjust(1)
    return builder.as_markup()


def get_test_list_keyboard() -> InlineKeyboardMarkup:
    """Список доступных тестов"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="Тест 1", callback_data="test:1"))
    builder.add(InlineKeyboardButton(text="Тест 2", callback_data="test:2"))
    builder.add(InlineKeyboardButton(text="Тест 3", callback_data="test:3"))
    builder.add(InlineKeyboardButton(text="ℹ️ О тестах", callback_data="about_tests"))
    builder.add(get_back_button("profile"))
    builder.adjust(1)
    return builder.as_markup()


def get_test_info_keyboard(test_id: int) -> InlineKeyboardMarkup:
    """Информация о тесте с кнопкой начала"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="▶️ Пройти тест", callback_data=f"start_test:{test_id}"))
    builder.add(get_back_button("tests_list"))
    builder.adjust(1)
    return builder.as_markup()
