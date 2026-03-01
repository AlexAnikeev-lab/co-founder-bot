"""
Клавиатуры для экрана подписки
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from texts.i18n import t


def get_subscription_benefits_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки на экране преимуществ: Оплатить, Назад в профиль."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "subscription_btn_pay"), callback_data="subscription_pay"),
        InlineKeyboardButton(text=t(lang, "subscription_btn_back_profile"), callback_data="subscription_back_profile"),
    )
    builder.adjust(1)
    return builder.as_markup()


def get_subscription_how_to_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки на экране «Как оплатить»: Показать код, Назад."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "subscription_btn_show_code"), callback_data="subscription_show_code"),
        InlineKeyboardButton(text=t(lang, "subscription_btn_back_profile"), callback_data="subscription_back_profile"),
    )
    builder.adjust(1)
    return builder.as_markup()


def get_subscription_code_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки на экране с кодом: Я оплатил, Назад в профиль."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "subscription_btn_i_paid"), callback_data="subscription_i_paid"),
        InlineKeyboardButton(text=t(lang, "subscription_btn_back_profile"), callback_data="subscription_back_profile"),
    )
    builder.adjust(1)
    return builder.as_markup()


def get_subscription_congrats_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """После активации подписки: Вернуться в профиль."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t(lang, "subscription_back_to_profile"), callback_data="subscription_back_profile"),
    )
    return builder.as_markup()
