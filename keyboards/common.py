"""
Общие клавиатуры
"""

from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_back_button(callback_data: str = "back", lang: str = "ru") -> InlineKeyboardButton:
    """Кнопка Назад (язык: ru/en)."""
    from texts.i18n import t
    return InlineKeyboardButton(text=t(lang, "back_inline"), callback_data=callback_data)


def get_main_menu_button(lang: str = "ru") -> InlineKeyboardButton:
    """Кнопка Главное меню (язык: ru/en)."""
    from texts.i18n import t
    return InlineKeyboardButton(text=t(lang, "menu_main"), callback_data="main_menu")


def get_accept_button(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка принятия соглашения (язык интерфейса)."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "accept_and_continue"), callback_data="accept_legal"))
    return builder.as_markup()


def get_start_button(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка первого экрана приветствия (Газ / Go) — язык ru/en."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "welcome_btn_gas"), callback_data="welcome_gas"))
    return builder.as_markup()


def get_welcome_step2_button(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка второго экрана приветствия (Круто! / Cool!) — язык ru/en."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "welcome_btn_cool"), callback_data="start_registration"))
    return builder.as_markup()


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Выбор языка: Русский / English (регистрация)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Русский", callback_data="set_lang_ru"))
    builder.add(InlineKeyboardButton(text="English", callback_data="set_lang_en"))
    builder.adjust(2)
    return builder.as_markup()


def get_profile_language_keyboard() -> InlineKeyboardMarkup:
    """Выбор языка в профиле: Русский / English."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Русский", callback_data="profile_set_lang_ru"))
    builder.add(InlineKeyboardButton(text="English", callback_data="profile_set_lang_en"))
    builder.adjust(2)
    return builder.as_markup()


def get_learning_mode_button() -> InlineKeyboardMarkup:
    """Кнопка для обучающего режима"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Я ещё покажу 😎", callback_data="learning_mode"))
    builder.add(get_back_button("back_to_start"))
    return builder.as_markup()


def get_cancel_button() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def get_skip_and_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопки Пропустить и Отмена для шагов регистрации"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⏭ Пропустить", callback_data="reg_skip"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def get_contact_request_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса контакта"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить контакт", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
