"""
Мэтчинг участников мероприятия (за 24 часа до начала).

Использует те же данные, что и «Поиск партнёров»: основной тест + заполненная анкета.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.events_repository import EventsRepository, Event
from repositories.user_repository import UserRepository, User
from repositories.test_repository import TestResultRepository, TestResult
from services.compatibility_service import CompatibilityService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PairMatch:
    a_id: int
    b_id: int
    score: int


def _get_user_profile(test_result: TestResult) -> Optional[dict]:
    if not test_result or not test_result.main_test_completed:
        return None
    return {
        "hustler_percent": test_result.hustler_percent or 0,
        "hacker_percent": test_result.hacker_percent or 0,
        "hipster_percent": test_result.hipster_percent or 0,
        "ethics_score": test_result.ethics_score or 0,
        "goals_score": test_result.goals_score or 0,
        "risk_score": test_result.risk_score or 0,
        "decision_score": test_result.decision_score or 0,
        "comm_score": test_result.comm_score or 0,
        "profile_label": test_result.profile_label,
    }


def _dm_link(user: User) -> str:
    if user.username:
        uname = (user.username or "").strip().lstrip("@")
        if uname:
            return f"https://t.me/{uname}"
    return f"tg://user?id={user.telegram_id}"


async def build_pairs_for_event(session: AsyncSession, event: Event) -> list[PairMatch]:
    user_ids = await EventsRepository.list_registered_user_ids(session, event.id)
    if len(user_ids) < 2:
        return []

    # Берём только тех, кому ещё не слали уведомление по этому мероприятию
    eligible: list[int] = []
    for uid in user_ids:
        if not await EventsRepository.was_notified(session, event.id, uid):
            eligible.append(uid)
    if len(eligible) < 2:
        return []

    users_map = await UserRepository.get_by_telegram_ids(session, eligible)
    test_map = await TestResultRepository.get_by_user_ids(session, eligible)

    # фильтруем как в партнёрах: есть тест и заполнены поля анкеты
    filtered: list[int] = []
    profiles: dict[int, dict] = {}
    for uid in eligible:
        u = users_map.get(uid)
        tr = test_map.get(uid)
        if not u or not tr:
            continue
        if (u.ban_status or "none") == "full":
            continue
        if not (u.short_description and u.full_description and u.qualities):
            continue
        p = _get_user_profile(tr)
        if not p:
            continue
        profiles[uid] = p
        filtered.append(uid)
    if len(filtered) < 2:
        return []

    pairs: list[PairMatch] = []
    # O(n^2) — нормально для списка участников мероприятия
    for i in range(len(filtered)):
        for j in range(i + 1, len(filtered)):
            a, b = filtered[i], filtered[j]
            score = CompatibilityService.calculate_compatibility(profiles[a], profiles[b])
            pairs.append(PairMatch(a_id=a, b_id=b, score=int(score)))

    pairs.sort(key=lambda x: x.score, reverse=True)

    used: set[int] = set()
    chosen: list[PairMatch] = []
    for p in pairs:
        if p.a_id in used or p.b_id in used:
            continue
        used.add(p.a_id)
        used.add(p.b_id)
        chosen.append(p)
    return chosen


async def notify_pairs_for_event(bot: Bot, session: AsyncSession, event: Event) -> int:
    """
    Возвращает количество пользователей, которым отправлено уведомление (по 2 на пару).
    """
    from handlers.swipe import format_user_profile  # локально, чтобы не создавать циклические импорты при старте

    pairs = await build_pairs_for_event(session, event)
    if not pairs:
        return 0

    users_needed: set[int] = set()
    for p in pairs:
        users_needed.add(p.a_id)
        users_needed.add(p.b_id)

    users_map = await UserRepository.get_by_telegram_ids(session, list(users_needed))
    sent_users = 0

    for p in pairs:
        a = users_map.get(p.a_id)
        b = users_map.get(p.b_id)
        if not a or not b:
            continue

        # Сообщение A про B
        try:
            profile_text_b = format_user_profile(b, compatibility=None, expanded=True, lang=getattr(a, "language", None) or "ru")
            text_a = (
                "У нас есть мэтч!\n"
                "Мы подобрали тебе идеальную компанию для завтрашнего мероприятия:\n\n"
                f"{profile_text_b}\n\n"
                f"Ссылка на профиль: {_dm_link(b)}"
            )
            await bot.send_message(chat_id=a.telegram_id, text=text_a, parse_mode="HTML")
            await EventsRepository.mark_notified(session, event.id, a.telegram_id, b.telegram_id)
            sent_users += 1
        except Exception as e:
            logger.warning("Не удалось отправить мэтч A=%s по event=%s: %s", a.telegram_id, event.id, e)

        # Сообщение B про A
        try:
            profile_text_a = format_user_profile(a, compatibility=None, expanded=True, lang=getattr(b, "language", None) or "ru")
            text_b = (
                "У нас есть мэтч!\n"
                "Мы подобрали тебе идеальную компанию для завтрашнего мероприятия:\n\n"
                f"{profile_text_a}\n\n"
                f"Ссылка на профиль: {_dm_link(a)}"
            )
            await bot.send_message(chat_id=b.telegram_id, text=text_b, parse_mode="HTML")
            await EventsRepository.mark_notified(session, event.id, b.telegram_id, a.telegram_id)
            sent_users += 1
        except Exception as e:
            logger.warning("Не удалось отправить мэтч B=%s по event=%s: %s", b.telegram_id, event.id, e)

    return sent_users

