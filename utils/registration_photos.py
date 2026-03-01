"""
Отправка/редактирование сообщений с фото по шагам регистрации.
Сначала используется file_id (мгновенно), если нет — файл с диска (медленнее).
"""

from typing import Optional
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup

from config import get_registration_photo_path, get_registration_photo_file_id


def _photo_input(step_key: str, lang: str = "ru"):
    """Фото для отправки: file_id (строка) или FSInputFile(path). По языку выбирается папка (ru → photos, en → photos_engls)."""
    file_id = get_registration_photo_file_id(step_key, lang=lang)
    if file_id:
        return file_id
    path = get_registration_photo_path(step_key, lang=lang)
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
    lang: str = "ru",
) -> Optional[int]:
    """
    Показать шаг с фото (по file_id или по файлу). lang задаёт папку: ru → photos, en → photos_engls.
    Возвращает message_id или None при fallback на текст.
    """
    photo = _photo_input(step_key, lang=lang)
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
