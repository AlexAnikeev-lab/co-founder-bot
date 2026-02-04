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


def get_back_button(callback_data: str = "back") -> InlineKeyboardButton:
    """Кнопка Назад"""
    return InlineKeyboardButton(text="⬅ Назад", callback_data=callback_data)


def get_main_menu_button() -> InlineKeyboardButton:
    """Кнопка Главное меню"""
    return InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")


def get_accept_button() -> InlineKeyboardMarkup:
    """Кнопка принятия соглашения"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Принимаю и продолжаю ✅", callback_data="accept_legal"))
    return builder.as_markup()


def get_start_button() -> InlineKeyboardMarkup:
    """Кнопка начала работы"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Газ 🚀", callback_data="start_registration"))
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
