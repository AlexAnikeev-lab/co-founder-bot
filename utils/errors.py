"""
Обработка ошибок и уведомление администратора
"""

import logging
from typing import Optional
from aiogram import Bot
from config import Config

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


async def notify_admin_new_user(bot: Bot, name: str, telegram_id: int, username: str | None) -> None:
    """Уведомление админам о новой регистрации"""
    un = f"@{username}" if (username and username.strip()) else "—"
    text = (
        "🆕 <b>Новый пользователь</b>\n\n"
        f"👤 {name or 'Без имени'}\n"
        f"📱 ID: <code>{telegram_id}</code>\n"
        f"📧 {un}"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            logger.error("Не удалось отправить уведомление о новом пользователе %s: %s", admin_id, e)


async def handle_error(bot: Optional[Bot], error: Exception, context: str = "") -> None:
    """Обработка ошибки с логированием и уведомлением администратора"""
    error_message = f"{context}\nОшибка: {type(error).__name__}: {str(error)}"
    logger.error(error_message, exc_info=True)
    
    if bot:
        await notify_admin(bot, error_message)
