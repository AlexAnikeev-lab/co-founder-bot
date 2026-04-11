"""
Middleware для защиты от спама и флуда.
Потокобезопасно при высокой нагрузке (lock по user_id, ограничение размера словаря).
"""

import asyncio
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

# Минимальный интервал между запросами (в секундах)
THROTTLE_TIME = 1.0
# Максимум записей в словаре (очистка старых при переполнении)
THROTTLE_DICT_MAX_SIZE = 10_000

# Время последнего запроса: user_id -> timestamp
_user_last_request: Dict[int, float] = {}
_lock = asyncio.Lock()

# Callback_data, для которых не применяем throttle (последовательные нажатия — норма)
THROTTLE_SKIP_PREFIXES = (
    "test_answer:",
    "next_question:",
    "finish_test:",
)


async def _should_skip_throttle(event: TelegramObject, data: Dict[str, Any]) -> bool:
    if isinstance(event, CallbackQuery) and event.data:
        if any(event.data.startswith(prefix) for prefix in THROTTLE_SKIP_PREFIXES):
            return True
    # Для шагов регистрации не применяем throttling к сообщениям,
    # чтобы ввод не "проглатывался" при быстром ответе пользователя.
    if isinstance(event, Message):
        state = data.get("state")
        if state:
            try:
                current = await state.get_state()
            except Exception:
                current = None
            if current and (
                "RegistrationStates" in current
                or "AdminEventsStates" in current
            ):
                return True
    return False


def _cleanup_old_entries() -> None:
    """Оставить только недавние записи, если словарь разросся."""
    if len(_user_last_request) <= THROTTLE_DICT_MAX_SIZE:
        return
    now = time.time()
    cutoff = now - 3600  # старше часа удаляем
    to_remove = [uid for uid, ts in _user_last_request.items() if ts < cutoff]
    for uid in to_remove:
        _user_last_request.pop(uid, None)


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware для защиты от флуда (потокобезопасный при 400+ пользователях)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if await _should_skip_throttle(event, data):
            return await handler(event, data)

        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        async with _lock:
            _cleanup_old_entries()
            last = _user_last_request.get(user_id)
            now = time.time()
            if last is not None and (now - last) < THROTTLE_TIME:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Подожди немного...", show_alert=False)
                return
            _user_last_request[user_id] = now

        return await handler(event, data)
