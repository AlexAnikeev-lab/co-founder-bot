"""
Клавиатуры для тестов
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.common import get_back_button, get_main_menu_button
from texts.i18n import t


def get_post_registration_offer_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после регистрации (язык: ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t(lang, "btn_pass_main_test"),
        callback_data="start_test:main"
    ))
    builder.add(get_main_menu_button(lang))
    builder.adjust(1)
    return builder.as_markup()


def get_post_registration_minor_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после регистрации для несовершеннолетних (язык: ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t(lang, "profile_tests"),
        callback_data="tests",
    ))
    builder.add(get_main_menu_button(lang))
    builder.adjust(1)
    return builder.as_markup()


def get_test_list_keyboard(main_test_completed: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    """Список доступных тестов (язык ru/en). Основной тест скрыт, если уже пройден."""
    builder = InlineKeyboardBuilder()
    if not main_test_completed:
        builder.add(InlineKeyboardButton(
            text=t(lang, "tests_main_btn"),
            callback_data="test:main"
        ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "tests_roles_btn"),
        callback_data="test:roles_extra"
    ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "tests_ethics_btn"),
        callback_data="test:ethics_extra"
    ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "tests_goals_btn"),
        callback_data="test:goals_extra"
    ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "tests_risk_btn"),
        callback_data="test:risk_extra"
    ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "tests_decision_btn"),
        callback_data="test:decision_extra"
    ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "tests_comm_btn"),
        callback_data="test:comm_extra"
    ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "tests_about_btn"),
        callback_data="about_tests"
    ))
    builder.add(get_back_button("profile", lang))
    builder.adjust(1)
    return builder.as_markup()


def get_test_info_keyboard(test_type: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Информация о тесте с кнопкой начала (язык ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t(lang, "test_start_btn"),
        callback_data=f"start_test:{test_type}"
    ))
    builder.add(get_back_button("tests", lang))
    builder.adjust(1)
    return builder.as_markup()


def get_test_answer_keyboard(
    answers: dict,
    question_num: int,
    test_type: str,
    is_scale: bool = False,
    lang: str = "ru",
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
    
    builder.add(get_back_button("tests", lang))
    builder.adjust(1)
    return builder.as_markup()


def get_test_progress_keyboard(
    test_type: str,
    current_question: int,
    total_questions: int,
    is_last: bool = False,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Клавиатура с прогрессом теста"""
    builder = InlineKeyboardBuilder()
    
    if is_last:
        builder.add(InlineKeyboardButton(
            text=t(lang, "test_finish_btn"),
            callback_data=f"finish_test:{test_type}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text=f"{t(lang, 'test_next_question_btn')} ({current_question + 1}/{total_questions})",
            callback_data=f"next_question:{test_type}:{current_question + 1}"
        ))
    
    builder.add(get_back_button("tests", lang))
    builder.adjust(1)
    return builder.as_markup()


def get_test_results_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура после завершения теста (язык ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text=t(lang, "btn_my_profile"),
        callback_data="profile"
    ))
    builder.add(InlineKeyboardButton(
        text=t(lang, "btn_other_tests"),
        callback_data="tests"
    ))
    builder.add(get_back_button("main_menu", lang))
    builder.adjust(1)
    return builder.as_markup()
