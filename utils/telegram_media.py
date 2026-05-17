"""
Безопасная отправка медиа в Telegram.

file_id привязан к боту: при смене BOT_TOKEN старые id не работают.
При ошибке отправляем тот же текст без фото.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message

logger = logging.getLogger(__name__)

_INVALID_FILE_MARKERS = (
    "wrong file identifier",
    "file identifier",
    "file_id",
    "photo_invalid",
    "can't use file",
    "failed to get file",
    "file not found",
    "invalid file",
)


def is_invalid_telegram_file_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _INVALID_FILE_MARKERS)


async def send_photo_safe(
    bot: Bot,
    chat_id: int,
    photo: Any,
    *,
    caption: Optional[str] = None,
    parse_mode: str = "HTML",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    **kwargs: Any,
) -> Message:
    """send_photo с fallback на текст, если file_id/фото недоступны."""
    try:
        return await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs,
        )
    except (TelegramBadRequest, Exception) as exc:
        logger.warning("send_photo → текст (chat=%s): %s", chat_id, exc)
        return await bot.send_message(
            chat_id=chat_id,
            text=caption or " ",
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )


async def answer_photo_safe(
    message: Message,
    photo: Any,
    *,
    caption: Optional[str] = None,
    parse_mode: str = "HTML",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    **kwargs: Any,
) -> Message:
    """answer_photo с fallback на текст."""
    try:
        return await message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs,
        )
    except (TelegramBadRequest, Exception) as exc:
        logger.warning("answer_photo → текст: %s", exc)
        return await message.answer(
            text=caption or " ",
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )


async def send_profile_card(
    message: Message,
    *,
    photo_id: Optional[str],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
) -> Message:
    """Карточка анкеты: фото + подпись или только текст."""
    if photo_id:
        return await answer_photo_safe(
            message,
            photo_id,
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    return await message.answer(
        text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


async def bot_send_profile_card(
    bot: Bot,
    chat_id: int,
    *,
    photo_id: Optional[str],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
) -> Message:
    if photo_id:
        return await send_photo_safe(
            bot,
            chat_id,
            photo_id,
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    return await bot.send_message(
        chat_id,
        text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


async def edit_message_media_safe(
    bot: Bot,
    chat_id: int,
    message_id: int,
    photo: Any,
    *,
    caption: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> bool:
    """True — медиа обновлено; False — нужен fallback (текст/new message)."""
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(media=photo, caption=caption, parse_mode=parse_mode),
        )
        if reply_markup is not None:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup,
            )
        return True
    except (TelegramBadRequest, Exception) as exc:
        logger.warning("edit_message_media failed: %s", exc)
        return False
