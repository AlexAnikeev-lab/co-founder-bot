"""
Миграция: создание таблицы admin_user_archive для архива пользователей (админ-панель).
Запустить один раз после обновления кода.
"""

import asyncio
from repositories.database import engine, Base
from repositories.admin_archive_repository import AdminUserArchive


async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблица admin_user_archive создана (или уже существовала).")


if __name__ == "__main__":
    asyncio.run(migrate())
