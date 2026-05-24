import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from init_db import init_database
from middlewares.db_session import DbSessionMiddleware
from middlewares.auth import AuthMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.delete_previous import BotDeletePrevious, DeletePreviousMiddleware
from handlers import register_all_handlers
from utils.logger import setup_logging
from services.events_scheduler import events_scheduler_loop


async def main() -> None:
    """Основная функция запуска бота"""
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Загрузка конфигурации
    config = Config()
    if config.TEST_MODE:
        logger.warning("TEST_MODE=true — бот использует настройки из .env.test")
    
    #
    try:
        await init_database()
    except Exception as e:
        logger.error("Ошибка инициализации БД: %s", e, exc_info=True)
        raise
    
    bot = BotDeletePrevious(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(DeletePreviousMiddleware())
    dp.callback_query.middleware(DeletePreviousMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Регистрация всех handlers
    register_all_handlers(dp)

    # Планировщик мероприятий (мэтчинг за 24 часа до старта)
    asyncio.create_task(events_scheduler_loop(bot, poll_seconds=60))
    
    # Запуск бота
    logger.info("Бот запущен")
    if config.PAYMENT_GROUP_ID is not None:
        logger.info("Группа оплаты включена: PAYMENT_GROUP_ID=%s (сообщения с кодами будут обрабатываться)", config.PAYMENT_GROUP_ID)
    else:
        logger.info("PAYMENT_GROUP_ID не задан — проверка кодов в группе отключена")
    try:
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
  