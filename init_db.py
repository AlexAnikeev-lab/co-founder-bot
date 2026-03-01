"""
Скрипт для инициализации базы данных.
Создаёт все необходимые таблицы (вызов create_all идемпотентен — не трогает существующие).
"""

import asyncio
import logging
from repositories.database import engine, Base
from repositories.user_repository import User
from repositories.test_repository import TestResult
from repositories.swipe_repository import Swipe
from repositories.admin_archive_repository import AdminUserArchive
from repositories.subscription_repository import SubscriptionPendingCode

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Создаёт таблицы БД, если их ещё нет. Безопасно вызывать при каждом запуске."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных: таблицы проверены/созданы")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_database())
    print("База данных инициализирована успешно!")
