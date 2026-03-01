"""
Архив данных пользователей для админов. Заполняется при регистрации, ничего не удаляется.
"""

from typing import Optional, List, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from repositories.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime


class AdminUserArchive(Base):
    """Снимок данных пользователя на момент регистрации (только добавление, без удаления)."""
    __tablename__ = "admin_user_archive"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(index=True)
    username: Mapped[Optional[str]] = mapped_column(default=None)
    phone: Mapped[Optional[str]] = mapped_column(default=None)
    name: Mapped[Optional[str]] = mapped_column(default=None)
    age: Mapped[Optional[int]] = mapped_column(default=None)
    photo_id: Mapped[Optional[str]] = mapped_column(default=None)
    short_description: Mapped[Optional[str]] = mapped_column(default=None)
    full_description: Mapped[Optional[str]] = mapped_column(default=None)
    qualities: Mapped[Optional[str]] = mapped_column(default=None)
    is_minor: Mapped[bool] = mapped_column(default=False)
    archived_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class AdminArchiveRepository:
    """Репозиторий архива пользователей для админ-панели."""

    @staticmethod
    async def create_from_user(session: AsyncSession, user) -> AdminUserArchive:
        """Сохранить снимок пользователя в архив (при регистрации)."""
        record = AdminUserArchive(
            telegram_id=user.telegram_id,
            username=user.username,
            phone=user.phone,
            name=user.name,
            age=user.age,
            photo_id=user.photo_id,
            short_description=user.short_description,
            full_description=user.full_description,
            qualities=user.qualities,
            is_minor=getattr(user, "is_minor", False),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def get_page(
        session: AsyncSession,
        page: int = 0,
        per_page: int = 15,
    ) -> List[AdminUserArchive]:
        """Список записей архива по странице (для кнопок-имён)."""
        offset = page * per_page
        result = await session.execute(
            select(AdminUserArchive)
            .order_by(AdminUserArchive.archived_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_total_count(session: AsyncSession) -> int:
        """Общее количество записей в архиве."""
        r = await session.execute(select(func.count(AdminUserArchive.id)))
        return r.scalar() or 0

    @staticmethod
    async def get_by_telegram_ids_sorted(
        session: AsyncSession,
        telegram_ids: Sequence[int],
    ) -> List[AdminUserArchive]:
        """
        Получить все записи архива по списку telegram_id, отсортированные по archived_at DESC.
        Используется для фильтрации (например, премиум-пользователи с мэтчами).
        """
        if not telegram_ids:
            return []
        result = await session.execute(
            select(AdminUserArchive)
            .where(AdminUserArchive.telegram_id.in_(telegram_ids))
            .order_by(AdminUserArchive.archived_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, archive_id: int) -> Optional[AdminUserArchive]:
        """Получить одну запись по id."""
        result = await session.execute(
            select(AdminUserArchive).where(AdminUserArchive.id == archive_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_first_by_telegram_id(
        session: AsyncSession, telegram_id: int
    ) -> Optional[AdminUserArchive]:
        """Получить последнюю по времени запись архива по telegram_id."""
        result = await session.execute(
            select(AdminUserArchive)
            .where(AdminUserArchive.telegram_id == telegram_id)
            .order_by(AdminUserArchive.archived_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
