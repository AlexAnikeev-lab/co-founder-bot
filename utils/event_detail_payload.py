"""
Сериализация и отправка «карточки» мероприятия как в Telegram:
текст + MessageEntity (цитаты, кастомные эмодзи и т.д.), фото/видео с подписью.

Соответствует Bot API: при передаче entities не используется parse_mode
(см. sendMessage: entities и parse_mode взаимоисключающи).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message, MessageEntity
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)

PAYLOAD_VERSION = 1


def _dump_entities(entities: list[MessageEntity] | None) -> list[dict[str, Any]]:
    if not entities:
        return []
    out: list[dict[str, Any]] = []
    for e in entities:
        try:
            out.append(e.model_dump(mode="json", exclude_none=True))
        except Exception:
            logger.warning("Не удалось сериализовать entity: %s", e, exc_info=True)
    return out


def _load_entities(raw: list[dict[str, Any]] | None) -> list[MessageEntity] | None:
    if not raw:
        return None
    entities: list[MessageEntity] = []
    for item in raw:
        try:
            entities.append(MessageEntity.model_validate(item))
        except Exception:
            logger.warning("Пропуск некорректной entity: %s", item, exc_info=True)
    return entities or None


def serialize_event_detail_message(message: Message) -> dict[str, Any] | None:
    """
    Сохраняет одно сообщение админа для показа пользователям.
    Поддерживаются типы, которые можно надёжно восстановить по file_id + entities.
    """
    ct = message.content_type
    if ct == ContentType.TEXT:
        text = message.text or ""
        entities = _dump_entities(message.entities)
        if not text.strip() and not entities:
            return None
        return {
            "v": PAYLOAD_VERSION,
            "kind": "text",
            "text": text,
            "entities": entities,
        }
    if ct == ContentType.PHOTO:
        if not message.photo:
            return None
        return {
            "v": PAYLOAD_VERSION,
            "kind": "photo",
            "file_id": message.photo[-1].file_id,
            "has_media_spoiler": bool(message.has_media_spoiler),
            "caption": message.caption or "",
            "entities": _dump_entities(message.caption_entities),
        }
    if ct == ContentType.VIDEO:
        if not message.video:
            return None
        return {
            "v": PAYLOAD_VERSION,
            "kind": "video",
            "file_id": message.video.file_id,
            "has_media_spoiler": bool(message.has_media_spoiler),
            "caption": message.caption or "",
            "entities": _dump_entities(message.caption_entities),
        }
    if ct == ContentType.ANIMATION:
        if not message.animation:
            return None
        return {
            "v": PAYLOAD_VERSION,
            "kind": "animation",
            "file_id": message.animation.file_id,
            "has_media_spoiler": bool(message.has_media_spoiler),
            "caption": message.caption or "",
            "entities": _dump_entities(message.caption_entities),
        }
    if ct == ContentType.DOCUMENT:
        if not message.document:
            return None
        return {
            "v": PAYLOAD_VERSION,
            "kind": "document",
            "file_id": message.document.file_id,
            "caption": message.caption or "",
            "entities": _dump_entities(message.caption_entities),
        }
    return None


def detail_payload_to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def detail_json_to_payload(raw: str | None) -> dict[str, Any] | None:
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("v") == PAYLOAD_VERSION and data.get("kind"):
            return data
    except json.JSONDecodeError:
        logger.warning("detail_json: невалидный JSON")
    return None


def plain_text_preview_from_payload(payload: dict[str, Any]) -> str:
    kind = payload.get("kind")
    if kind == "text":
        return (payload.get("text") or "").strip()[:500]
    if kind in ("photo", "video", "animation", "document"):
        cap = (payload.get("caption") or "").strip()
        return (cap or f"[{kind}]")[:500]
    return ""


def legacy_payload_from_event(
    *,
    title: str,
    description: str,
    price: str,
    starts_at_str: str,
) -> dict[str, Any]:
    """Старые записи без detail_json — показываем как HTML без entities."""
    text = (
        f"<b>{title}</b>\n\n"
        f"{description}\n\n"
        f"💰 <b>Стоимость:</b> {price}\n"
        f"🗓 <b>Дата и время:</b> {starts_at_str}"
    )
    return {
        "v": PAYLOAD_VERSION,
        "kind": "text",
        "text": text,
        "entities": [],
        "parse_mode": "HTML",
    }


async def send_event_detail_message(
    bot: Bot,
    chat_id: int,
    payload: dict[str, Any],
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """
    Отправляет сохранённое описание. Возвращает объект Message.
    Для контента с entities явно parse_mode=None, чтобы не ломать разметку из entities.
    """
    kind = payload.get("kind")
    pm = payload.get("parse_mode")
    if kind == "text":
        text = payload.get("text") or ""
        entities = _load_entities(payload.get("entities"))
        if pm == "HTML":
            return await bot.send_message(
                chat_id,
                text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        return await bot.send_message(
            chat_id,
            text,
            entities=entities,
            reply_markup=reply_markup,
            parse_mode=None,
        )
    if kind == "photo":
        entities = _load_entities(payload.get("entities"))
        return await bot.send_photo(
            chat_id,
            photo=payload["file_id"],
            caption=payload.get("caption") or "",
            caption_entities=entities,
            has_media_spoiler=bool(payload.get("has_media_spoiler")),
            reply_markup=reply_markup,
            parse_mode=None,
        )
    if kind == "video":
        entities = _load_entities(payload.get("entities"))
        return await bot.send_video(
            chat_id,
            video=payload["file_id"],
            caption=payload.get("caption") or "",
            caption_entities=entities,
            has_media_spoiler=bool(payload.get("has_media_spoiler")),
            reply_markup=reply_markup,
            parse_mode=None,
        )
    if kind == "animation":
        entities = _load_entities(payload.get("entities"))
        return await bot.send_animation(
            chat_id,
            animation=payload["file_id"],
            caption=payload.get("caption") or "",
            caption_entities=entities,
            has_media_spoiler=bool(payload.get("has_media_spoiler")),
            reply_markup=reply_markup,
            parse_mode=None,
        )
    if kind == "document":
        entities = _load_entities(payload.get("entities"))
        return await bot.send_document(
            chat_id,
            document=payload["file_id"],
            caption=payload.get("caption") or "",
            caption_entities=entities,
            reply_markup=reply_markup,
            parse_mode=None,
        )
    raise ValueError(f"Неизвестный kind описания мероприятия: {kind}")
