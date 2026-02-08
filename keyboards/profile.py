"""
Клавиатуры для профиля
"""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления профиля"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Да, удалить", callback_data="delete_profile_confirm"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="delete_profile_cancel"))
    builder.adjust(1)
    return builder.as_markup()


def get_edit_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура редактирования профиля (без изменения имени)"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📸 Фото", callback_data="edit_photo"))
    builder.add(InlineKeyboardButton(text="✍️ Краткое описание", callback_data="edit_short_description"))
    builder.add(InlineKeyboardButton(text="📝 Полное описание", callback_data="edit_full_description"))
    builder.add(InlineKeyboardButton(text="⭐ Качества", callback_data="edit_qualities"))
    builder.adjust(1)
    return builder.as_markup()
