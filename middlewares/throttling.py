"""
Middleware для защиты от спама и флуда
"""

import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

# Хранение времени последнего запроса для каждого пользователя
user_last_request: Dict[int, float] = {}

# Минимальный интервал между запросами (в секундах)
THROTTLE_TIME = 1.0

# Callback_data, для которых не применяем throttle (последовательные нажатия — норма)
THROTTLE_SKIP_PREFIXES = (
    "test_answer:",   # ответ на вопрос теста
    "next_question:", # следующий вопрос
    "finish_test:",   # завершение теста
)


def _should_skip_throttle(event: TelegramObject) -> bool:
    """Пропустить throttle для тестов и других быстрых последовательных callback."""
    if isinstance(event, CallbackQuery) and event.data:
        return any(event.data.startswith(prefix) for prefix in THROTTLE_SKIP_PREFIXES)
    return False


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware для защиты от флуда"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Проверка на флуд"""
        if _should_skip_throttle(event):
            return await handler(event, data)

        user_id = None
        
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            
            if user_id in user_last_request:
                elapsed = time.time() - user_last_request[user_id]
                if elapsed < THROTTLE_TIME:
                    # Слишком частый запрос
                    if isinstance(event, CallbackQuery):
                        await event.answer("⏳ Подожди немного...", show_alert=False)
                    return
            
            user_last_request[user_id] = time.time()
        
        return await handler(event, data)
