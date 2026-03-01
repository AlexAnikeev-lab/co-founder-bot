"""
Репозиторий для подписки: ожидающие коды оплаты и проверка подписки.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from repositories.database import Base
from sqlalchemy.orm import Mapped, mapped_column


class SubscriptionPendingCode(Base):
    """Код ожидания оплаты: пользователь нажал «Показать код», отправит его в группу."""
    __tablename__ = "subscription_pending_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    user_id: Mapped[int] = mapped_column(index=True)  # telegram_id
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class SubscriptionRepository:
    """Репозиторий для подписки и кодов оплаты."""

    @staticmethod
    async def add_pending_code(session: AsyncSession, code: str, user_id: int) -> SubscriptionPendingCode:
        """Добавить код ожидания оплаты (старый код пользователя удаляется)."""
        await session.execute(
            delete(SubscriptionPendingCode).where(SubscriptionPendingCode.user_id == user_id)
        )
        row = SubscriptionPendingCode(code=code, user_id=user_id)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row

    @staticmethod
    async def get_user_by_code(session: AsyncSession, code: str) -> Optional[int]:
        """По коду из сообщения в группе вернуть user_id или None."""
        result = await session.execute(
            select(SubscriptionPendingCode.user_id).where(
                SubscriptionPendingCode.code == code.strip()
            )
        )
        row = result.scalar_one_or_none()
        return int(row) if row is not None else None

    @staticmethod
    async def consume_code(session: AsyncSession, code: str) -> Optional[int]:
        """Найти пользователя по коду, удалить код из таблицы, вернуть user_id."""
        user_id = await SubscriptionRepository.get_user_by_code(session, code)
        if user_id is None:
            return None
        await session.execute(
            delete(SubscriptionPendingCode).where(SubscriptionPendingCode.code == code.strip())
        )
        await session.commit()
        return user_id
