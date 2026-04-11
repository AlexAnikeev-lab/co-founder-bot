"""
Админ-управление мероприятиями: добавление/редактирование/удаление,
подбор пар, рассылка зарегистрировавшимся, просмотр пар.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from keyboards.admin import AdminCallbackData
from keyboards.admin_events import (
    AdminEventsCallbackData,
    AdminEventsEditCallbackData,
    AdminEventCreateMatchCallbackData,
    get_admin_events_list_keyboard,
    get_admin_event_view_keyboard,
    get_admin_event_edit_fields_keyboard,
    get_admin_event_delete_confirm_keyboard,
    get_admin_event_create_match_keyboard,
)
from repositories.events_repository import EventsRepository
from repositories.user_repository import UserRepository
from services.events_matching import build_pairs_for_event, notify_pairs_for_event
from states.events_admin import AdminEventsStates
from utils.validators import parse_event_end_date
from utils.errors import handle_error
from utils.event_detail_payload import (
    detail_json_to_payload,
    detail_payload_to_json,
    plain_text_preview_from_payload,
    serialize_event_detail_message,
    send_event_detail_message,
)

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    cfg = Config()
    return user_id in cfg.ADMIN_IDS


def _button_label_ok(text: str) -> bool:
    t = text.strip()
    if len(t) < 1 or len(t) > 64:
        return False
    return True


def _format_admin_event_text(ev) -> str:
    parsed = detail_json_to_payload(ev.detail_json)
    if parsed:
        pv = plain_text_preview_from_payload(parsed) or "—"
        if len(pv) > 280:
            pv = pv[:280] + "…"
        desc_note = pv
    else:
        desc_note = ((ev.description or "")[:280] + "…") if len(ev.description or "") > 280 else (ev.description or "—")

    del_day = ev.starts_at.strftime("%d.%m.%Y")
    return (
        f"📅 <b>Мероприятие #{ev.position}</b>\n\n"
        f"🔘 <b>Текст кнопки:</b> {ev.title}\n"
        f"📝 <b>Описание (превью):</b> {desc_note}\n\n"
        f"🗑 <b>Удаление карточки:</b> автоматически после окончания <b>{del_day}</b> (сразу после 23:59)\n\n"
        f"🔔 <b>Подбор пар:</b> {'Да' if ev.matching_enabled else 'Нет'}"
    )


async def _admin_events_list(callback: CallbackQuery, session: AsyncSession) -> None:
    items = await EventsRepository.list_items(session)
    labels: list[tuple[int, str]] = []
    for it in items:
        flag = "✅" if it.matching_enabled else "❌"
        labels.append((it.id, f"{it.position}. {it.title[:32]} (до {it.starts_at.strftime('%d.%m.%Y')}) {flag}"))
    text = "📅 <b>Мероприятия</b>\n\nВыберите мероприятие или добавьте новое."
    await callback.message.edit_text(text, reply_markup=get_admin_events_list_keyboard(labels), parse_mode="HTML")


@router.callback_query(AdminCallbackData.filter(F.action == "events"))
async def admin_events_entry(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    try:
        await _admin_events_list(callback, session)
    except Exception as e:
        logger.error("Ошибка списка мероприятий: %s", e, exc_info=True)
        await handle_error(None, e, "admin_events_entry")


@router.callback_query(AdminEventsCallbackData.filter(F.action == "add"))
async def admin_events_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    await state.update_data(admin_event_create={})
    await state.set_state(AdminEventsStates.waiting_for_title)
    await callback.message.edit_text(
        "➕ <b>Добавление мероприятия</b>\n\n"
        "Введите <b>текст для кнопки</b> в списке мероприятий (до 64 символов).\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(F.text == "/cancel", StateFilter(AdminEventsStates))
async def admin_events_cancel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Отменено. Вернитесь в /admin → 📅 Мероприятия.")


@router.message(AdminEventsStates.waiting_for_title, F.text)
async def admin_events_add_title(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    title = (message.text or "").strip()
    if not _button_label_ok(title):
        await message.answer("Текст кнопки: от 1 до 64 символов.")
        return
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["title"] = title
    await state.update_data(admin_event_create=create)
    await state.set_state(AdminEventsStates.waiting_for_description)
    await message.answer(
        "Отправьте <b>одно сообщение</b> с описанием мероприятия — бот сохранит его как есть: "
        "эмодзи, форматирование, цитаты, картинка с подписью и т.д.\n"
        "(Поддерживаются: текст, фото, видео, GIF, документ с подписью.)",
        parse_mode="HTML",
    )


@router.message(AdminEventsStates.waiting_for_description)
async def admin_events_add_description(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        return
    payload = serialize_event_detail_message(message)
    if not payload:
        await message.answer(
            "Такой тип сообщения не поддерживается. "
            "Отправьте текст, фото, видео, анимацию или документ (можно с подписью)."
        )
        return
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["detail_payload"] = payload
    create["description_plain"] = plain_text_preview_from_payload(payload) or "—"
    await state.update_data(admin_event_create=create)
    await state.set_state(AdminEventsStates.waiting_for_match_choice)
    await message.answer(
        "Включить <b>подбор пар</b> для этого мероприятия?",
        parse_mode="HTML",
        reply_markup=get_admin_event_create_match_keyboard(),
    )


@router.callback_query(
    AdminEventCreateMatchCallbackData.filter(),
    StateFilter(AdminEventsStates.waiting_for_match_choice),
)
async def admin_events_create_match_choice(
    callback: CallbackQuery,
    callback_data: AdminEventCreateMatchCallbackData,
    state: FSMContext,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["matching_enabled"] = callback_data.choice == "y"
    await state.update_data(admin_event_create=create)
    await state.set_state(AdminEventsStates.waiting_for_event_date)
    await callback.message.edit_text(
        "Укажите <b>дату</b> календарного дня мероприятия в формате <code>ДД.ММ.ГГГГ</code> "
        "(например: <code>07.04.2026</code>).\n\n"
        "После окончания этого дня карточка будет <b>удалена</b> автоматически. "
        "Цену, время и прочее укажите в описании выше.",
        parse_mode="HTML",
        reply_markup=None,
    )


@router.message(AdminEventsStates.waiting_for_match_choice, F.text)
async def admin_events_match_choice_hint(message: Message) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await message.answer("Выберите «Да» или «Нет» кнопками выше.")


@router.message(AdminEventsStates.waiting_for_event_date, F.text)
async def admin_events_add_event_date(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    dt = parse_event_end_date(message.text or "")
    if not dt:
        await message.answer("Не понял дату. Формат: <code>ДД.ММ.ГГГГ</code> (только дата).", parse_mode="HTML")
        return
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["starts_at"] = dt
    payload = create.get("detail_payload")
    if not isinstance(payload, dict):
        await message.answer("❌ Внутренняя ошибка: нет описания. Начните заново: /admin → Мероприятия → Добавить.")
        await state.clear()
        return
    detail_json = detail_payload_to_json(payload)
    desc_plain = str(create.get("description_plain") or "—")[:10000]
    try:
        ev = await EventsRepository.create(
            session,
            title=create["title"],
            description=desc_plain,
            detail_json=detail_json,
            price="—",
            starts_at=create["starts_at"],
            banner_file_id=None,
            matching_enabled=bool(create.get("matching_enabled")),
        )
    except Exception as e:
        logger.error("Ошибка создания мероприятия: %s", e, exc_info=True)
        await handle_error(None, e, "admin_events_add_event_date")
        await message.answer("❌ Ошибка создания. Попробуйте позже.")
        return
    await state.clear()
    await message.answer(
        "✅ Мероприятие добавлено.\n\n" + _format_admin_event_text(ev),
        reply_markup=get_admin_event_view_keyboard(ev.id, bool(ev.matching_enabled)),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "open"))
async def admin_events_open(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        await callback.message.edit_text("❌ Мероприятие не найдено.")
        return
    await callback.message.edit_text(
        _format_admin_event_text(ev),
        reply_markup=get_admin_event_view_keyboard(ev.id, bool(ev.matching_enabled)),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "toggle_match"))
async def admin_events_toggle_match(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        return
    new_val = not bool(ev.matching_enabled)
    await EventsRepository.update_event(session, ev.id, matching_enabled=new_val)
    ev2 = await EventsRepository.get_by_id(session, ev.id)
    await callback.message.edit_text(
        _format_admin_event_text(ev2),
        reply_markup=get_admin_event_view_keyboard(ev2.id, bool(ev2.matching_enabled)),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "participants"))
async def admin_events_participants(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        return
    ids = await EventsRepository.list_registered_user_ids(session, ev.id)
    lines = [f"👥 <b>Зарегистрировавшиеся</b>\n\nМероприятие: <b>{ev.title}</b>\nВсего: <b>{len(ids)}</b>\n"]
    for tid in ids[:50]:
        u = await UserRepository.get_by_telegram_id(session, tid)
        name = (u.name if u and u.name else f"ID{tid}")
        lines.append(f"• {name} — <code>{tid}</code>")
    if len(ids) > 50:
        lines.append(f"\n... и ещё {len(ids) - 50}")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=get_admin_event_view_keyboard(ev.id, bool(ev.matching_enabled)),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "pairs_list"))
async def admin_events_pairs_list(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        return
    pairs = await build_pairs_for_event(session, ev, only_unnotified=False)
    if not pairs:
        text = (
            f"👀 <b>Пары</b>\n\nМероприятие: <b>{ev.title}</b>\n\n"
            "Нет подходящих пар: мало зарегистрированных участников с заполненной анкетой и основным тестом."
        )
    else:
        uids: set[int] = set()
        for p in pairs:
            uids.add(p.a_id)
            uids.add(p.b_id)
        users_map = await UserRepository.get_by_telegram_ids(session, list(uids))
        lines = [f"👀 <b>Пары</b> ({len(pairs)})\n\nМероприятие: <b>{ev.title}</b>\n"]
        for p in pairs:
            ua = users_map.get(p.a_id)
            ub = users_map.get(p.b_id)
            na = (ua.name if ua and ua.name else str(p.a_id))[:40]
            nb = (ub.name if ub and ub.name else str(p.b_id))[:40]
            lines.append(f"• {na} × {nb} — совместимость <b>{p.score}%</b>")
        text = "\n".join(lines)
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_event_view_keyboard(ev.id, bool(ev.matching_enabled)),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "broadcast"))
async def admin_events_broadcast_start(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        await callback.answer("Не найдено", show_alert=True)
        return
    n = await EventsRepository.count_registrations(session, ev.id)
    await callback.answer()
    await state.clear()
    await state.update_data(admin_event_broadcast_id=ev.id)
    await state.set_state(AdminEventsStates.waiting_for_broadcast_message)
    await callback.message.answer(
        f"✉️ <b>Рассылка участникам</b>\n\nМероприятие: <b>{ev.title}</b>\n"
        f"Зарегистрировано: <b>{n}</b>.\n\n"
        "Отправьте <b>одно сообщение</b> — его получат все зарегистрированные (как есть: текст, фото, форматирование).\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(AdminEventsStates.waiting_for_broadcast_message)
async def admin_events_broadcast_apply(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        return
    data = await state.get_data()
    eid = data.get("admin_event_broadcast_id")
    if not eid:
        await state.clear()
        return
    payload = serialize_event_detail_message(message)
    if not payload:
        await message.answer("Неподдерживаемый тип. Отправьте текст, фото, видео, GIF или документ.")
        return
    ids = await EventsRepository.list_registered_user_ids(session, int(eid))
    if not ids:
        await state.clear()
        await message.answer("Нет зарегистрированных участников — рассылка не нужна.")
        return
    sent = 0
    errors = 0
    for uid in ids:
        try:
            await send_event_detail_message(message.bot, uid, payload, reply_markup=None)
            sent += 1
        except Exception as e:
            errors += 1
            logger.warning("Рассылка мероприятия: не отправлено user=%s: %s", uid, e)
        await asyncio.sleep(0.035)
    await state.clear()
    await message.answer(
        f"Готово. Доставлено: <b>{sent}</b> из {len(ids)}."
        + (f" Ошибок: {errors}." if errors else ""),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "remind_pairs"))
async def admin_events_remind_pairs(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer("Отправляю…")
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        await callback.message.answer("❌ Мероприятие не найдено.")
        return
    try:
        sent = await notify_pairs_for_event(callback.bot, session, ev)
        if sent > 0:
            await callback.message.answer(f"✅ Уведомления о парах отправлены: {sent} сообщений.")
        else:
            await callback.message.answer("ℹ️ Нет подходящих пар для отправки (или уведомления уже были отправлены).")
    except Exception as e:
        logger.error("Ошибка ручной отправки напоминаний о паре: %s", e, exc_info=True)
        await handle_error(None, e, "admin_events_remind_pairs")
        await callback.message.answer("❌ Не удалось отправить напоминания.")


@router.callback_query(AdminEventsCallbackData.filter(F.action == "edit"))
async def admin_events_edit_menu(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        return
    await callback.message.edit_text(
        "✏️ <b>Редактирование мероприятия</b>\n\nВыберите, что изменить:",
        reply_markup=get_admin_event_edit_fields_keyboard(ev.id),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsEditCallbackData.filter(F.action == "field"))
async def admin_events_edit_field_pick(
    callback: CallbackQuery,
    callback_data: AdminEventsEditCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        return
    await state.clear()
    await state.update_data(admin_edit_event_id=ev.id, admin_edit_field=callback_data.field)
    await state.set_state(AdminEventsStates.waiting_for_edit_field)
    prompts = {
        "title": "Введите новый текст кнопки (1–64 символа).",
        "description": "Отправьте новое сообщение-описание (текст, фото и т.д.) — оно полностью заменит старое.",
        "event_date": "Введите новую дату в формате `ДД.ММ.ГГГГ` (конец этого дня — затем карточка удалится).",
    }
    await callback.message.answer("✏️ " + prompts.get(callback_data.field, "Введите новое значение."), parse_mode="HTML")


@router.message(AdminEventsStates.waiting_for_edit_field)
async def admin_events_edit_field_apply(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        return
    data = await state.get_data()
    event_id = data.get("admin_edit_event_id")
    field = data.get("admin_edit_field")
    if not event_id or not field:
        await state.clear()
        return
    ev = await EventsRepository.get_by_id(session, int(event_id))
    if not ev:
        await state.clear()
        await message.answer("❌ Мероприятие не найдено.")
        return

    try:
        if field == "title":
            title = (message.text or "").strip()
            if not _button_label_ok(title):
                await message.answer("Текст кнопки: от 1 до 64 символов.")
                return
            await EventsRepository.update_event(session, ev.id, title=title)
        elif field == "description":
            payload = serialize_event_detail_message(message)
            if not payload:
                await message.answer("Неподдерживаемый тип сообщения.")
                return
            desc_plain = plain_text_preview_from_payload(payload) or "—"
            await EventsRepository.update_event(
                session,
                ev.id,
                description=desc_plain[:10000],
                detail_json=detail_payload_to_json(payload),
            )
        elif field == "event_date":
            dt = parse_event_end_date(message.text or "")
            if not dt:
                await message.answer("Не понял дату. Формат: `ДД.ММ.ГГГГ`.", parse_mode="HTML")
                return
            await EventsRepository.update_event(session, ev.id, starts_at=dt)
        else:
            await message.answer("Неизвестное поле.")
            return
    except Exception as e:
        logger.error("Ошибка редактирования мероприятия: %s", e, exc_info=True)
        await handle_error(None, e, "admin_events_edit_field_apply")
        await message.answer("❌ Ошибка сохранения.")
        await state.clear()
        return

    await state.clear()
    ev2 = await EventsRepository.get_by_id(session, ev.id)
    await message.answer(
        "✅ Обновлено.\n\n" + _format_admin_event_text(ev2),
        reply_markup=get_admin_event_view_keyboard(ev2.id, bool(ev2.matching_enabled)),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "delete"))
async def admin_events_delete_ask(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    ev = await EventsRepository.get_by_id(session, callback_data.event_id)
    if not ev:
        return
    await callback.message.edit_text(
        "⚠️ <b>Удалить мероприятие?</b>\n\nЭто действие удалит карточку и пересчитает порядок списка.",
        reply_markup=get_admin_event_delete_confirm_keyboard(ev.id),
        parse_mode="HTML",
    )


@router.callback_query(AdminEventsCallbackData.filter(F.action == "delete_confirm"))
async def admin_events_delete_confirm(
    callback: CallbackQuery,
    callback_data: AdminEventsCallbackData,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    try:
        await EventsRepository.delete_event(session, callback_data.event_id)
    except Exception as e:
        logger.error("Ошибка удаления мероприятия: %s", e, exc_info=True)
        await handle_error(None, e, "admin_events_delete_confirm")
        await callback.message.answer("❌ Не удалось удалить.")
        return
    await callback.message.edit_text("✅ Удалено. Возвращаю список…", parse_mode="HTML")
    await _admin_events_list(callback, session)


def register_handlers(dp) -> None:
    dp.include_router(router)
