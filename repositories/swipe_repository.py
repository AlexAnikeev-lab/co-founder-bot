"""
Репозиторий для работы со свайпами (лайки, дизлайки, пропуски)
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, UniqueConstraint, delete, func
from sqlalchemy.orm import aliased
from repositories.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timedelta


class Swipe(Base):
    """Модель свайпа (лайк/дизлайк/пропуск)"""
    __tablename__ = "swipes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    swiper_id: Mapped[int] = mapped_column(index=True)  # telegram_id того, кто свайпнул
    swiped_id: Mapped[int] = mapped_column(index=True)  # telegram_id того, на кого свайпнули
    
    action: Mapped[str] = mapped_column()  # "like", "dislike", "skip", "bookmark"
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Уникальный индекс: один пользователь может свайпнуть другого только один раз
    __table_args__ = (
        UniqueConstraint('swiper_id', 'swiped_id', name='unique_swipe'),
    )


class SwipeRepository:
    """Репозиторий для работы со свайпами"""
    
    @staticmethod
    async def create_swipe(
        session: AsyncSession,
        swiper_id: int,
        swiped_id: int,
        action: str
    ) -> Swipe:
        """Создание свайпа"""
        # Проверяем, не было ли уже такого свайпа
        existing = await SwipeRepository.get_swipe(session, swiper_id, swiped_id)
        if existing:
            # Обновляем существующий
            existing.action = action
            existing.created_at = datetime.utcnow()
            await session.commit()
            await session.refresh(existing)
            return existing
        
        swipe = Swipe(
            swiper_id=swiper_id,
            swiped_id=swiped_id,
            action=action
        )
        session.add(swipe)
        await session.commit()
        await session.refresh(swipe)
        return swipe
    
    @staticmethod
    async def get_swipe(
        session: AsyncSession,
        swiper_id: int,
        swiped_id: int
    ) -> Optional[Swipe]:
        """Получение свайпа"""
        result = await session.execute(
            select(Swipe).where(
                and_(
                    Swipe.swiper_id == swiper_id,
                    Swipe.swiped_id == swiped_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def count_in_last_7_days(
        session: AsyncSession,
        swiper_id: int,
        action: str,
    ) -> int:
        """Количество свайпов с действием action за последние 7 дней (по created_at)."""
        since = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            select(func.count(Swipe.id)).where(
                and_(
                    Swipe.swiper_id == swiper_id,
                    Swipe.action == action,
                    Swipe.created_at >= since,
                )
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_swiped_user_ids(
        session: AsyncSession,
        swiper_id: int
    ) -> List[int]:
        """Получение списка ID пользователей, на которых уже свайпнули"""
        result = await session.execute(
            select(Swipe.swiped_id).where(Swipe.swiper_id == swiper_id)
        )
        return [row[0] for row in result.fetchall()]

    @staticmethod
    async def get_bookmarked_user_ids(
        session: AsyncSession,
        swiper_id: int
    ) -> List[int]:
        """Список telegram_id пользователей в избранном (action=bookmark), по дате добавления (новые первые)."""
        result = await session.execute(
            select(Swipe.swiped_id)
            .where(
                and_(Swipe.swiper_id == swiper_id, Swipe.action == "bookmark")
            )
            .order_by(Swipe.created_at.desc())
        )
        return [row[0] for row in result.fetchall()]
    
    @staticmethod
    async def check_mutual_like(
        session: AsyncSession,
        user1_id: int,
        user2_id: int
    ) -> bool:
        """Проверка взаимного лайка (совпадения)"""
        swipe1 = await SwipeRepository.get_swipe(session, user1_id, user2_id)
        swipe2 = await SwipeRepository.get_swipe(session, user2_id, user1_id)
        
        return (
            swipe1 is not None and swipe1.action == "like" and
            swipe2 is not None and swipe2.action == "like"
        )
    
    @staticmethod
    async def get_likes_received(
        session: AsyncSession,
        user_id: int
    ) -> List[Swipe]:
        """Получение всех лайков, полученных пользователем"""
        result = await session.execute(
            select(Swipe).where(
                and_(
                    Swipe.swiped_id == user_id,
                    Swipe.action == "like"
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_mutual_matches(
        session: AsyncSession,
        user_id: int
    ) -> List[int]:
        """Список telegram_id пользователей, с которыми взаимный лайк (совпадение)"""
        # Все лайки, которые поставил user_id
        my_likes = await session.execute(
            select(Swipe.swiped_id).where(
                and_(Swipe.swiper_id == user_id, Swipe.action == "like")
            )
        )
        my_liked_ids = [row[0] for row in my_likes.fetchall()]
        if not my_liked_ids:
            return []
        # Среди них те, кто тоже лайкнул user_id
        result = await session.execute(
            select(Swipe.swiper_id).where(
                and_(
                    Swipe.swiped_id == user_id,
                    Swipe.action == "like",
                    Swipe.swiper_id.in_(my_liked_ids)
                )
            )
        )
        return [row[0] for row in result.fetchall()]

    @staticmethod
    async def get_swipe_stats_for_user(
        session: AsyncSession,
        user_id: int,
    ) -> dict:
        """
        Статистика свайпов для одного пользователя:
        likes_given, likes_received, dislikes_given, matches (list of (telegram_id, name)).
        """
        # Лайки, которые поставил
        r1 = await session.execute(
            select(func.count(Swipe.id)).where(
                and_(Swipe.swiper_id == user_id, Swipe.action == "like")
            )
        )
        likes_given = r1.scalar() or 0
        # Лайки, полученные
        r2 = await session.execute(
            select(func.count(Swipe.id)).where(
                and_(Swipe.swiped_id == user_id, Swipe.action == "like")
            )
        )
        likes_received = r2.scalar() or 0
        # Дизлайки, которые поставил
        r3 = await session.execute(
            select(func.count(Swipe.id)).where(
                and_(Swipe.swiper_id == user_id, Swipe.action == "dislike")
            )
        )
        dislikes_given = r3.scalar() or 0
        # Мэтчи (с кем)
        match_ids = await SwipeRepository.get_mutual_matches(session, user_id)
        return {
            "likes_given": likes_given,
            "likes_received": likes_received,
            "dislikes_given": dislikes_given,
            "match_ids": match_ids,
        }

    @staticmethod
    async def get_users_with_mutual_matches(session: AsyncSession) -> list[int]:
        """
        Список telegram_id пользователей, у которых есть хотя бы одно совпадение (взаимный лайк).
        Используется в админ-панели для фильтрации.
        """
        s1 = aliased(Swipe)
        s2 = aliased(Swipe)
        result = await session.execute(
            select(func.distinct(s1.swiper_id)).join(
                s2,
                and_(
                    s1.swiper_id == s2.swiped_id,
                    s1.swiped_id == s2.swiper_id,
                    s1.action == "like",
                    s2.action == "like",
                ),
            )
        )
        return [row[0] for row in result.fetchall()]

    @staticmethod
    async def get_swipe_stats(session: AsyncSession) -> Dict[str, Any]:
        """Статистика по свайпам: количество лайков, дизлайков, пропусков, закладок и всего записей"""
        total = await session.execute(select(func.count(Swipe.id)))
        total_count = total.scalar() or 0

        like_result = await session.execute(
            select(func.count(Swipe.id)).where(Swipe.action == "like")
        )
        likes = like_result.scalar() or 0

        dislike_result = await session.execute(
            select(func.count(Swipe.id)).where(Swipe.action == "dislike")
        )
        dislikes = dislike_result.scalar() or 0

        skip_result = await session.execute(
            select(func.count(Swipe.id)).where(Swipe.action == "skip")
        )
        skips = skip_result.scalar() or 0

        bookmark_result = await session.execute(
            select(func.count(Swipe.id)).where(Swipe.action == "bookmark")
        )
        bookmarks = bookmark_result.scalar() or 0

        return {
            "total": total_count,
            "likes": likes,
            "dislikes": dislikes,
            "skips": skips,
            "bookmarks": bookmarks,
        }

    @staticmethod
    async def clear_likes_and_dislikes(session: AsyncSession) -> int:
        """Удалить все записи с action like и dislike. Возвращает количество удалённых записей."""
        result = await session.execute(
            delete(Swipe).where(Swipe.action.in_(["like", "dislike"]))
        )
        await session.commit()
        return result.rowcount or 0

    @staticmethod
    async def clear_all_swipes(session: AsyncSession) -> int:
        """Удалить все записи свайпов (лайки, дизлайки, пропуски, закладки). Возвращает количество удалённых."""
        result = await session.execute(delete(Swipe))
        await session.commit()
        return result.rowcount or 0
