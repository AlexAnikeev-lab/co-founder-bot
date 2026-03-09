"""
Middleware: одна сессия БД на весь запрос.
Устраняет затор при нагрузке (несколько сессий на один апдейт).
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.database import async_session_maker


class DbSessionMiddleware(BaseMiddleware):
    """Создаёт сессию БД в начале обработки и передаёт в data['session']; закрывает после обработчика."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)
