"""
Репозиторий мероприятий: карточки событий, регистрации и уведомления о мэтчинге.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    """Плоский текст (для старых карточек и превью в админке)."""
    detail_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """JSON с текстом/медиа и entities (цитаты, кастомные эмодзи и т.д.)."""

    price: Mapped[str] = mapped_column(String(64), nullable=False, default="0")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    banner_file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    matching_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EventRegistration(Base):
    __tablename__ = "event_registrations"
    __table_args__ = (UniqueConstraint("event_id", "user_telegram_id", name="uq_event_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_telegram_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )


class EventMatchNotification(Base):
    """
    Фиксирует факт отправки уведомления о мэтче для пользователя на конкретное мероприятие,
    чтобы не слать повторно при перезапуске бота.
    """

    __tablename__ = "event_match_notifications"
    __table_args__ = (UniqueConstraint("event_id", "user_telegram_id", name="uq_event_match_notif"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_telegram_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    matched_with_telegram_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())


@dataclass(frozen=True)
class EventListItem:
    id: int
    position: int
    title: str
    starts_at: datetime
    matching_enabled: bool


class EventsRepository:
    # -------- Events --------
    @staticmethod
    async def get_count(session: AsyncSession) -> int:
        res = await session.execute(select(func.count(Event.id)))
        return int(res.scalar() or 0)

    @staticmethod
    async def list_all(session: AsyncSession) -> list[Event]:
        res = await session.execute(select(Event).order_by(Event.position.asc(), Event.id.asc()))
        return list(res.scalars().all())

    @staticmethod
    async def list_items(session: AsyncSession) -> list[EventListItem]:
        res = await session.execute(
            select(Event.id, Event.position, Event.title, Event.starts_at, Event.matching_enabled)
            .order_by(Event.position.asc(), Event.id.asc())
        )
        out: list[EventListItem] = []
        for row in res.all():
            out.append(
                EventListItem(
                    id=int(row.id),
                    position=int(row.position),
                    title=str(row.title),
                    starts_at=row.starts_at,
                    matching_enabled=bool(row.matching_enabled),
                )
            )
        return out

    @staticmethod
    async def get_by_id(session: AsyncSession, event_id: int) -> Event | None:
        res = await session.execute(select(Event).where(Event.id == event_id))
        return res.scalar_one_or_none()

    @staticmethod
    async def get_by_position(session: AsyncSession, position: int) -> Event | None:
        res = await session.execute(select(Event).where(Event.position == position))
        return res.scalar_one_or_none()

    @staticmethod
    async def get_first(session: AsyncSession) -> Event | None:
        res = await session.execute(select(Event).order_by(Event.position.asc(), Event.id.asc()).limit(1))
        return res.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        title: str,
        description: str,
        detail_json: str | None,
        price: str,
        starts_at: datetime,
        banner_file_id: str | None = None,
        matching_enabled: bool = False,
    ) -> Event:
        # позиция = в конец списка
        res = await session.execute(select(func.max(Event.position)))
        max_pos = int(res.scalar() or 0)
        ev = Event(
            position=max_pos + 1,
            title=title,
            description=description,
            detail_json=detail_json,
            price=price,
            starts_at=starts_at,
            banner_file_id=banner_file_id,
            matching_enabled=matching_enabled,
        )
        session.add(ev)
        await session.commit()
        await session.refresh(ev)
        return ev

    @staticmethod
    async def update_event(
        session: AsyncSession,
        event_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        detail_json: Optional[str] = None,
        price: Optional[str] = None,
        starts_at: Optional[datetime] = None,
        banner_file_id: Optional[str] = None,
        matching_enabled: Optional[bool] = None,
    ) -> None:
        values = {}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if detail_json is not None:
            values["detail_json"] = detail_json
        if price is not None:
            values["price"] = price
        if starts_at is not None:
            values["starts_at"] = starts_at
        if banner_file_id is not None:
            values["banner_file_id"] = banner_file_id
        if matching_enabled is not None:
            values["matching_enabled"] = matching_enabled
        if not values:
            return
        await session.execute(update(Event).where(Event.id == event_id).values(**values))
        await session.commit()

    @staticmethod
    async def delete_expired_events(session: AsyncSession, *, before: datetime) -> int:
        """
        Удаляет мероприятия, у которых starts_at < before (хранится конец календарного дня).
        Удаляет с конца списка позиций, чтобы пересчёт position в delete_event был корректным.
        """
        res = await session.execute(
            select(Event).where(Event.starts_at < before).order_by(Event.position.desc())
        )
        rows: list[Event] = list(res.scalars().all())
        n = 0
        for ev in rows:
            await EventsRepository.delete_event(session, ev.id)
            n += 1
        return n

    @staticmethod
    async def delete_event(session: AsyncSession, event_id: int) -> None:
        ev = await EventsRepository.get_by_id(session, event_id)
        if not ev:
            return
        deleted_pos = int(ev.position)
        await session.execute(delete(Event).where(Event.id == event_id))
        # пересчёт позиций
        await session.execute(
            update(Event).where(Event.position > deleted_pos).values(position=Event.position - 1)
        )
        await session.commit()

    # -------- Registrations --------
    @staticmethod
    async def is_registered(session: AsyncSession, event_id: int, user_telegram_id: int) -> bool:
        res = await session.execute(
            select(EventRegistration.id).where(
                (EventRegistration.event_id == event_id)
                & (EventRegistration.user_telegram_id == user_telegram_id)
            )
        )
        return res.scalar_one_or_none() is not None

    @staticmethod
    async def register_user(session: AsyncSession, event_id: int, user_telegram_id: int) -> bool:
        if await EventsRepository.is_registered(session, event_id, user_telegram_id):
            return False
        session.add(EventRegistration(event_id=event_id, user_telegram_id=user_telegram_id))
        await session.commit()
        return True

    @staticmethod
    async def unregister_user(session: AsyncSession, event_id: int, user_telegram_id: int) -> None:
        await session.execute(
            delete(EventRegistration).where(
                (EventRegistration.event_id == event_id)
                & (EventRegistration.user_telegram_id == user_telegram_id)
            )
        )
        await session.commit()

    @staticmethod
    async def list_registered_user_ids(session: AsyncSession, event_id: int) -> list[int]:
        res = await session.execute(
            select(EventRegistration.user_telegram_id)
            .where(EventRegistration.event_id == event_id)
            .order_by(EventRegistration.registered_at.asc())
        )
        return [int(x) for x in res.scalars().all()]

    @staticmethod
    async def count_registrations(session: AsyncSession, event_id: int) -> int:
        res = await session.execute(
            select(func.count(EventRegistration.id)).where(EventRegistration.event_id == event_id)
        )
        return int(res.scalar() or 0)

    # -------- Notifications --------
    @staticmethod
    async def mark_notified(
        session: AsyncSession,
        event_id: int,
        user_telegram_id: int,
        matched_with_telegram_id: int | None,
    ) -> None:
        session.add(
            EventMatchNotification(
                event_id=event_id,
                user_telegram_id=user_telegram_id,
                matched_with_telegram_id=matched_with_telegram_id,
            )
        )
        await session.commit()

    @staticmethod
    async def was_notified(session: AsyncSession, event_id: int, user_telegram_id: int) -> bool:
        res = await session.execute(
            select(EventMatchNotification.id).where(
                (EventMatchNotification.event_id == event_id)
                & (EventMatchNotification.user_telegram_id == user_telegram_id)
            )
        )
        return res.scalar_one_or_none() is not None

    @staticmethod
    async def get_events_starting_in_window(
        session: AsyncSession,
        *,
        start_from: datetime,
        start_to: datetime,
        matching_enabled_only: bool = True,
    ) -> list[Event]:
        q = select(Event).where((Event.starts_at >= start_from) & (Event.starts_at <= start_to))
        if matching_enabled_only:
            q = q.where(Event.matching_enabled == True)  # noqa: E712
        q = q.order_by(Event.starts_at.asc())
        res = await session.execute(q)
        return list(res.scalars().all())

