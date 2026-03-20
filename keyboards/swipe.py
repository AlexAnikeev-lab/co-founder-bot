"""
Клавиатуры для свайпов (поиск партнеров)
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# Тексты кнопок для reply-клавиатуры в разделе Партнеры (🤝 🌟 👎)
PARTNERS_BTN_LIKE = "🤝"
PARTNERS_BTN_BOOKMARK = "🌟"
PARTNERS_BTN_DISLIKE = "👎"


PARTNERS_BTN_SUPER_LIKE = "🔥"


def get_partners_reply_keyboard(lang: str = "ru", has_super_like: bool = False) -> ReplyKeyboardMarkup:
    """
    Reply-клавиатура в разделе Партнеры: действия над текущей анкетой и выход.
    has_super_like: показывать кнопку супер-лайка (для подписчиков, пока не использован).
    """
    from texts.i18n import t
    builder = ReplyKeyboardBuilder()
    if has_super_like:
        builder.add(KeyboardButton(text=PARTNERS_BTN_SUPER_LIKE))
    builder.add(
        KeyboardButton(text=PARTNERS_BTN_LIKE),
        KeyboardButton(text=PARTNERS_BTN_BOOKMARK),
        KeyboardButton(text=PARTNERS_BTN_DISLIKE),
    )
    builder.adjust(3 if not has_super_like else 2, 2 if has_super_like else 1)
    builder.row(KeyboardButton(text=t(lang, "profile_back")))
    return builder.as_markup(resize_keyboard=True)


def get_swipe_keyboard_expand_only(
    swiped_user_id: int,
    expanded: bool = False,
    from_notification: bool = False,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """
    Под карточкой анкеты только кнопка «Развернуть» / «Свернуть».
    lang — язык для подписи кнопки.
    """
    from texts.i18n import t
    expand_btn = t(lang, "card_expand_btn")
    collapse_btn = t(lang, "card_collapse_btn")
    builder = InlineKeyboardBuilder()
    if expanded:
        callback = f"collapse_profile_notif:{swiped_user_id}" if from_notification else f"collapse_profile:{swiped_user_id}"
        builder.add(InlineKeyboardButton(text=collapse_btn, callback_data=callback))
    else:
        callback = f"expand_profile_notif:{swiped_user_id}" if from_notification else f"expand_profile:{swiped_user_id}"
        builder.add(InlineKeyboardButton(text=expand_btn, callback_data=callback))
    return builder.as_markup()


def get_swipe_keyboard(
    swiped_user_id: int,
    expanded: bool = False,
    lang: str = "ru",
    has_super_like: bool = False,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для свайпов. has_super_like: добавить кнопку 🔥 супер-лайка (для подписчиков).
    """
    from texts.i18n import t
    expand_btn = t(lang, "card_expand_btn")
    collapse_btn = t(lang, "card_collapse_btn")
    builder = InlineKeyboardBuilder()
    if has_super_like:
        builder.add(InlineKeyboardButton(text=t(lang, "card_super_like_btn"), callback_data=f"swipe_super_like:{swiped_user_id}"))
    builder.add(
        InlineKeyboardButton(text="🤝", callback_data=f"swipe_like:{swiped_user_id}"),
        InlineKeyboardButton(text="🌟", callback_data=f"swipe_bookmark:{swiped_user_id}"),
        InlineKeyboardButton(text="👎", callback_data=f"swipe_dislike:{swiped_user_id}"),
    )
    builder.adjust(3 if not has_super_like else 2, 2 if has_super_like else 1)
    if expanded:
        builder.row(
            InlineKeyboardButton(text=collapse_btn, callback_data=f"collapse_profile:{swiped_user_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text=expand_btn, callback_data=f"expand_profile:{swiped_user_id}")
        )
    return builder.as_markup()


def get_swipe_keyboard_from_notification(
    swiped_user_id: int, expanded: bool = False, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура для ответа на анкету из уведомления «Вас лайкнули»."""
    from texts.i18n import t
    expand_btn = t(lang, "card_expand_btn")
    collapse_btn = t(lang, "card_collapse_btn")
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🤝", callback_data=f"swipe_notif_like:{swiped_user_id}"),
        InlineKeyboardButton(text="🌟", callback_data=f"swipe_notif_bookmark:{swiped_user_id}"),
        InlineKeyboardButton(text="👎", callback_data=f"swipe_notif_dislike:{swiped_user_id}"),
    )
    builder.adjust(3)
    if expanded:
        builder.row(
            InlineKeyboardButton(
                text=collapse_btn,
                callback_data=f"collapse_profile_notif:{swiped_user_id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=expand_btn,
                callback_data=f"expand_profile_notif:{swiped_user_id}",
            )
        )
    return builder.as_markup()


def get_favorites_keyboard(
    swiped_user_id: int,
    index: int,
    total: int,
    expanded: bool = False,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра избранного: 🤝 👎, развернуть/свернуть, Назад/Далее."""
    from texts.i18n import t
    expand_btn = t(lang, "card_expand_btn")
    collapse_btn = t(lang, "card_collapse_btn")
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🤝", callback_data=f"swipe_like:{swiped_user_id}"),
        InlineKeyboardButton(text="👎", callback_data=f"swipe_dislike:{swiped_user_id}"),
    )
    builder.adjust(2)
    if expanded:
        builder.row(
            InlineKeyboardButton(
                text=collapse_btn,
                callback_data=f"collapse_favorites:{swiped_user_id}:{index}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=expand_btn,
                callback_data=f"expand_favorites:{swiped_user_id}:{index}",
            )
        )
    nav_buttons = []
    if index > 0:
        nav_buttons.append(
            InlineKeyboardButton(text=t(lang, "favorites_back"), callback_data=f"favorites_prev:{index}")
        )
    if index < total - 1:
        nav_buttons.append(
            InlineKeyboardButton(text=t(lang, "favorites_next"), callback_data=f"favorites_next:{index}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)
    builder.row(
        InlineKeyboardButton(
            text=t(lang, "favorites_back_to_people"),
            callback_data="people",
        ),
    )
    return builder.as_markup()
