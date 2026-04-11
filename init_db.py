"""
Скрипт для инициализации базы данных.
Создаёт все необходимые таблицы (вызов create_all идемпотентен — не трогает существующие).
"""

import asyncio
import logging
from sqlalchemy import inspect, text

from repositories.database import engine, Base
from repositories.user_repository import User
from repositories.test_repository import TestResult
from repositories.swipe_repository import Swipe
from repositories.admin_archive_repository import AdminUserArchive
from repositories.subscription_repository import SubscriptionPendingCode
from repositories.events_repository import Event, EventRegistration, EventMatchNotification

logger = logging.getLogger(__name__)


def _migrate_events_detail_json(sync_conn) -> None:
    """Добавляет колонку detail_json к events на существующих SQLite/прочих БД."""
    try:
        insp = inspect(sync_conn)
        if not insp.has_table("events"):
            return
        cols = {c["name"] for c in insp.get_columns("events")}
        if "detail_json" in cols:
            return
        sync_conn.execute(text("ALTER TABLE events ADD COLUMN detail_json TEXT"))
    except Exception:
        logger.exception("Миграция events.detail_json не выполнена")


async def init_database() -> None:
    """Создаёт таблицы БД, если их ещё нет. Безопасно вызывать при каждом запуске."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_events_detail_json)
    logger.info("База данных: таблицы проверены/созданы")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_database())
    print("База данных инициализирована успешно!")
