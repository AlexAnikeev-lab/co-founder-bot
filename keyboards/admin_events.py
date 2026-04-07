"""
Клавиатуры админа для управления мероприятиями.
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.admin import AdminCallbackData


class AdminEventsCallbackData(CallbackData, prefix="adm_ev"):
    action: str  # open, add, edit, delete, toggle_match, participants, back
    event_id: int


class AdminEventsEditCallbackData(CallbackData, prefix="adm_eve"):
    action: str  # field
    event_id: int
    field: str  # banner,title,description,price,datetime


def get_admin_events_list_keyboard(events: list[tuple[int, str]],) -> InlineKeyboardMarkup:
    """
    events: [(event_id, label), ...]
    """
    b = InlineKeyboardBuilder()
    for event_id, label in events:
        b.add(
            InlineKeyboardButton(
                text=label,
                callback_data=AdminEventsCallbackData(action="open", event_id=event_id).pack(),
            )
        )
    if events:
        b.adjust(1)
    b.row(
        InlineKeyboardButton(text="➕ Добавить мероприятие", callback_data=AdminEventsCallbackData(action="add", event_id=0).pack())
    )
    b.row(
        InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack())
    )
    return b.as_markup()


def get_admin_event_view_keyboard(event_id: int, matching_enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "🔔 Подбор пар: ВКЛ ✅" if matching_enabled else "🔕 Подбор пар: ВЫКЛ ❌"
    b.add(
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=AdminEventsCallbackData(action="toggle_match", event_id=event_id).pack(),
        )
    )
    b.add(
        InlineKeyboardButton(
            text="👥 Зарегистрировавшиеся",
            callback_data=AdminEventsCallbackData(action="participants", event_id=event_id).pack(),
        )
    )
    b.add(
        InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=AdminEventsCallbackData(action="edit", event_id=event_id).pack(),
        )
    )
    b.add(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=AdminEventsCallbackData(action="delete", event_id=event_id).pack(),
        )
    )
    b.add(
        InlineKeyboardButton(
            text="🔙 К списку мероприятий",
            callback_data=AdminCallbackData(action="events").pack(),
        )
    )
    b.adjust(1)
    return b.as_markup()


def get_admin_event_edit_fields_keyboard(event_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for field, label in (
        ("banner", "🖼 Баннер"),
        ("title", "🏷 Название"),
        ("description", "📝 Описание"),
        ("price", "💰 Цена"),
        ("datetime", "🗓 Дата/время"),
    ):
        b.add(
            InlineKeyboardButton(
                text=label,
                callback_data=AdminEventsEditCallbackData(action="field", event_id=event_id, field=field).pack(),
            )
        )
    b.add(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=AdminEventsCallbackData(action="open", event_id=event_id).pack(),
        )
    )
    b.adjust(1)
    return b.as_markup()


def get_admin_event_delete_confirm_keyboard(event_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.add(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=AdminEventsCallbackData(action="delete_confirm", event_id=event_id).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=AdminEventsCallbackData(action="open", event_id=event_id).pack(),
        ),
    )
    b.adjust(2)
    return b.as_markup()

