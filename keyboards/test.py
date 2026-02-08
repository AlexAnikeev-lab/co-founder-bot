"""
Клавиатуры для тестов
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.common import get_back_button, get_main_menu_button


def get_post_registration_offer_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после регистрации: предложение пройти основной тест или позже"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📋 Пройти основной тест",
        callback_data="start_test:main"
    ))
    builder.add(get_main_menu_button())
    builder.adjust(1)
    return builder.as_markup()


def get_test_list_keyboard(main_test_completed: bool = False) -> InlineKeyboardMarkup:
    """Список доступных тестов. Основной тест скрыт, если уже пройден (перепройти нельзя)."""
    builder = InlineKeyboardBuilder()
    if not main_test_completed:
        builder.add(InlineKeyboardButton(
            text="📋 Основной тест (10 вопросов)",
            callback_data="test:main"
        ))
    builder.add(InlineKeyboardButton(
        text="🎭 Ролевые предпочтения",
        callback_data="test:roles_extra"
    ))
    builder.add(InlineKeyboardButton(
        text="⚖️ Ценности и этика",
        callback_data="test:ethics_extra"
    ))
    builder.add(InlineKeyboardButton(
        text="🎯 Цели и мотивация",
        callback_data="test:goals_extra"
    ))
    builder.add(InlineKeyboardButton(
        text="🎲 Толерантность к риску",
        callback_data="test:risk_extra"
    ))
    builder.add(InlineKeyboardButton(
        text="🤔 Стиль принятия решений",
        callback_data="test:decision_extra"
    ))
    builder.add(InlineKeyboardButton(
        text="💬 Стиль коммуникации",
        callback_data="test:comm_extra"
    ))
    builder.add(InlineKeyboardButton(
        text="ℹ️ О тестах",
        callback_data="about_tests"
    ))
    builder.add(get_back_button("profile"))
    builder.adjust(1)
    return builder.as_markup()


def get_test_info_keyboard(test_type: str) -> InlineKeyboardMarkup:
    """Информация о тесте с кнопкой начала"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="▶️ Начать тест",
        callback_data=f"start_test:{test_type}"
    ))
    builder.add(get_back_button("tests"))
    builder.adjust(1)
    return builder.as_markup()


def get_test_answer_keyboard(
    answers: dict,
    question_num: int,
    test_type: str,
    is_scale: bool = False
) -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами ответов на вопрос теста
    
    Args:
        answers: Словарь ответов {"a": "Текст ответа", ...}
        question_num: Номер вопроса
        test_type: Тип теста
        is_scale: True если это шкала 1-5
    """
    builder = InlineKeyboardBuilder()
    
    if is_scale:
        # Шкала 1-5
        for i in range(1, 6):
            label = answers.get(str(i), str(i))
            builder.add(InlineKeyboardButton(
                text=f"{i} - {label}",
                callback_data=f"test_answer:{test_type}:{question_num}:{i}"
            ))
    else:
        # Обычные варианты ответов
        for key in sorted(answers.keys()):
            answer_text = answers[key]
            # Обрезаем длинный текст для кнопки
            if len(answer_text) > 50:
                button_text = answer_text[:47] + "..."
            else:
                button_text = answer_text
            
            builder.add(InlineKeyboardButton(
                text=f"{key.upper()}) {button_text}",
                callback_data=f"test_answer:{test_type}:{question_num}:{key}"
            ))
    
    builder.add(get_back_button("tests"))
    builder.adjust(1)
    return builder.as_markup()


def get_test_progress_keyboard(
    test_type: str,
    current_question: int,
    total_questions: int,
    is_last: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура с прогрессом теста"""
    builder = InlineKeyboardBuilder()
    
    if is_last:
        builder.add(InlineKeyboardButton(
            text="✅ Завершить тест",
            callback_data=f"finish_test:{test_type}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text=f"➡️ Следующий вопрос ({current_question + 1}/{total_questions})",
            callback_data=f"next_question:{test_type}:{current_question + 1}"
        ))
    
    builder.add(get_back_button("tests"))
    builder.adjust(1)
    return builder.as_markup()


def get_test_results_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после завершения теста"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📊 Мой профиль",
        callback_data="profile"
    ))
    builder.add(InlineKeyboardButton(
        text="📝 Пройти другие тесты",
        callback_data="tests"
    ))
    builder.add(get_back_button("main_menu"))
    builder.adjust(1)
    return builder.as_markup()
