"""
Клавиатуры для профиля (язык: ru/en)
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts.i18n import t


def get_delete_confirm_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления профиля (язык: ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "delete_yes"), callback_data="delete_profile_confirm"))
    builder.add(InlineKeyboardButton(text=t(lang, "delete_cancel"), callback_data="delete_profile_cancel"))
    builder.adjust(1)
    return builder.as_markup()


def get_edit_profile_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура редактирования профиля (язык: ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "edit_photo"), callback_data="edit_photo"))
    builder.add(InlineKeyboardButton(text=t(lang, "edit_short_description"), callback_data="edit_short_description"))
    builder.add(InlineKeyboardButton(text=t(lang, "edit_full_description"), callback_data="edit_full_description"))
    builder.add(InlineKeyboardButton(text=t(lang, "edit_quality_1"), callback_data="edit_quality_1"))
    builder.add(InlineKeyboardButton(text=t(lang, "edit_quality_2"), callback_data="edit_quality_2"))
    builder.add(InlineKeyboardButton(text=t(lang, "edit_quality_3"), callback_data="edit_quality_3"))
    builder.adjust(1)
    return builder.as_markup()
