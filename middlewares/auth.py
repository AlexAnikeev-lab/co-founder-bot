"""
Middleware для проверки авторизации пользователя
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from repositories.user_repository import UserRepository
from repositories.database import get_session


class AuthMiddleware(BaseMiddleware):
    """Middleware для проверки регистрации пользователя"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Проверка регистрации пользователя"""
        user_id = None
        
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            
            # Получение пользователя из базы данных
            async for session in get_session():
                user = await UserRepository.get_by_telegram_id(session, user_id)
                data["user"] = user
                break
        
        return await handler(event, data)
