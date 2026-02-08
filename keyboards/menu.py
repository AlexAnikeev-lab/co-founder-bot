"""
Клавиатуры главного меню
"""

from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_menu_keyboard(is_minor: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню (прикрепленное к клавиатуре)"""
    builder = ReplyKeyboardBuilder()
    
    if is_minor:
        # Меню для несовершеннолетних
        builder.add(KeyboardButton(text="📚 Обучение"))
        builder.add(KeyboardButton(text="ℹ️ Информация"))
        builder.add(KeyboardButton(text="👤 Профиль"))
    else:
        # Полное меню
        builder.add(KeyboardButton(text="📚 Обучение"))
        builder.add(KeyboardButton(text="🤝 Партнеры"))
        builder.add(KeyboardButton(text="ℹ️ Информация"))
        builder.add(KeyboardButton(text="👤 Профиль"))
        builder.add(KeyboardButton(text="⭐ Co-founder Premium"))
    
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup(resize_keyboard=True)


# Тексты кнопок reply-меню в разделе Профиль
PROFILE_REPLY_TESTS = "📝 Тесты"
PROFILE_REPLY_PEOPLE = "👥 Люди"
PROFILE_REPLY_PREMIUM = "⭐ Co-founder Premium"
PROFILE_REPLY_BACK = "◀️ Назад"


def get_profile_reply_keyboard(is_minor: bool = False) -> ReplyKeyboardMarkup:
    """Reply-клавиатура в разделе Профиль: Тесты, Люди, Premium, Назад."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=PROFILE_REPLY_TESTS))
    if not is_minor:
        builder.add(KeyboardButton(text=PROFILE_REPLY_PEOPLE))
        builder.add(KeyboardButton(text=PROFILE_REPLY_PREMIUM))
    builder.add(KeyboardButton(text=PROFILE_REPLY_BACK))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_profile_keyboard(is_minor: bool = False) -> InlineKeyboardMarkup:
    """Под анкетой: Изменить, Удалить профиль (без кнопки Назад)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_profile"))
    builder.add(InlineKeyboardButton(text="🗑 Удалить профиль", callback_data="delete_profile"))
    builder.adjust(1)
    return builder.as_markup()


def get_people_keyboard() -> InlineKeyboardMarkup:
    """Меню раздела Люди"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🔍 Поиск людей", callback_data="search_people"))
    builder.add(InlineKeyboardButton(text="⭐ Избранные", callback_data="favorites"))
    builder.add(InlineKeyboardButton(text="🤝 Совпадения", callback_data="matches"))
    builder.adjust(1)
    return builder.as_markup()
