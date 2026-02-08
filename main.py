"""
Co-founder Bot - Telegram бот для знакомств и поиска партнёров
Главный файл запуска бота
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from middlewares.auth import AuthMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.delete_previous import BotDeletePrevious, DeletePreviousMiddleware
from handlers import register_all_handlers
from utils.logger import setup_logging


async def main() -> None:
    """Основная функция запуска бота"""
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Загрузка конфигурации
    config = Config()
    
    # Инициализация бота и диспетчера (BotDeletePrevious удаляет предыдущие сообщения при новой отправке)
    bot = BotDeletePrevious(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация middleware
    dp.message.middleware(DeletePreviousMiddleware())
    dp.callback_query.middleware(DeletePreviousMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Регистрация всех handlers
    register_all_handlers(dp)
    
    # Запуск бота
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
