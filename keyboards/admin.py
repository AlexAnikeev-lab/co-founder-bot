"""
Клавиатуры админ-панели
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from keyboards.common import get_back_button


class AdminCallbackData(CallbackData, prefix="admin"):
    """CallbackData для админ-панели"""
    action: str  # menu, clear_swipes, clear_confirm, clear_cancel, back


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели: статистика, архив пользователей, очистка лайков/дизлайков"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="🔄 Обновить статистику",
            callback_data=AdminCallbackData(action="refresh").pack()
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="👥 Посмотреть всех пользователей",
            callback_data=AdminCallbackData(action="users").pack()
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="🗑 Очистить лайки и дизлайки",
            callback_data=AdminCallbackData(action="clear_swipes").pack()
        )
    )
    builder.add(get_back_button("main_menu"))
    builder.adjust(1)
    return builder.as_markup()


# Пагинация и просмотр пользователя — callback_data с числом (страница или id)
USERS_PAGE_PREFIX = "adm_p:"
USER_VIEW_PREFIX = "adm_u:"


def get_admin_users_page_keyboard(
    records: list,
    page: int,
    total_count: int,
    per_page: int = 15,
) -> InlineKeyboardMarkup:
    """Клавиатура: до 15 кнопок с именами + Назад/Далее по страницам."""
    builder = InlineKeyboardBuilder()
    for r in records:
        label = (r.name or f"ID{r.telegram_id}" or f"#{r.id}").strip()
        if len(label) > 35:
            label = label[:32] + "..."
        builder.add(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{USER_VIEW_PREFIX}{r.id}"
            )
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"{USERS_PAGE_PREFIX}{page - 1}"))
    if (page + 1) * per_page < total_count:
        nav.append(InlineKeyboardButton(text="Далее ➡", callback_data=f"{USERS_PAGE_PREFIX}{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.add(InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack()))
    return builder.as_markup()


def get_admin_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения очистки лайков и дизлайков"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="✅ Да, очистить",
            callback_data=AdminCallbackData(action="clear_confirm").pack()
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=AdminCallbackData(action="clear_cancel").pack()
        )
    )
    builder.adjust(2)
    return builder.as_markup()
