"""
Клавиатуры админ-панели
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from keyboards.common import get_back_button


class AdminCallbackData(CallbackData, prefix="admin"):
    """CallbackData для админ-панели"""
    action: str  # menu, clear_swipes, clear_confirm, clear_cancel, back, search, activity, activity_7, activity_30, inactive_30, new_users, new_1, new_7, new_30, broadcast, broadcast_*, premium_expiring, export_csv


class AdminPremiumCallbackData(CallbackData, prefix="adm_prem"):
    """CallbackData для управления премиум-подпиской пользователя из админки"""
    action: str  # ask_give, ask_remove, confirm_give, confirm_remove, cancel
    telegram_id: int


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="🔄 Обновить статистику",
            callback_data=AdminCallbackData(action="refresh").pack()
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="🔍 Поиск пользователя",
            callback_data=AdminCallbackData(action="search").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="👥 Пользователи",
            callback_data=AdminCallbackData(action="users").pack()
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="💎 Премиум с мэтчами",
            callback_data=AdminCallbackData(action="users_premium_matches").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="📢 Массовая рассылка",
            callback_data=AdminCallbackData(action="broadcast").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="📈 Активность",
            callback_data=AdminCallbackData(action="activity").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="🆕 Новые за период",
            callback_data=AdminCallbackData(action="new_users").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="📅 Премиум по дате",
            callback_data=AdminCallbackData(action="premium_expiring").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="📥 Экспорт в CSV",
            callback_data=AdminCallbackData(action="export_csv").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="📅 Мероприятия",
            callback_data=AdminCallbackData(action="events").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="⚙️ Лимиты",
            callback_data=AdminCallbackData(action="limits").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="🧪 Демо-пользователи",
            callback_data=AdminCallbackData(action="demo_users").pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="🗑 Очистить свайпы",
            callback_data=AdminCallbackData(action="clear_swipes").pack()
        )
    )
    builder.add(get_back_button("main_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_admin_limits_keyboard(current_likes_limit: int) -> InlineKeyboardMarkup:
    """Клавиатура экрана «Лимиты»: текущий лимит лайков и кнопки для выбора нового (0 = без лимита)."""
    builder = InlineKeyboardBuilder()
    # Варианты: 0 (без лимита), 1, 3, 5, 10
    for n in (0, 1, 3, 5, 10):
        label = "Без лимита" if n == 0 else str(n)
        if n == current_likes_limit:
            label = f"• {label} (сейчас)"
        builder.add(
            InlineKeyboardButton(
                text=label,
                callback_data=AdminCallbackData(action=f"set_likes_limit_{n}").pack(),
            )
        )
    builder.adjust(2, 2, 1)  # два ряда по 2, потом один
    builder.add(InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack()))
    return builder.as_markup()


USERS_LIVE_PAGE_PREFIX = "adm_lp:"
USER_LIVE_VIEW_PREFIX = "adm_lu:"
USERS_PAGE_PREFIX = "adm_p:"
USERS_PREMIUM_PAGE_PREFIX = "adm_pp:"
USER_VIEW_PREFIX = "adm_u:"
# Действия с пользователем по telegram_id
ADM_BAN_PREFIX = "adm_ban:"
ADM_WRITE_PREFIX = "adm_write:"
ADM_PROFILE_PREFIX = "adm_profile:"
ADM_PROFILE_BACK_PREFIX = "adm_profile_back:"
ADM_SWIPES_PREFIX = "adm_sw:"


def get_admin_user_view_keyboard(
    telegram_id: int,
    ban_status: str,
    has_premium: bool = False,
) -> InlineKeyboardMarkup:
    """Клавиатура карточки пользователя: бан, премиум, написать, анкета, открыть чат, назад."""
    builder = InlineKeyboardBuilder()
    status = (ban_status or "none").strip().lower()
    if status == "full":
        ban_text = "🔴 Полный бан (нажать: снять)"
    elif status == "shadow":
        ban_text = "🟠 Теневой бан (нажать: полный бан)"
    else:
        ban_text = "🟢 Не заблокирован (нажать: теневой бан)"
    builder.add(
        InlineKeyboardButton(text=ban_text, callback_data=f"{ADM_BAN_PREFIX}{telegram_id}")
    )
    if has_premium:
        prem_text = "💎 Премиум активен (нажать: снять)"
        action = "ask_remove"
    else:
        prem_text = "💎 Выдать премиум"
        action = "ask_give"
    builder.add(
        InlineKeyboardButton(
            text=prem_text,
            callback_data=AdminPremiumCallbackData(action=action, telegram_id=telegram_id).pack(),
        )
    )
    builder.add(
        InlineKeyboardButton(text="✉️ Написать", callback_data=f"{ADM_WRITE_PREFIX}{telegram_id}"),
        InlineKeyboardButton(text="👤 Анкета", callback_data=f"{ADM_PROFILE_PREFIX}{telegram_id}"),
    )
    builder.add(
        InlineKeyboardButton(
            text="💬 Открыть чат",
            url=f"tg://user?id={telegram_id}",
        ),
    )
    builder.add(
        InlineKeyboardButton(
            text="📊 Свайпы/мэтчи",
            callback_data=f"{ADM_SWIPES_PREFIX}{telegram_id}",
        ),
    )
    builder.adjust(1, 2)
    builder.add(InlineKeyboardButton(text="🔙 К списку", callback_data=AdminCallbackData(action="users").pack()))
    return builder.as_markup()


def get_admin_live_users_page_keyboard(
    users: list,
    page: int,
    total_count: int,
    per_page: int = 15,
) -> InlineKeyboardMarkup:
    """
    Клавиатура списка актуальных пользователей (по живой таблице users):
    имена как кнопки, пагинация и большая кнопка «Посмотреть архив».
    """
    builder = InlineKeyboardBuilder()
    for u in users:
        label = (u.name or f"ID{u.telegram_id}").strip()
        if len(label) > 35:
            label = label[:32] + "..."
        builder.add(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{USER_LIVE_VIEW_PREFIX}{u.telegram_id}",
            )
        )
    # Имена — всегда по одной кнопке в строке
    if users:
        builder.adjust(1)
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data=f"{USERS_LIVE_PAGE_PREFIX}{page - 1}",
            )
        )
    if (page + 1) * per_page < total_count:
        nav.append(
            InlineKeyboardButton(
                text="Далее ➡",
                callback_data=f"{USERS_LIVE_PAGE_PREFIX}{page + 1}",
            )
        )
    if nav:
        builder.row(*nav)

    # Большая кнопка для перехода в архив — отдельной строкой
    archive_btn = InlineKeyboardButton(
        text="📁 Посмотреть архив",
        callback_data=AdminCallbackData(action="users_archive").pack(),
    )
    builder.row(archive_btn)

    # Кнопка возврата в админ-панель — отдельной строкой
    back_btn = InlineKeyboardButton(
        text="🔙 К админ-панели",
        callback_data=AdminCallbackData(action="back").pack(),
    )
    builder.row(back_btn)
    return builder.as_markup()


def get_admin_users_page_keyboard(
    records: list,
    page: int,
    total_count: int,
    per_page: int = 15,
    prefix: str = USERS_PAGE_PREFIX,
) -> InlineKeyboardMarkup:
    """Клавиатура: до 15 кнопок с именами + Назад/Далее по страницам.

    prefix определяет пространство callback_data для пагинации и просмотра
    (обычный архив или фильтр по премиум-пользователям с мэтчами).
    """
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
    # Имена в архиве — тоже по одной в строке
    if records:
        builder.adjust(1)
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data=f"{prefix}{page - 1}",
            )
        )
    if (page + 1) * per_page < total_count:
        nav.append(
            InlineKeyboardButton(
                text="Далее ➡",
                callback_data=f"{prefix}{page + 1}",
            )
        )
    if nav:
        builder.row(*nav)

    # Кнопка перехода к актуальным пользователям
    live_btn = InlineKeyboardButton(
        text="👥 Актуальные",
        callback_data=AdminCallbackData(action="users").pack(),
    )
    builder.row(live_btn)

    # Кнопка возврата в админ-панель
    back_btn = InlineKeyboardButton(
        text="🔙 К админ-панели",
        callback_data=AdminCallbackData(action="back").pack(),
    )
    builder.row(back_btn)
    return builder.as_markup()


def get_admin_activity_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода активности."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🟢 Активные за 7 дней", callback_data=AdminCallbackData(action="activity_7").pack()),
        InlineKeyboardButton(text="🟢 Активные за 30 дней", callback_data=AdminCallbackData(action="activity_30").pack()),
    )
    builder.add(
        InlineKeyboardButton(text="🔴 Не заходили 30+ дней", callback_data=AdminCallbackData(action="inactive_30").pack()),
    )
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallbackData(action="back").pack()))
    builder.adjust(1)
    return builder.as_markup()


def get_admin_new_users_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода для новых пользователей."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Сегодня", callback_data=AdminCallbackData(action="new_1").pack()),
        InlineKeyboardButton(text="За неделю", callback_data=AdminCallbackData(action="new_7").pack()),
        InlineKeyboardButton(text="За месяц", callback_data=AdminCallbackData(action="new_30").pack()),
    )
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallbackData(action="back").pack()))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора фильтра для рассылки."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📢 Всем", callback_data=AdminCallbackData(action="broadcast_all").pack()),
    )
    builder.add(
        InlineKeyboardButton(text="🟢 Активные за 7 дней", callback_data=AdminCallbackData(action="broadcast_active_7").pack()),
        InlineKeyboardButton(text="🟢 Активные за 30 дней", callback_data=AdminCallbackData(action="broadcast_active_30").pack()),
    )
    builder.add(
        InlineKeyboardButton(text="💎 Премиум", callback_data=AdminCallbackData(action="broadcast_premium").pack()),
        InlineKeyboardButton(text="🆕 Новые за неделю", callback_data=AdminCallbackData(action="broadcast_new_7").pack()),
    )
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallbackData(action="back").pack()))
    builder.adjust(1)
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


def get_admin_demo_users_keyboard() -> InlineKeyboardMarkup:
    """Управление демо-пользователями."""
    builder = InlineKeyboardBuilder()
    for n in (5, 10, 20):
        builder.add(
            InlineKeyboardButton(
                text=f"➕ Добавить {n}",
                callback_data=AdminCallbackData(action=f"demo_seed_{n}").pack(),
            )
        )
    builder.adjust(3)
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить всех демо",
            callback_data=AdminCallbackData(action="demo_delete_ask").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack())
    )
    return builder.as_markup()


def get_admin_demo_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="✅ Да, удалить всех",
            callback_data=AdminCallbackData(action="demo_delete_confirm").pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=AdminCallbackData(action="demo_users").pack(),
        ),
    )
    builder.adjust(2)
    return builder.as_markup()


def get_admin_premium_confirm_keyboard(telegram_id: int, give: bool) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения выдачи/снятия премиум-подписки"""
    builder = InlineKeyboardBuilder()
    if give:
        yes_action = "confirm_give"
        yes_text = "✅ Да, выдать премиум"
    else:
        yes_action = "confirm_remove"
        yes_text = "✅ Да, снять премиум"
    builder.add(
        InlineKeyboardButton(
            text=yes_text,
            callback_data=AdminPremiumCallbackData(action=yes_action, telegram_id=telegram_id).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=AdminPremiumCallbackData(action="cancel", telegram_id=telegram_id).pack(),
        ),
    )
    builder.adjust(2)
    return builder.as_markup()
