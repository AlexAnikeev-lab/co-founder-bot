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
    action: str  # open, nav, join
    event_id: int


class EventsNavCallbackData(CallbackData, prefix="evn"):
    action: str  # prev, next
    position: int


def get_event_card_keyboard(
    *,
    lang: str,
    event_id: int,
    position: int,
    total: int,
    show_prev: bool,
    show_next: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="💼 " + t(lang, "events_btn_join"),
            callback_data=EventsCallbackData(action="join", event_id=event_id).pack(),
        )
    )

    nav_row: list[InlineKeyboardButton] = []
    if show_prev:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ " + t(lang, "events_btn_prev"),
                callback_data=EventsNavCallbackData(action="prev", position=position).pack(),
            )
        )
    if show_next:
        nav_row.append(
            InlineKeyboardButton(
                text=t(lang, "events_btn_next") + " ➡️",
                callback_data=EventsNavCallbackData(action="next", position=position).pack(),
            )
        )
    if nav_row:
        builder.row(*nav_row)

    builder.add(get_back_button("main_menu", lang))
    builder.adjust(1)
    return builder.as_markup()

