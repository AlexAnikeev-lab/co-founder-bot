"""
Раздел «Мероприятия» (пользовательский интерфейс).
"""

from __future__ import annotations

import logging
import html

from aiogram import Router, F
from aiogram.types import FSInputFile
from aiogram.types import CallbackQuery, Message
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_events_list_photo_file_id, get_events_list_photo_path
from keyboards.events import (
    EventsCallbackData,
    get_event_card_keyboard,
    get_event_pair_details_keyboard,
    get_events_list_keyboard,
)
from keyboards.menu import get_main_menu_keyboard
from keyboards.common import get_back_button
from repositories.user_repository import UserRepository
from repositories.test_repository import TestResultRepository
from repositories.events_repository import EventsRepository, Event
from services.compatibility_service import CompatibilityService
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
    reg_event_ids = await EventsRepository.list_registered_event_ids_for_user(session, user_id)
    notified_event_ids = await EventsRepository.list_notified_event_ids_for_user(session, user_id)
    kb_items: list[tuple[int, str]] = []
    for it in items:
        title = (it.title or "").strip()[:56]
        markers: list[str] = []
        if it.id in reg_event_ids:
            markers.append("✅")
        if it.id in notified_event_ids:
            markers.append("🔔")
        markers_text = (" " + " ".join(markers)) if markers else ""
        btn_text = (title + markers_text)[:64]
        kb_items.append((it.id, btn_text))
    kb = get_events_list_keyboard(lang=lang, items=kb_items)
    cover_file_id = get_events_list_photo_file_id(lang=lang)
    cover_path = get_events_list_photo_path(lang=lang)

    async def _send_list_message(msg: Message) -> Message:
        if cover_file_id:
            return await msg.answer_photo(
                photo=cover_file_id,
                caption=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
        if cover_path:
            return await msg.answer_photo(
                photo=FSInputFile(cover_path),
                caption=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
        return await msg.answer(text, reply_markup=kb, parse_mode="HTML")

    if isinstance(message_or_callback, CallbackQuery):
        cb = message_or_callback
        msg = cb.message
        if not msg:
            return
        try:
            await msg.delete()
        except Exception:
            pass
        sent = await _send_list_message(msg)
        await state.update_data(last_bot_message_id=sent.message_id)
    else:
        m = message_or_callback
        sent = await _send_list_message(m)
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
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        lang, _ = await _get_lang_and_minor(session, callback.from_user.id)
        if not user or not user.is_registered:
            await callback.answer()
            await callback.message.answer(t(lang, "not_registered_use_start"))
            return

        test_result = await TestResultRepository.get_by_user_id(session, callback.from_user.id)
        if not test_result or not test_result.main_test_completed:
            builder = InlineKeyboardBuilder()
            builder.add(
                InlineKeyboardButton(
                    text=t(lang, "partners_btn_take_test"),
                    callback_data="start_test:main",
                )
            )
            builder.add(get_back_button("main_menu", lang))
            builder.adjust(1)
            await callback.answer()
            await callback.message.answer(
                f"{t(lang, 'events_title')}\n\n{t(lang, 'partners_main_test_required')}",
                reply_markup=builder.as_markup(),
            )
            return

        missing_fields: list[str] = []
        if not user.short_description:
            missing_fields.append(t(lang, "partners_field_short_desc"))
        if not user.full_description:
            missing_fields.append(t(lang, "partners_field_full_desc"))
        if not user.qualities:
            missing_fields.append(t(lang, "partners_field_qualities"))
        if missing_fields:
            builder = InlineKeyboardBuilder()
            builder.add(get_back_button("main_menu", lang))
            builder.adjust(1)
            await callback.answer()
            await callback.message.answer(
                f"{t(lang, 'events_title')}\n\n{t(lang, 'partners_fill_profile').format(fields=', '.join(missing_fields))}",
                reply_markup=builder.as_markup(),
            )
            return

        ok = await EventsRepository.register_user(session, callback_data.event_id, callback.from_user.id)
        await callback.answer()
        await callback.message.answer(t(lang, "events_join_ok") if ok else t(lang, "events_join_already"))
    except Exception as e:
        logger.error("Ошибка регистрации на мероприятие: %s", e, exc_info=True)
        await handle_error(None, e, "events_join")
        await callback.answer(t("ru", "error_try_later"), show_alert=True)


@router.callback_query(F.data.startswith("event_pair_more:"))
async def events_pair_more(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать расширенную информацию о подобранной паре для мероприятия."""
    if not callback.from_user or not callback.message:
        return
    await callback.answer()
    try:
        parts = (callback.data or "").split(":")
        if len(parts) != 2:
            return
        partner_id = int(parts[1])
        viewer_id = callback.from_user.id

        viewer = await UserRepository.get_by_telegram_id(session, viewer_id)
        partner = await UserRepository.get_by_telegram_id(session, partner_id)
        lang = (getattr(viewer, "language", None) or "ru") if viewer else "ru"
        if not partner:
            await callback.answer(t(lang, "profile_unavailable"), show_alert=True)
            return

        compatibility_explanation = None
        tr_viewer = await TestResultRepository.get_by_user_id(session, viewer_id)
        tr_partner = await TestResultRepository.get_by_user_id(session, partner_id)
        if tr_viewer and tr_partner and tr_viewer.main_test_completed and tr_partner.main_test_completed:
            from handlers.swipe import _get_user_profile
            pv = _get_user_profile(tr_viewer, include_label=True)
            pp = _get_user_profile(tr_partner, include_label=True)
            if pv and pp:
                score, details = CompatibilityService.calculate_compatibility_detailed(pv, pp)
                compatibility_explanation = CompatibilityService.get_compatibility_explanation(score, details, lang=lang)

        from handlers.swipe import _clean_full_description
        details_parts: list[str] = []
        more = _clean_full_description(getattr(partner, "full_description", None))
        if more:
            details_parts.append(f"<b>{t(lang, 'card_more')}:</b>")
            details_parts.append(f"<blockquote>{html.escape(more)}</blockquote>")
        if compatibility_explanation:
            details_parts.append(f"<b>{t(lang, 'card_why_compatibility')}</b>")
            details_parts.append(compatibility_explanation)
        if not details_parts:
            details_parts.append(t(lang, "events_pair_more_empty"))

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await callback.message.answer(
            "\n\n".join(details_parts),
            reply_markup=get_event_pair_details_keyboard(lang=lang, dm_link=_dm_link(partner)),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Ошибка показа деталей пары мероприятия: %s", e, exc_info=True)
        await handle_error(None, e, "events_pair_more")
        await callback.answer(t("ru", "error_try_later"), show_alert=True)


def _dm_link(user) -> str:
    username = (getattr(user, "username", None) or "").strip().lstrip("@")
    if username:
        return f"https://t.me/{username}"
    return f"tg://user?id={user.telegram_id}"


def register_handlers(dp) -> None:
    dp.include_router(router)
