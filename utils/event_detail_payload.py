"""
Сериализация и отправка «карточки» мероприятия как в Telegram:
текст + MessageEntity (цитаты, кастомные эмодзи и т.д.), фото/видео с подписью.
"""

from __future__ import annotations

import html
import json
import logging
from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from aiogram.types import Message, MessageEntity
from aiogram.types import InlineKeyboardMarkup

from utils.telegram_media import send_photo_with_fallback

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
    safe_title = html.escape(title or "Мероприятие")
    safe_desc = html.escape(description or "—")
    safe_price = html.escape(price or "—")
    text = (
        f"<b>{safe_title}</b>\n\n"
        f"{safe_desc}\n\n"
        f"💰 <b>Стоимость:</b> {safe_price}\n"
        f"🗓 <b>Дата и время:</b> {html.escape(starts_at_str)}"
    )
    return {
        "v": PAYLOAD_VERSION,
        "kind": "text",
        "text": text,
        "entities": [],
        "parse_mode": "HTML",
    }


def _spoiler_kwargs(payload: dict[str, Any]) -> dict[str, bool]:
    """aiogram 3: параметр has_spoiler (в payload храним has_media_spoiler с Message)."""
    if payload.get("has_media_spoiler"):
        return {"has_spoiler": True}
    return {}


def _pick_send_text(payload: dict[str, Any], fallback_text: str | None) -> str:
    preview = plain_text_preview_from_payload(payload).strip()
    if preview:
        return preview
    if fallback_text and fallback_text.strip():
        return fallback_text.strip()
    return "📅 Мероприятие"


async def _safe_send_message(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    entities: list[MessageEntity] | None = None,
    parse_mode: str | None = None,
) -> Message:
    """Отправка текста с цепочкой fallback — карточка всегда доходит."""
    body = (text or "").strip() or "📅 Мероприятие"

    if parse_mode == "HTML":
        try:
            return await Bot.send_message(
                bot,
                chat_id=chat_id,
                text=body,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        except (TelegramBadRequest, TelegramAPIError) as exc:
            logger.warning("event HTML send failed: %s", exc)

    if entities:
        try:
            return await Bot.send_message(
                bot,
                chat_id=chat_id,
                text=body,
                entities=entities,
                reply_markup=reply_markup,
            )
        except (TelegramBadRequest, TelegramAPIError) as exc:
            logger.warning("event entities send failed: %s", exc)

    try:
        return await Bot.send_message(
            bot,
            chat_id=chat_id,
            text=body,
            reply_markup=reply_markup,
        )
    except (TelegramBadRequest, TelegramAPIError) as exc:
        logger.warning("event plain send failed: %s", exc)
        return await Bot.send_message(
            bot,
            chat_id=chat_id,
            text="📅 Мероприятие",
            reply_markup=reply_markup,
        )


async def _send_text_payload(
    bot: Bot,
    chat_id: int,
    payload: dict[str, Any],
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    fallback_text: str | None = None,
) -> Message:
    text = payload.get("text") or _pick_send_text(payload, fallback_text)
    pm = payload.get("parse_mode")
    entities = _load_entities(payload.get("entities"))
    return await _safe_send_message(
        bot,
        chat_id,
        text,
        reply_markup=reply_markup,
        entities=entities if pm != "HTML" else None,
        parse_mode=pm if pm == "HTML" else None,
    )


async def _send_media_payload(
    bot: Bot,
    chat_id: int,
    payload: dict[str, Any],
    *,
    send_method: str,
    file_kw: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    fallback_text: str | None = None,
) -> Message:
    file_id = payload.get("file_id")
    caption = (payload.get("caption") or "").strip()
    entities = _load_entities(payload.get("entities"))
    fallback_body = caption or _pick_send_text(payload, fallback_text)

    if not file_id:
        return await _safe_send_message(
            bot, chat_id, fallback_body, reply_markup=reply_markup
        )

    send_fn = getattr(Bot, f"send_{send_method}", None)
    if send_fn is None:
        return await _safe_send_message(
            bot, chat_id, fallback_body, reply_markup=reply_markup
        )

    if send_method == "photo":
        try:
            return await send_photo_with_fallback(
                bot,
                chat_id,
                file_id,
                caption=caption or fallback_body,
                parse_mode="HTML" if not entities else None,
                reply_markup=reply_markup,
                caption_entities=entities if entities else None,
                **_spoiler_kwargs(payload),
            )
        except Exception as exc:
            logger.warning("event photo send failed: %s", exc)

    kwargs: dict[str, Any] = {
        file_kw: file_id,
        "caption": caption or None,
        "reply_markup": reply_markup,
    }
    if entities:
        kwargs["caption_entities"] = entities
    if send_method in ("photo", "video", "animation"):
        kwargs.update(_spoiler_kwargs(payload))

    try:
        return await send_fn(bot, chat_id=chat_id, **kwargs)
    except (TelegramBadRequest, TelegramAPIError, TypeError) as exc:
        logger.warning("event %s send failed: %s", send_method, exc)

    if entities and caption:
        try:
            return await send_fn(
                bot,
                chat_id=chat_id,
                **{file_kw: file_id, "caption": caption, "reply_markup": reply_markup},
            )
        except (TelegramBadRequest, TelegramAPIError, TypeError) as exc:
            logger.warning("event %s retry without entities failed: %s", send_method, exc)

    return await _safe_send_message(
        bot, chat_id, fallback_body, reply_markup=reply_markup
    )


async def send_event_detail_message(
    bot: Bot,
    chat_id: int,
    payload: dict[str, Any],
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    fallback_text: str | None = None,
) -> Message:
    """
    Отправляет сохранённое описание. Всегда возвращает Message (не бросает наружу).
    """
    if not payload or not isinstance(payload, dict):
        return await _safe_send_message(
            bot,
            chat_id,
            fallback_text or "📅 Мероприятие",
            reply_markup=reply_markup,
        )

    kind = payload.get("kind")
    try:
        if kind == "text":
            return await _send_text_payload(
                bot, chat_id, payload, reply_markup=reply_markup, fallback_text=fallback_text
            )
        if kind == "photo":
            return await _send_media_payload(
                bot,
                chat_id,
                payload,
                send_method="photo",
                file_kw="photo",
                reply_markup=reply_markup,
                fallback_text=fallback_text,
            )
        if kind == "video":
            return await _send_media_payload(
                bot,
                chat_id,
                payload,
                send_method="video",
                file_kw="video",
                reply_markup=reply_markup,
                fallback_text=fallback_text,
            )
        if kind == "animation":
            return await _send_media_payload(
                bot,
                chat_id,
                payload,
                send_method="animation",
                file_kw="animation",
                reply_markup=reply_markup,
                fallback_text=fallback_text,
            )
        if kind == "document":
            return await _send_media_payload(
                bot,
                chat_id,
                payload,
                send_method="document",
                file_kw="document",
                reply_markup=reply_markup,
                fallback_text=fallback_text,
            )
    except Exception as exc:
        logger.error("send_event_detail_message(%s): %s", kind, exc, exc_info=True)

    body = plain_text_preview_from_payload(payload) or fallback_text or "📅 Мероприятие"
    return await _safe_send_message(bot, chat_id, body, reply_markup=reply_markup)
