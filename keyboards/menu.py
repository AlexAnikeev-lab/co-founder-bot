"""
Клавиатуры главного меню
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.common import get_back_button


def get_main_menu_keyboard(is_minor: bool = False) -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    if is_minor:
        # Меню для несовершеннолетних
        builder.add(InlineKeyboardButton(text="📚 Обучение", callback_data="learning"))
        builder.add(InlineKeyboardButton(text="ℹ️ Информация", callback_data="info"))
        builder.add(InlineKeyboardButton(text="👤 Профиль", callback_data="profile"))
    else:
        # Полное меню
        builder.add(InlineKeyboardButton(text="📚 Обучение", callback_data="learning"))
        builder.add(InlineKeyboardButton(text="💕 Знакомства", callback_data="dating"))
        builder.add(InlineKeyboardButton(text="ℹ️ Информация", callback_data="info"))
        builder.add(InlineKeyboardButton(text="👤 Профиль", callback_data="profile"))
        builder.add(InlineKeyboardButton(text="⭐ Co-founder Premium", callback_data="premium"))
    
    builder.adjust(1)
    return builder.as_markup()


def get_profile_keyboard(is_minor: bool = False) -> InlineKeyboardMarkup:
    """Меню профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_profile"))
    builder.add(InlineKeyboardButton(text="📝 Тесты", callback_data="tests"))
    
    if not is_minor:
        builder.add(InlineKeyboardButton(text="👥 Люди", callback_data="people"))
        builder.add(InlineKeyboardButton(text="⭐ Избранные", callback_data="favorites"))
        builder.add(InlineKeyboardButton(text="💕 Мэтчи", callback_data="matches"))
    
    builder.add(InlineKeyboardButton(text="ℹ️ Инструкция по боту", callback_data="bot_instruction"))
    builder.add(InlineKeyboardButton(text="🗑 Удалить профиль", callback_data="delete_profile"))
    
    if not is_minor:
        builder.add(InlineKeyboardButton(text="⭐ Co-founder Premium", callback_data="premium"))
    
    builder.add(get_back_button("main_menu"))
    builder.adjust(1)
    return builder.as_markup()
