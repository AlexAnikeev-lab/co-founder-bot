"""
Middleware для проверки авторизации пользователя
"""

from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from repositories.user_repository import UserRepository

# Обновлять last_seen_at не чаще чем раз в N минут (снижение нагрузки на БД)
LAST_SEEN_UPDATE_INTERVAL_MINUTES = 5


class AuthMiddleware(BaseMiddleware):
    """Middleware для проверки регистрации пользователя. Использует data['session'] от DbSessionMiddleware."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if not session:
            return await handler(event, data)

        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            user = await UserRepository.get_by_telegram_id(session, user_id)
            data["user"] = user
            if user and user.is_registered:
                # Обновляем last_seen_at не чаще чем раз в N минут
                now = datetime.utcnow()
                last = user.last_seen_at
                if last is None or (now - last) > timedelta(minutes=LAST_SEEN_UPDATE_INTERVAL_MINUTES):
                    try:
                        await UserRepository.update(session, user, last_seen_at=now)
                    except Exception:
                        pass

        return await handler(event, data)
