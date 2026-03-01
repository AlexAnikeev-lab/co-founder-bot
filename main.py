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
from init_db import init_database
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
    
    # Автоматическая инициализация БД при первом запуске (создаёт таблицы, если их нет)
    try:
        await init_database()
    except Exception as e:
        logger.error("Ошибка инициализации БД: %s", e, exc_info=True)
        raise
    
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
    if config.PAYMENT_GROUP_ID is not None:
        logger.info("Группа оплаты включена: PAYMENT_GROUP_ID=%s (сообщения с кодами будут обрабатываться)", config.PAYMENT_GROUP_ID)
    else:
        logger.info("PAYMENT_GROUP_ID не задан — проверка кодов в группе отключена")
    try:
        # Явно включаем message и edited_message, чтобы апдейты из группы оплаты не терялись
        allowed = list(dp.resolve_used_update_types())
        for ut in ("message", "edited_message"):
            if ut not in allowed:
                allowed.append(ut)
        await dp.start_polling(bot, allowed_updates=allowed)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
