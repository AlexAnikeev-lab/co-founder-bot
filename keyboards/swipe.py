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


# Тексты кнопок для reply-клавиатуры в разделе Партнеры (🤝 🏷 👎)
PARTNERS_BTN_LIKE = "🤝"
PARTNERS_BTN_BOOKMARK = "🏷"
PARTNERS_BTN_DISLIKE = "👎"
PARTNERS_BTN_BACK = "◀️ Назад"


def get_partners_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Reply-клавиатура в разделе Партнеры: действия над текущей анкетой и выход.
    Показывается над полем ввода при заходе в Партнеры.
    """
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text=PARTNERS_BTN_LIKE),
        KeyboardButton(text=PARTNERS_BTN_BOOKMARK),
        KeyboardButton(text=PARTNERS_BTN_DISLIKE),
    )
    builder.adjust(3)
    builder.row(KeyboardButton(text=PARTNERS_BTN_BACK))
    return builder.as_markup(resize_keyboard=True)


def get_swipe_keyboard_expand_only(
    swiped_user_id: int,
    expanded: bool = False,
    from_notification: bool = False,
) -> InlineKeyboardMarkup:
    """
    Под карточкой анкеты только кнопка «Развернуть» / «Свернуть».
    Используется в разделе Партнеры, когда действия 🤝 🏷 👎 вынесены в reply-клавиатуру.
    """
    from texts.messages import CARD_EXPAND_BTN, CARD_COLLAPSE_BTN

    builder = InlineKeyboardBuilder()
    if expanded:
        callback = f"collapse_profile_notif:{swiped_user_id}" if from_notification else f"collapse_profile:{swiped_user_id}"
        builder.add(InlineKeyboardButton(text=CARD_COLLAPSE_BTN, callback_data=callback))
    else:
        callback = f"expand_profile_notif:{swiped_user_id}" if from_notification else f"expand_profile:{swiped_user_id}"
        builder.add(InlineKeyboardButton(text=CARD_EXPAND_BTN, callback_data=callback))
    return builder.as_markup()


def get_swipe_keyboard(swiped_user_id: int, expanded: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для свайпов.

    Args:
        swiped_user_id: ID пользователя, на которого свайпают
        expanded: True — показывать кнопку «Свернуть», False — «Развернуть»
    """
    from texts.messages import CARD_EXPAND_BTN, CARD_COLLAPSE_BTN

    builder = InlineKeyboardBuilder()

    # Кнопки действий (без пропуска)
    builder.add(
        InlineKeyboardButton(text="👎", callback_data=f"swipe_dislike:{swiped_user_id}"),
        InlineKeyboardButton(text="🏷", callback_data=f"swipe_bookmark:{swiped_user_id}"),
        InlineKeyboardButton(text="🤝", callback_data=f"swipe_like:{swiped_user_id}"),
    )
    builder.adjust(3)

    # Развернуть / Свернуть
    if expanded:
        builder.row(
            InlineKeyboardButton(
                text=CARD_COLLAPSE_BTN,
                callback_data=f"collapse_profile:{swiped_user_id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=CARD_EXPAND_BTN,
                callback_data=f"expand_profile:{swiped_user_id}",
            )
        )
    return builder.as_markup()


def get_swipe_keyboard_from_notification(swiped_user_id: int, expanded: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для ответа на анкету из уведомления «Вас лайкнули» (кнопка «Посмотреть»).
    После действия не показываем следующую анкету из ленты — только мэтч или «Вы ответили».
    """
    from texts.messages import CARD_EXPAND_BTN, CARD_COLLAPSE_BTN

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="👎", callback_data=f"swipe_notif_dislike:{swiped_user_id}"),
        InlineKeyboardButton(text="🏷", callback_data=f"swipe_notif_bookmark:{swiped_user_id}"),
        InlineKeyboardButton(text="🤝", callback_data=f"swipe_notif_like:{swiped_user_id}"),
    )
    builder.adjust(3)
    if expanded:
        builder.row(
            InlineKeyboardButton(
                text=CARD_COLLAPSE_BTN,
                callback_data=f"collapse_profile_notif:{swiped_user_id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=CARD_EXPAND_BTN,
                callback_data=f"expand_profile_notif:{swiped_user_id}",
            )
        )
    return builder.as_markup()
