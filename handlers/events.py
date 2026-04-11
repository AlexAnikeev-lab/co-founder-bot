"""
Раздел «Мероприятия» (пользовательский интерфейс).
"""

from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.events import (
    EventsCallbackData,
    get_event_card_keyboard,
    get_events_list_keyboard,
)
from keyboards.menu import get_main_menu_keyboard
from repositories.user_repository import UserRepository
from repositories.events_repository import EventsRepository, Event
from texts.i18n import t, text_options
from utils.errors import handle_error
from utils.event_detail_payload import (
    detail_json_to_payload,
    legacy_payload_from_event,
    send_event_detail_message,
)

logger = logging.getLogger(__name__)
router = Router()


def _event_detail_payload(ev: Event) -> dict:
    parsed = detail_json_to_payload(ev.detail_json)
    if parsed:
        return parsed
    return legacy_payload_from_event(
        title=ev.title,
        description=ev.description,
        price=ev.price,
        starts_at_str=ev.starts_at.strftime("%d.%m.%Y %H:%M"),
    )


async def _get_lang_and_minor(session: AsyncSession, user_id: int) -> tuple[str, bool]:
    lang, is_minor = "ru", False
    u = await UserRepository.get_by_telegram_id(session, user_id)
    if u:
        lang = getattr(u, "language", None) or "ru"
        is_minor = bool(getattr(u, "is_minor", False))
    return lang, is_minor


async def _show_events_list(
    *,
    message_or_callback: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user_id: int,
) -> None:
    lang, is_minor = await _get_lang_and_minor(session, user_id)
    items = await EventsRepository.list_items(session)
    if not items:
        text = t(lang, "events_title") + "\n\n" + t(lang, "events_empty")
        if isinstance(message_or_callback, CallbackQuery):
            msg = message_or_callback.message
            if not msg:
                return
            try:
                await msg.edit_text(text, reply_markup=None, parse_mode="HTML")
            except Exception:
                await msg.answer(text, reply_markup=None, parse_mode="HTML")
        else:
            await message_or_callback.answer(
                text,
                reply_markup=get_main_menu_keyboard(is_minor=is_minor, lang=lang),
                parse_mode="HTML",
            )
        return

    text = t(lang, "events_title") + "\n\n" + t(lang, "choose_event_from_list")
    kb_items: list[tuple[int, str]] = []
    for it in items:
        btn_text = (it.title or "")[:64]
        kb_items.append((it.id, btn_text))
    kb = get_events_list_keyboard(lang=lang, items=kb_items)

    if isinstance(message_or_callback, CallbackQuery):
        cb = message_or_callback
        msg = cb.message
        if not msg:
            return
        try:
            if msg.photo:
                await msg.delete()
                sent = await msg.answer(text, reply_markup=kb, parse_mode="HTML")
                await state.update_data(last_bot_message_id=sent.message_id)
            else:
                await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            try:
                await msg.delete()
            except Exception:
                pass
            sent = await msg.answer(text, reply_markup=kb, parse_mode="HTML")
            await state.update_data(last_bot_message_id=sent.message_id)
    else:
        m = message_or_callback
        sent = await m.answer(text, reply_markup=kb, parse_mode="HTML")
        await state.update_data(last_bot_message_id=sent.message_id)


async def _show_event_detail(
    *,
    message_or_callback: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user_id: int,
    event_id: int,
) -> None:
    lang, is_minor = await _get_lang_and_minor(session, user_id)
    ev = await EventsRepository.get_by_id(session, event_id)
    if not ev:
        text = t(lang, "events_title") + "\n\n" + t(lang, "events_not_found")
        if isinstance(message_or_callback, CallbackQuery):
            msg = message_or_callback.message
            if msg:
                try:
                    await msg.edit_text(text, reply_markup=None, parse_mode="HTML")
                except Exception:
                    await msg.answer(text, parse_mode="HTML")
        else:
            await message_or_callback.answer(text, reply_markup=get_main_menu_keyboard(is_minor=is_minor, lang=lang))
        return

    payload = _event_detail_payload(ev)
    kb = get_event_card_keyboard(lang=lang, event_id=ev.id)

    if isinstance(message_or_callback, CallbackQuery):
        cb = message_or_callback
        msg = cb.message
        if not msg:
            return
        try:
            await msg.delete()
        except Exception:
            pass
        try:
            sent = await send_event_detail_message(
                msg.bot,
                msg.chat.id,
                payload,
                reply_markup=kb,
            )
            await state.update_data(last_bot_message_id=sent.message_id)
        except Exception as e:
            logger.error("Ошибка показа описания мероприятия: %s", e, exc_info=True)
            await handle_error(None, e, "_show_event_detail")
            sent = await msg.answer("❌ " + t(lang, "error_try_later"), reply_markup=kb)
            await state.update_data(last_bot_message_id=sent.message_id)
    else:
        m = message_or_callback
        try:
            sent = await send_event_detail_message(
                m.bot,
                m.chat.id,
                payload,
                reply_markup=kb,
            )
            await state.update_data(last_bot_message_id=sent.message_id)
        except Exception as e:
            logger.error("Ошибка показа описания мероприятия: %s", e, exc_info=True)
            await handle_error(None, e, "_show_event_detail")
            sent = await m.answer("❌ " + t(lang, "error_try_later"), reply_markup=kb)
            await state.update_data(last_bot_message_id=sent.message_id)


@router.message(F.text.in_(text_options("menu_events")))
async def events_from_menu(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user:
        return
    try:
        try:
            await message.delete()
        except Exception:
            pass
        await _show_events_list(
            message_or_callback=message,
            state=state,
            session=session,
            user_id=message.from_user.id,
        )
    except Exception as e:
        logger.error("Ошибка открытия мероприятий: %s", e, exc_info=True)
        await handle_error(None, e, "events_from_menu")


@router.callback_query(F.data == "events_list")
async def events_back_to_list(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.from_user:
        return
    await callback.answer()
    try:
        await _show_events_list(
            message_or_callback=callback,
            state=state,
            session=session,
            user_id=callback.from_user.id,
        )
    except Exception as e:
        logger.error("Ошибка возврата к списку мероприятий: %s", e, exc_info=True)
        await handle_error(None, e, "events_back_to_list")
        await callback.answer(t("ru", "error_try_later"), show_alert=True)


@router.callback_query(EventsCallbackData.filter(F.action == "open"))
async def events_open(
    callback: CallbackQuery,
    callback_data: EventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user:
        return
    await callback.answer()
    try:
        await _show_event_detail(
            message_or_callback=callback,
            state=state,
            session=session,
            user_id=callback.from_user.id,
            event_id=int(callback_data.event_id),
        )
    except Exception as e:
        logger.error("Ошибка открытия карточки мероприятия: %s", e, exc_info=True)
        await handle_error(None, e, "events_open")
        await callback.answer(t("ru", "error_try_later"), show_alert=True)


@router.callback_query(EventsCallbackData.filter(F.action == "join"))
async def events_join(callback: CallbackQuery, callback_data: EventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
    if not callback.from_user or not callback.message:
        return
    try:
        lang, _ = await _get_lang_and_minor(session, callback.from_user.id)
        ok = await EventsRepository.register_user(session, callback_data.event_id, callback.from_user.id)
        await callback.answer()
        await callback.message.answer(t(lang, "events_join_ok") if ok else t(lang, "events_join_already"))
    except Exception as e:
        logger.error("Ошибка регистрации на мероприятие: %s", e, exc_info=True)
        await handle_error(None, e, "events_join")
        await callback.answer(t("ru", "error_try_later"), show_alert=True)


def register_handlers(dp) -> None:
    dp.include_router(router)
