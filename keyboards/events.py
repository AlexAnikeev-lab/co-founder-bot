"""
Клавиатуры раздела «Мероприятия» (пользовательский UI).
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import get_back_button
from texts.i18n import t


class EventsCallbackData(CallbackData, prefix="ev"):
    action: str  # open, join
    event_id: int


def get_events_list_keyboard(*, lang: str, items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    Список мероприятий: каждая кнопка открывает карточку.

    items: [(event_id, button_text), ...]
    """
    builder = InlineKeyboardBuilder()
    for event_id, button_text in items:
        builder.add(
            InlineKeyboardButton(
                text=button_text,
                callback_data=EventsCallbackData(action="open", event_id=event_id).pack(),
            )
        )

    builder.add(get_back_button("main_menu", lang))
    builder.adjust(1)
    return builder.as_markup()


def get_event_card_keyboard(
    *,
    lang: str,
    event_id: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="💼 " + t(lang, "events_btn_join"),
            callback_data=EventsCallbackData(action="join", event_id=event_id).pack(),
        )
    )

    builder.add(get_back_button("events_list", lang))
    builder.adjust(1)
    return builder.as_markup()


def get_event_pair_profile_keyboard(*, lang: str, partner_id: int, dm_link: str) -> InlineKeyboardMarkup:
    """Кнопки карточки подобранной пары: Подробнее + Написать в ЛС."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=t(lang, "card_more"),
            callback_data=f"event_pair_more:{partner_id}",
        )
    )
    builder.add(
        InlineKeyboardButton(
            text=t(lang, "btn_go_to_dm"),
            url=dm_link,
        )
    )
    builder.adjust(1)
    return builder.as_markup()


def get_event_pair_details_keyboard(*, lang: str, dm_link: str) -> InlineKeyboardMarkup:
    """Кнопка под сообщением с деталями пары: только Написать в ЛС."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=t(lang, "btn_go_to_dm"),
            url=dm_link,
        )
    )
    builder.adjust(1)
    return builder.as_markup()
