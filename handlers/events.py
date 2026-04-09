"""
Раздел «Мероприятия» (пользовательский интерфейс).
"""

from __future__ import annotations

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.events import (
    EventsCallbackData,
    EventsNavCallbackData,
    get_event_card_keyboard,
    get_events_list_keyboard,
)
from keyboards.menu import get_main_menu_keyboard
from repositories.user_repository import UserRepository
from repositories.events_repository import EventsRepository, Event
from texts.i18n import t, text_options
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()


def _format_event_card_text(ev: Event, position: int, total: int) -> str:
    return (
        f"{position} / {total}\n\n"
        f"<b>{ev.title}</b>\n\n"
        f"{ev.description}\n\n"
        f"💰 <b>Стоимость:</b> {ev.price}\n"
        f"🗓 <b>Дата и время:</b> {ev.starts_at.strftime('%d.%m.%Y %H:%M')}"
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
        btn_text = f"{it.position}. {it.title} • {it.starts_at.strftime('%d.%m %H:%M')}"
        kb_items.append((it.id, btn_text))
    kb = get_events_list_keyboard(lang=lang, items=kb_items)

    if isinstance(message_or_callback, CallbackQuery):
        cb = message_or_callback
        msg = cb.message
        if not msg:
            return
        try:
            # Если до этого была карточка с фото — проще переслать новым сообщением
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


async def _show_event_by_position(
    *,
    message_or_callback: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user_id: int,
    position: int,
) -> None:
    lang, is_minor = await _get_lang_and_minor(session, user_id)
    total = await EventsRepository.get_count(session)
    if total <= 0:
        text = t(lang, "events_title") + "\n\n" + t(lang, "events_empty")
        if isinstance(message_or_callback, CallbackQuery):
            msg = message_or_callback.message
            try:
                await msg.edit_text(text, reply_markup=None)
            except Exception:
                await msg.answer(text)
        else:
            await message_or_callback.answer(text, reply_markup=get_main_menu_keyboard(is_minor=is_minor, lang=lang))
        return

    position = max(1, min(total, position))
    ev = await EventsRepository.get_by_position(session, position)
    if not ev:
        # если позиции «дырявые» (не должны быть), показываем первый
        ev = await EventsRepository.get_first(session)
        position = int(ev.position) if ev else 1
    if not ev:
        return

    card_text = _format_event_card_text(ev, position, total)
    kb = get_event_card_keyboard(
        lang=lang,
        event_id=ev.id,
        position=position,
        total=total,
        show_prev=position > 1,
        show_next=position < total,
    )

    if isinstance(message_or_callback, CallbackQuery):
        cb = message_or_callback
        msg = cb.message
        if not msg:
            return
        # стараемся обновлять существующее сообщение
        try:
            if ev.banner_file_id:
                if msg.photo:
                    await msg.edit_media(
                        media=InputMediaPhoto(media=ev.banner_file_id, caption=card_text, parse_mode="HTML"),
                        reply_markup=kb,
                    )
                else:
                    await msg.delete()
                    sent = await msg.answer_photo(photo=ev.banner_file_id, caption=card_text, reply_markup=kb, parse_mode="HTML")
                    await state.update_data(last_bot_message_id=sent.message_id)
            else:
                if msg.photo:
                    await msg.delete()
                    sent = await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")
                    await state.update_data(last_bot_message_id=sent.message_id)
                else:
                    await msg.edit_text(card_text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            try:
                await msg.delete()
            except Exception:
                pass
            if ev.banner_file_id:
                sent = await msg.answer_photo(photo=ev.banner_file_id, caption=card_text, reply_markup=kb, parse_mode="HTML")
            else:
                sent = await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")
            await state.update_data(last_bot_message_id=sent.message_id)
    else:
        m = message_or_callback
        sent = None
        if ev.banner_file_id:
            sent = await m.answer_photo(photo=ev.banner_file_id, caption=card_text, reply_markup=kb, parse_mode="HTML")
        else:
            sent = await m.answer(card_text, reply_markup=kb, parse_mode="HTML")
        if sent:
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
async def events_open(callback: CallbackQuery, callback_data: EventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
    if not callback.from_user:
        return
    await callback.answer()
    try:
        ev = await EventsRepository.get_by_id(session, int(callback_data.event_id))
        if not ev:
            lang, _ = await _get_lang_and_minor(session, callback.from_user.id)
            if callback.message:
                try:
                    await callback.message.edit_text(
                        "❌ " + t(lang, "events_not_found"),
                        reply_markup=None,
                        parse_mode="HTML",
                    )
                except Exception:
                    await callback.message.answer(
                        "❌ " + t(lang, "events_not_found"),
                        parse_mode="HTML",
                    )
            return
        await _show_event_by_position(
            message_or_callback=callback,
            state=state,
            session=session,
            user_id=callback.from_user.id,
            position=int(ev.position),
        )
    except Exception as e:
        logger.error("Ошибка открытия карточки мероприятия: %s", e, exc_info=True)
        await handle_error(None, e, "events_open")
        await callback.answer(t("ru", "error_try_later"), show_alert=True)


@router.callback_query(EventsNavCallbackData.filter())
async def events_nav(callback: CallbackQuery, callback_data: EventsNavCallbackData, state: FSMContext, session: AsyncSession) -> None:
    if not callback.from_user:
        return
    await callback.answer()
    try:
        pos = int(callback_data.position)
        if callback_data.action == "prev":
            pos -= 1
        elif callback_data.action == "next":
            pos += 1
        await _show_event_by_position(
            message_or_callback=callback,
            state=state,
            session=session,
            user_id=callback.from_user.id,
            position=pos,
        )
    except Exception as e:
        logger.error("Ошибка навигации мероприятий: %s", e, exc_info=True)
        await handle_error(None, e, "events_nav")
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

