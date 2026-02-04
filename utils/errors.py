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
    """Отправка уведомления администратору"""
    try:
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"⚠️ <b>Ошибка в боте</b>\n\n{message}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление администратору: {e}")


async def handle_error(bot: Optional[Bot], error: Exception, context: str = "") -> None:
    """Обработка ошибки с логированием и уведомлением администратора"""
    error_message = f"{context}\nОшибка: {type(error).__name__}: {str(error)}"
    logger.error(error_message, exc_info=True)
    
    if bot:
        await notify_admin(bot, error_message)
