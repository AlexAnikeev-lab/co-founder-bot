"""
Обработка ошибок и уведомление администратора
"""

import html
import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import Config
from keyboards.admin import ADM_BAN_PREFIX, ADM_PROFILE_PREFIX

logger = logging.getLogger(__name__)
config = Config()


async def notify_admin(bot: Bot, message: str) -> None:
    """Отправка уведомления всем администраторам"""
    text = f"⚠️ <b>Ошибка в боте</b>\n\n{message}"
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")


def _new_user_notify_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="👤 Анкета",
            callback_data=f"{ADM_PROFILE_PREFIX}{telegram_id}",
        ),
        InlineKeyboardButton(
            text="🔒 Заблокировать",
            callback_data=f"{ADM_BAN_PREFIX}{telegram_id}",
        ),
    )
    builder.adjust(2)
    return builder.as_markup()


def _dm_url_for_user(telegram_id: int, username: str | None) -> str:
    """Ссылка для перехода в ЛС: t.me/username или tg://user?id=."""
    if username and username.strip():
        return f"https://t.me/{username.strip().lstrip('@')}"
    return f"tg://user?id={telegram_id}"


async def notify_admin_event_registration(
    bot: Bot,
    *,
    user_name: str,
    telegram_id: int,
    username: str | None,
    event_title: str,
) -> None:
    """Уведомление админам о регистрации пользователя на мероприятие."""
    from services.demo_test_users import is_demo_telegram_id

    if is_demo_telegram_id(telegram_id):
        return

    display_name = (user_name or "").strip() or "Без имени"
    dm_url = _dm_url_for_user(telegram_id, username)
    name_link = f'<a href="{dm_url}">{html.escape(display_name)}</a>'
    title_safe = html.escape((event_title or "").strip() or "—")
    text = (
        "📅 <b>Регистрация на мероприятие</b>\n\n"
        f"{name_link} зарегистрировался на «<b>{title_safe}</b>»"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(
                "Не удалось отправить уведомление о регистрации на мероприятие %s: %s",
                admin_id,
                e,
            )


async def notify_admin_new_user(bot: Bot, name: str, telegram_id: int, username: str | None) -> None:
    """Уведомление админам о новой регистрации с кнопками просмотра и бана."""
    from services.demo_test_users import is_demo_telegram_id

    if is_demo_telegram_id(telegram_id):
        return
    un = f"@{username}" if (username and username.strip()) else "—"
    text = (
        "🆕 <b>Новый пользователь</b>\n\n"
        f"👤 {name or 'Без имени'}\n"
        f"📱 ID: <code>{telegram_id}</code>\n"
        f"📧 {un}"
    )
    kb = _new_user_notify_keyboard(telegram_id)
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=kb)
        except Exception as e:
            logger.error("Не удалось отправить уведомление о новом пользователе %s: %s", admin_id, e)


async def handle_error(bot: Optional[Bot], error: Exception, context: str = "") -> None:
    """Обработка ошибки с логированием и уведомлением администратора"""
    error_message = f"{context}\nОшибка: {type(error).__name__}: {str(error)}"
    logger.error(error_message, exc_info=True)

    if bot:
        await notify_admin(bot, error_message)
