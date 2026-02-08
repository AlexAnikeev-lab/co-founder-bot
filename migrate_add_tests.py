"""
Миграция базы данных: добавление таблицы test_results
"""

import asyncio
from repositories.database import engine, Base
from repositories.test_repository import TestResult


async def migrate_add_tests():
    """Добавление таблицы test_results"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблица test_results создана успешно!")


if __name__ == "__main__":
    asyncio.run(migrate_add_tests())
