"""
Скрипт для инициализации базы данных
Создаёт все необходимые таблицы
"""

import asyncio
from repositories.database import engine, Base
from repositories.user_repository import User
from repositories.test_repository import TestResult
from repositories.swipe_repository import Swipe
from repositories.admin_archive_repository import AdminUserArchive


async def init_database():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("База данных инициализирована успешно!")


if __name__ == "__main__":
    asyncio.run(init_database())
