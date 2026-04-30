"""
Репозиторий для работы с пользователями
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from repositories.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[Optional[str]]
    phone: Mapped[Optional[str]]
    name: Mapped[Optional[str]]
    city: Mapped[Optional[str]]
    age: Mapped[Optional[int]]
    photo_id: Mapped[Optional[str]]
    short_description: Mapped[Optional[str]]  # Краткое описание
    full_description: Mapped[Optional[str]]  # Полное описание
    qualities: Mapped[Optional[str]]  # 3 главных качества (через запятую)
    is_minor: Mapped[bool] = mapped_column(default=False)  # < 14 лет
    is_registered: Mapped[bool] = mapped_column(default=False)
    ban_status: Mapped[str] = mapped_column(default="none")  # none | shadow | full
    language: Mapped[str] = mapped_column(default="ru")  # ru | en — язык интерфейса (анкета не переводится)
    # Подписка
    subscription_active: Mapped[bool] = mapped_column(default=False)
    subscription_until: Mapped[Optional[datetime]] = mapped_column(default=None)  # None = бессрочно
    super_like_used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(default=None)  # последняя активность


class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_telegram_ids(session: AsyncSession, telegram_ids: list[int]) -> dict[int, User]:
        """Пакетная загрузка пользователей по telegram_id. Возвращает {telegram_id: User}."""
        if not telegram_ids:
            return {}
        result = await session.execute(
            select(User).where(User.telegram_id.in_(telegram_ids))
        )
        users = result.scalars().all()
        return {u.telegram_id: u for u in users}
    
    @staticmethod
    async def create(session: AsyncSession, telegram_id: int, username: Optional[str] = None) -> User:
        """Создание нового пользователя"""
        user = User(
            telegram_id=telegram_id,
            username=username
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def update(session: AsyncSession, user: User, **kwargs) -> User:
        """Обновление данных пользователя"""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def delete(session: AsyncSession, user: User) -> None:
        """Удаление пользователя"""
        await session.delete(user)
        await session.commit()

    @staticmethod
    async def get_total_count(session: AsyncSession) -> int:
        """Общее количество пользователей в базе"""
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0

    @staticmethod
    async def get_registered_count(session: AsyncSession) -> int:
        """Количество пользователей с завершённой регистрацией"""
        result = await session.execute(
            select(func.count(User.id)).where(User.is_registered == True)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_premium_by_telegram_ids(
        session: AsyncSession,
        telegram_ids: list[int],
    ) -> list[User]:
        """Получить пользователей с активной подпиской из указанного набора telegram_id."""
        if not telegram_ids:
            return []
        result = await session.execute(
            select(User).where(
                and_(
                    User.telegram_id.in_(telegram_ids),
                    User.subscription_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_registered_page(
        session: AsyncSession,
        page: int = 0,
        per_page: int = 15,
    ) -> list[User]:
        """Страница актуальных пользователей (зарегистрированных), по дате создания."""
        offset = page * per_page
        result = await session.execute(
            select(User)
            .where(User.is_registered == True)  # noqa: E712
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        return list(result.scalars().all())

    @staticmethod
    async def search_users(
        session: AsyncSession,
        query: str,
    ) -> list[User]:
        """Поиск по ID, username, телефону, имени (подстрока без учёта регистра)."""
        q = query.strip()
        if not q:
            return []
        # Число → ищем telegram_id
        try:
            tid = int(q)
            r = await session.execute(
                select(User).where(User.telegram_id == tid)
            )
            u = r.scalar_one_or_none()
            return [u] if u else []
        except ValueError:
            pass
        pattern = f"%{q}%"
        result = await session.execute(
            select(User).where(
                or_(
                    User.username.ilike(pattern),
                    User.phone.ilike(pattern),
                    User.name.ilike(pattern),
                )
            ).order_by(User.created_at.desc()).limit(50)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_active_in_last_days(
        session: AsyncSession,
        days: int,
    ) -> list[User]:
        """Пользователи, активные в последние N дней (last_seen_at или updated_at >= since)."""
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.is_registered == True,  # noqa: E712
                    or_(
                        User.last_seen_at >= since,
                        User.updated_at >= since,
                    ),
                )
            )
            .order_by(User.updated_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_inactive_more_than_days(
        session: AsyncSession,
        days: int,
    ) -> list[User]:
        """Пользователи, не активные более N дней (updated_at < since)."""
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.is_registered == True,  # noqa: E712
                    User.updated_at < since,
                )
            )
            .order_by(User.updated_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_registered_since(
        session: AsyncSession,
        days: int,
    ) -> list[User]:
        """Новые за последние N дней (по created_at)."""
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.is_registered == True,  # noqa: E712
                    User.created_at >= since,
                )
            )
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_premium_expiring_in_days(
        session: AsyncSession,
        days: int,
    ) -> list[User]:
        """Премиум, истекающий в ближайшие N дней (subscription_until не None)."""
        from datetime import timedelta
        now = datetime.utcnow()
        until = now + timedelta(days=days)
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.subscription_active == True,  # noqa: E712
                    User.subscription_until != None,
                    User.subscription_until >= now,
                    User.subscription_until <= until,
                )
            )
            .order_by(User.subscription_until.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_registered_for_export(session: AsyncSession) -> list[User]:
        """Все зарегистрированные пользователи для экспорта."""
        result = await session.execute(
            select(User)
            .where(User.is_registered == True)  # noqa: E712
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())
