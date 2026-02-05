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
from keyboards.common import get_back_button


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


def get_profile_keyboard(is_minor: bool = False) -> InlineKeyboardMarkup:
    """Меню профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_profile"))
    builder.add(InlineKeyboardButton(text="📝 Тесты", callback_data="tests"))
    
    if not is_minor:
        builder.add(InlineKeyboardButton(text="👥 Люди", callback_data="people"))
        builder.add(InlineKeyboardButton(text="⭐ Избранные", callback_data="favorites"))
        builder.add(InlineKeyboardButton(text="🤝 Совпадения", callback_data="matches"))
    
    builder.add(InlineKeyboardButton(text="ℹ️ Инструкция по боту", callback_data="bot_instruction"))
    builder.add(InlineKeyboardButton(text="🗑 Удалить профиль", callback_data="delete_profile"))
    
    if not is_minor:
        builder.add(InlineKeyboardButton(text="⭐ Co-founder Premium", callback_data="premium"))
    
    builder.add(get_back_button("main_menu"))
    builder.adjust(1)
    return builder.as_markup()
