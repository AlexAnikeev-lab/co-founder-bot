"""
Репозиторий для работы с пользователями
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
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
    age: Mapped[Optional[int]]
    photo_id: Mapped[Optional[str]]
    is_minor: Mapped[bool] = mapped_column(default=False)  # < 14 лет
    is_registered: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


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
