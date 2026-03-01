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


def get_accept_and_cancel_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки «Принимаю» и «Отмена» для шага соглашения (язык ru/en)."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "accept_and_continue"), callback_data="accept_legal"))
    builder.add(InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"))
    builder.adjust(2)
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


def get_language_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Выбор языка: Русский / English (регистрация). lang — для подписей кнопок."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "lang_russian"), callback_data="set_lang_ru"))
    builder.add(InlineKeyboardButton(text=t(lang, "lang_english"), callback_data="set_lang_en"))
    builder.adjust(2)
    return builder.as_markup()


def get_profile_language_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Выбор языка в профиле: Русский / English."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "lang_russian"), callback_data="profile_set_lang_ru"))
    builder.add(InlineKeyboardButton(text=t(lang, "lang_english"), callback_data="profile_set_lang_en"))
    builder.adjust(2)
    return builder.as_markup()


def get_learning_mode_button(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки для обучающего режима (язык ru/en): «Я ещё покажу» и Отмена."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "learning_btn_show"), callback_data="learning_mode"))
    builder.add(InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"))
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_button(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка отмены (язык ru/en)."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"))
    return builder.as_markup()


def get_skip_and_cancel_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки Пропустить и Отмена для шагов регистрации (язык ru/en)."""
    from texts.i18n import t
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="reg_skip"))
    builder.add(InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def get_contact_request_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Клавиатура для запроса контакта (язык: ru/en)."""
    from texts.i18n import t
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_send_contact"), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
