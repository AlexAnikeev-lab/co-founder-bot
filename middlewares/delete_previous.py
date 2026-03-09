"""
Удаление предыдущего сообщения бота при отправке нового.
Удаление выполняется в фоне, чтобы не блокировать отправку ответа (нагрузка 400+).
"""

import asyncio
import logging
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import Bot, BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

# Хранилище: chat_id -> список message_id (ограничиваем размер пачки)
_last_message_ids: Dict[int, List[int]] = {}
_MAX_BATCH_SIZE = 10
_current_batch: ContextVar[List[int]] = ContextVar("delete_previous_batch", default=[])


def protect_message(chat_id: int, message_id: int) -> None:
    """Убрать сообщение из списка на удаление — при следующей отправке бота это сообщение не будет удалено."""
    ids = _last_message_ids.get(chat_id)
    if not ids:
        return
    new_ids = [mid for mid in ids if mid != message_id]
    if new_ids != ids:
        _last_message_ids[chat_id] = new_ids if new_ids else []


def _chat_id_from_event(event: TelegramObject) -> int | None:
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
                        _last_message_ids[chat_id] = list(batch[-_MAX_BATCH_SIZE:])
                except LookupError:
                    pass


async def _delete_previous_messages(bot: Bot, chat_id: int, message_ids: List[int]) -> None:
    """Удалить сообщения в фоне (не блокирует отправку нового)."""
    for mid in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception as e:
            logger.debug("Не удалось удалить сообщение %s в чате %s: %s", mid, chat_id, e)


class BotDeletePrevious(Bot):
    """Бот, удаляющий предыдущие сообщения в чате. Удаление в фоне — не блокирует отправку."""

    async def send_message(self, chat_id: int, text: str = None, **kwargs) -> Message:
        if text is not None:
            kwargs["text"] = text
        ids = _last_message_ids.get(chat_id) or []
        if ids:
            _last_message_ids[chat_id] = []
            asyncio.create_task(_delete_previous_messages(self, chat_id, ids))
        msg = await super().send_message(chat_id, **kwargs)
        _append_message_id(chat_id, msg.message_id)
        return msg

    async def send_photo(self, chat_id: int, photo: Any = None, **kwargs) -> Message:
        if photo is not None:
            kwargs["photo"] = photo
        ids = _last_message_ids.get(chat_id) or []
        if ids:
            _last_message_ids[chat_id] = []
            asyncio.create_task(_delete_previous_messages(self, chat_id, ids))
        msg = await super().send_photo(chat_id, **kwargs)
        _append_message_id(chat_id, msg.message_id)
        return msg


def _append_message_id(chat_id: int, message_id: int) -> None:
    try:
        batch = _current_batch.get()
        batch.append(message_id)
    except LookupError:
        _current_batch.set([message_id])
