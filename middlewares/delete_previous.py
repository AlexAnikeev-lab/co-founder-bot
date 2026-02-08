"""
Удаление предыдущего сообщения бота при отправке нового.
Хранит последнюю «пачку» сообщений по chat_id и удаляет её перед новой отправкой.
"""

import logging
from contextvars import ContextVar
from typing import Callable, Dict, Any, Awaitable, List

from aiogram import Bot, BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

# Хранилище: chat_id -> список message_id последней отправки
_last_message_ids: Dict[int, List[int]] = {}
# Текущая пачка сообщений в рамках одного ответа (заполняется при send)
_current_batch: ContextVar[List[int]] = ContextVar("delete_previous_batch", default=[])


def _chat_id_from_event(event: TelegramObject) -> int | None:
    """Получить chat_id из сообщения или callback."""
    if isinstance(event, Message):
        return event.chat.id if event.chat else None
    if isinstance(event, CallbackQuery) and event.message:
        return event.message.chat.id if event.message.chat else None
    return None


class DeletePreviousMiddleware(BaseMiddleware):
    """Перед обработчиком очищает текущую пачку; после — сохраняет её в хранилище по chat_id."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        chat_id = _chat_id_from_event(event)
        _current_batch.set([])
        try:
            return await handler(event, data)
        finally:
            if chat_id is not None:
                try:
                    batch = _current_batch.get()
                    if batch:
                        _last_message_ids[chat_id] = list(batch)
                except LookupError:
                    pass


class BotDeletePrevious(Bot):
    """Бот, перед каждой отправкой удаляющий предыдущие сообщения в этом чате."""

    async def send_message(self, chat_id: int, **kwargs) -> Message:
        await _delete_previous_messages(self, chat_id)
        msg = await super().send_message(chat_id, **kwargs)
        _append_message_id(chat_id, msg.message_id)
        return msg

    async def send_photo(self, chat_id: int, **kwargs) -> Message:
        await _delete_previous_messages(self, chat_id)
        msg = await super().send_photo(chat_id, **kwargs)
        _append_message_id(chat_id, msg.message_id)
        return msg


async def _delete_previous_messages(bot: Bot, chat_id: int) -> None:
    """Удалить все сообщения из последней пачки в чате."""
    ids = _last_message_ids.get(chat_id) or []
    for mid in ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception as e:
            logger.debug("Не удалось удалить сообщение %s в чате %s: %s", mid, chat_id, e)
    if ids:
        _last_message_ids[chat_id] = []


def _append_message_id(chat_id: int, message_id: int) -> None:
    """Добавить message_id в текущую пачку (по контексту чата не привязываем — один контекст на запрос)."""
    try:
        batch = _current_batch.get()
        batch.append(message_id)
    except LookupError:
        _current_batch.set([message_id])
