"""
Отправка/редактирование сообщений с фото по шагам регистрации.
Сначала используется file_id (мгновенно), если нет — файл с диска (медленнее).
"""

from typing import Optional
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup

from config import get_registration_photo_path, get_registration_photo_file_id


def _photo_input(step_key: str):
    """Фото для отправки: file_id (строка) или FSInputFile(path)."""
    file_id = get_registration_photo_file_id(step_key)
    if file_id:
        return file_id
    path = get_registration_photo_path(step_key)
    if path:
        return FSInputFile(path)
    return None


async def show_registration_step(
    bot: Bot,
    chat_id: int,
    last_bot_message_id: Optional[int],
    step_key: str,
    caption: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Optional[int]:
    """
    Показать шаг с фото (по file_id или по файлу).
    Возвращает message_id или None при fallback на текст.
    """
    photo = _photo_input(step_key)
    if not photo:
        return None

    try:
        if last_bot_message_id is None:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return msg.message_id

        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=last_bot_message_id,
            media=InputMediaPhoto(
                media=photo,
                caption=caption,
                parse_mode="HTML",
            ),
        )
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=last_bot_message_id,
            reply_markup=reply_markup,
        )
        return last_bot_message_id
    except Exception:
        return None
