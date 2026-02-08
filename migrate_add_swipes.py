"""
Миграция: добавление таблицы swipes для свайпов
"""

import asyncio
from repositories.database import engine, Base
from repositories.swipe_repository import Swipe


async def migrate_add_swipes():
    """Создание таблицы swipes"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблица swipes создана успешно!")


if __name__ == "__main__":
    asyncio.run(migrate_add_swipes())
