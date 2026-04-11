"""
Планировщик мероприятий (раз в N секунд):

1. Удаление карточек, у которых прошёл указанный календарный день (starts_at = конец этого дня).
2. Рассылка мэтчей за ~24 часа до конца этого дня (если включён подбор пар).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from repositories.database import get_session
from repositories.events_repository import EventsRepository
from services.events_matching import notify_pairs_for_event

logger = logging.getLogger(__name__)


async def events_scheduler_loop(bot: Bot, *, poll_seconds: int = 60) -> None:
    """
    Окно: [now+24h, now+24h+poll_seconds] — чтобы поймать событие ровно за 24 часа,
    даже если тик чуть сместился.
    """
    await asyncio.sleep(2)  # дать боту подняться
    while True:
        try:
            now = datetime.now()
            start_from = now + timedelta(hours=24)
            start_to = start_from + timedelta(seconds=poll_seconds)
            async for session in get_session():
                try:
                    removed = await EventsRepository.delete_expired_events(session, before=now)
                    if removed:
                        logger.info("Удалено просроченных мероприятий: %s", removed)
                except Exception as e:
                    logger.exception("Ошибка удаления просроченных мероприятий: %s", e)

                events = await EventsRepository.get_events_starting_in_window(
                    session,
                    start_from=start_from,
                    start_to=start_to,
                    matching_enabled_only=True,
                )
                for ev in events:
                    try:
                        sent = await notify_pairs_for_event(bot, session, ev)
                        if sent:
                            logger.info("Мэтчи по мероприятию event_id=%s отправлены: %s", ev.id, sent)
                    except Exception as e:
                        logger.exception("Ошибка мэтчинга по мероприятию event_id=%s: %s", ev.id, e)
                break
        except Exception as e:
            logger.exception("Ошибка планировщика мероприятий: %s", e)
        await asyncio.sleep(poll_seconds)

