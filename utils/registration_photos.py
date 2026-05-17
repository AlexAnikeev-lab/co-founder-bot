"""
Отправка/редактирование сообщений с фото по шагам регистрации.
Сначала file_id, затем файл с диска; при ошибке — только текст.
"""

import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup

from config import get_registration_photo_path, get_registration_photo_file_id
from utils.telegram_media import edit_message_media_safe, send_photo_safe

logger = logging.getLogger(__name__)


def _photo_input(step_key: str, lang: str = "ru"):
    """Фото: file_id или FSInputFile. На тестовом боте file_id может быть чужим — тогда сработает диск или текст."""
    file_id = get_registration_photo_file_id(step_key, lang=lang)
    if file_id:
        return file_id
    path = get_registration_photo_path(step_key, lang=lang)
    if path:
        return FSInputFile(path)
    return None


async def _send_text_step(
    bot: Bot,
    chat_id: int,
    last_bot_message_id: Optional[int],
    caption: str,
    reply_markup: Optional[InlineKeyboardMarkup],
) -> int:
    if last_bot_message_id is None:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return msg.message_id
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=last_bot_message_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except Exception:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return msg.message_id
    return last_bot_message_id


async def show_registration_step(
    bot: Bot,
    chat_id: int,
    last_bot_message_id: Optional[int],
    step_key: str,
    caption: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    lang: str = "ru",
) -> Optional[int]:
    """
    Показать шаг с фото или текстом. Всегда возвращает message_id (никогда None из-за битого file_id).
    """
    photo = _photo_input(step_key, lang=lang)
    if not photo:
        return await _send_text_step(bot, chat_id, last_bot_message_id, caption, reply_markup)

    if last_bot_message_id is None:
        try:
            msg = await send_photo_safe(
                bot,
                chat_id,
                photo,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return msg.message_id
        except Exception as exc:
            logger.warning("registration step %s photo send failed: %s", step_key, exc)

    if last_bot_message_id is not None:
        edited = await edit_message_media_safe(
            bot,
            chat_id,
            last_bot_message_id,
            photo,
            caption=caption,
            reply_markup=reply_markup,
        )
        if edited:
            return last_bot_message_id

    return await _send_text_step(bot, chat_id, last_bot_message_id, caption, reply_markup)
