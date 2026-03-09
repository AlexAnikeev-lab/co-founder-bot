"""
Клавиатуры главного меню
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from texts.i18n import t


def get_main_menu_keyboard(is_minor: bool = False, lang: str = "ru") -> ReplyKeyboardMarkup:
    """Главное меню: первый ряд 📚 🤝 👤, второй ряд ⭐️ Co-founder Subscription (язык: ru/en)."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t(lang, "menu_learning")))
    if not is_minor:
        builder.add(KeyboardButton(text=t(lang, "menu_partners")))
    builder.add(KeyboardButton(text=t(lang, "menu_profile")))
    if not is_minor:
        builder.add(KeyboardButton(text=t(lang, "menu_premium")))
    # Первый ряд: 3 кнопки (📚 🤝 👤), второй ряд: Subscription
    builder.adjust(3 if not is_minor else 2)
    return builder.as_markup(resize_keyboard=True)


# Для совместимости (сопоставление кнопок в хендлерах)
PROFILE_REPLY_TESTS = "📝 Тесты"
PROFILE_REPLY_PEOPLE = "👥 Люди"
PROFILE_REPLY_PREMIUM = "⭐ Co-founder Premium"
PROFILE_REPLY_BACK = "◀️ Назад"


def get_profile_reply_keyboard(is_minor: bool = False, lang: str = "ru") -> ReplyKeyboardMarkup:
    """Reply-клавиатура в разделе Профиль (язык: ru/en)."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t(lang, "profile_tests")))
    if not is_minor:
        builder.add(KeyboardButton(text=t(lang, "profile_people")))
        builder.add(KeyboardButton(text=t(lang, "profile_premium")))
    builder.add(KeyboardButton(text=t(lang, "profile_back")))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_profile_keyboard(is_minor: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    """Под анкетой: Изменить, Удалить профиль, Сменить язык."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "edit_profile"), callback_data="edit_profile"))
    builder.add(InlineKeyboardButton(text=t(lang, "delete_profile"), callback_data="delete_profile"))
    builder.add(InlineKeyboardButton(text=t(lang, "change_language"), callback_data="profile_change_language"))
    builder.adjust(1)
    return builder.as_markup()


def get_people_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Меню раздела Люди (язык: ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "people_favorites"), callback_data="favorites"))
    builder.add(InlineKeyboardButton(text=t(lang, "people_matches"), callback_data="matches"))
    builder.adjust(1)
    return builder.as_markup()
