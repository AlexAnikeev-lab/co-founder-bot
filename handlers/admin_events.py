"""
Админ-управление мероприятиями: добавление/редактирование/удаление,
переключатель мэтчинга, просмотр зарегистрировавшихся.
"""

from __future__ import annotations

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from keyboards.admin import AdminCallbackData
from keyboards.admin_events import (
    AdminEventsCallbackData,
    AdminEventsEditCallbackData,
    get_admin_events_list_keyboard,
    get_admin_event_view_keyboard,
    get_admin_event_edit_fields_keyboard,
    get_admin_event_delete_confirm_keyboard,
)
from repositories.events_repository import EventsRepository
from repositories.user_repository import UserRepository
from services.events_matching import notify_pairs_for_event
from states.events_admin import AdminEventsStates
from utils.validators import parse_event_datetime
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    cfg = Config()
    return user_id in cfg.ADMIN_IDS


def _format_admin_event_text(ev) -> str:
    return (
        f"📅 <b>Мероприятие #{ev.position}</b>\n\n"
        f"<b>{ev.title}</b>\n\n"
        f"{ev.description}\n\n"
        f"💰 <b>Стоимость:</b> {ev.price}\n"
        f"🗓 <b>Дата и время:</b> {ev.starts_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"🔔 <b>Подбор пар:</b> {'Да' if ev.matching_enabled else 'Нет'}"
    )


async def _admin_events_list(callback: CallbackQuery, session: AsyncSession) -> None:
    items = await EventsRepository.list_items(session)
    labels: list[tuple[int, str]] = []
    for it in items:
        flag = "✅" if it.matching_enabled else "❌"
        labels.append((it.id, f"{it.position}. {it.title[:32]} ({it.starts_at.strftime('%d.%m %H:%M')}) {flag}"))
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
    await state.set_state(AdminEventsStates.waiting_for_banner)
    await callback.message.edit_text(
        "➕ <b>Добавление мероприятия</b>\n\nОтправьте баннер (картинку) одним сообщением.\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(F.text == "/cancel", AdminEventsStates.waiting_for_banner)
@router.message(F.text == "/cancel", AdminEventsStates.waiting_for_title)
@router.message(F.text == "/cancel", AdminEventsStates.waiting_for_description)
@router.message(F.text == "/cancel", AdminEventsStates.waiting_for_price)
@router.message(F.text == "/cancel", AdminEventsStates.waiting_for_datetime)
@router.message(F.text == "/cancel", AdminEventsStates.waiting_for_edit_field)
async def admin_events_cancel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Отменено. Вернитесь в /admin → 📅 Мероприятия.")


@router.message(AdminEventsStates.waiting_for_banner)
async def admin_events_add_banner(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    if not message.photo:
        await message.answer("Пожалуйста, отправьте изображение (баннер).")
        return
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["banner_file_id"] = file_id
    await state.update_data(admin_event_create=create)
    await state.set_state(AdminEventsStates.waiting_for_title)
    await message.answer("Введите <b>название</b> мероприятия (до 180 символов).", parse_mode="HTML")


@router.message(AdminEventsStates.waiting_for_title, F.text)
async def admin_events_add_title(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    title = (message.text or "").strip()
    if len(title) < 3 or len(title) > 180:
        await message.answer("Название должно быть от 3 до 180 символов.")
        return
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["title"] = title
    await state.update_data(admin_event_create=create)
    await state.set_state(AdminEventsStates.waiting_for_description)
    await message.answer("Введите <b>описание</b> мероприятия.", parse_mode="HTML")


@router.message(AdminEventsStates.waiting_for_description, F.text)
async def admin_events_add_description(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    desc = (message.text or "").strip()
    if len(desc) < 5:
        await message.answer("Описание слишком короткое. Введите подробнее.")
        return
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["description"] = desc
    await state.update_data(admin_event_create=create)
    await state.set_state(AdminEventsStates.waiting_for_price)
    await message.answer("Введите <b>стоимость</b> (например: `0`, `990₽`, `Free`).", parse_mode="HTML")


@router.message(AdminEventsStates.waiting_for_price, F.text)
async def admin_events_add_price(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    price = (message.text or "").strip()
    if len(price) < 1 or len(price) > 64:
        await message.answer("Цена должна быть от 1 до 64 символов.")
        return
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["price"] = price
    await state.update_data(admin_event_create=create)
    await state.set_state(AdminEventsStates.waiting_for_datetime)
    await message.answer("Введите <b>дату и время</b> в формате `ДД.ММ.ГГГГ ЧЧ:ММ`.\nНапример: `07.04.2026 18:30`.", parse_mode="HTML")


@router.message(AdminEventsStates.waiting_for_datetime, F.text)
async def admin_events_add_datetime(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    dt = parse_event_datetime(message.text or "")
    if not dt:
        await message.answer("Не понял дату/время. Формат: `ДД.ММ.ГГГГ ЧЧ:ММ`.", parse_mode="HTML")
        return
    data = await state.get_data()
    create = dict(data.get("admin_event_create") or {})
    create["starts_at"] = dt
    # create in DB
    try:
        ev = await EventsRepository.create(
            session,
            title=create["title"],
            description=create["description"],
            price=create["price"],
            starts_at=create["starts_at"],
            banner_file_id=create.get("banner_file_id"),
            matching_enabled=False,
        )
    except Exception as e:
        logger.error("Ошибка создания мероприятия: %s", e, exc_info=True)
        await handle_error(None, e, "admin_events_add_datetime")
        await message.answer("❌ Ошибка создания. Попробуйте позже.")
        return
    await state.clear()
    await message.answer("✅ Мероприятие добавлено. Откройте /admin → 📅 Мероприятия.")


@router.callback_query(AdminEventsCallbackData.filter(F.action == "open"))
async def admin_events_open(callback: CallbackQuery, callback_data: AdminEventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
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
async def admin_events_toggle_match(callback: CallbackQuery, callback_data: AdminEventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
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
async def admin_events_participants(callback: CallbackQuery, callback_data: AdminEventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
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


@router.callback_query(AdminEventsCallbackData.filter(F.action == "remind_pairs"))
async def admin_events_remind_pairs(callback: CallbackQuery, callback_data: AdminEventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
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
            await callback.message.answer(f"✅ Напоминания о паре отправлены: {sent} пользователям.")
        else:
            await callback.message.answer("ℹ️ Нет подходящих пар для отправки (или уведомления уже отправлены).")
    except Exception as e:
        logger.error("Ошибка ручной отправки напоминаний о паре: %s", e, exc_info=True)
        await handle_error(None, e, "admin_events_remind_pairs")
        await callback.message.answer("❌ Не удалось отправить напоминания.")


@router.callback_query(AdminEventsCallbackData.filter(F.action == "edit"))
async def admin_events_edit_menu(callback: CallbackQuery, callback_data: AdminEventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
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
async def admin_events_edit_field_pick(callback: CallbackQuery, callback_data: AdminEventsEditCallbackData, state: FSMContext, session: AsyncSession) -> None:
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
        "banner": "Отправьте новый баннер (картинку).",
        "title": "Введите новое название (3–180 символов).",
        "description": "Введите новое описание.",
        "price": "Введите новую стоимость (1–64 символа).",
        "datetime": "Введите новую дату/время в формате `ДД.ММ.ГГГГ ЧЧ:ММ`.",
    }
    await callback.message.answer("✏️ " + prompts.get(callback_data.field, "Введите новое значение."), parse_mode="HTML")


@router.message(AdminEventsStates.waiting_for_edit_field)
async def admin_events_edit_field_apply(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
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
        if field == "banner":
            if not message.photo:
                await message.answer("Пожалуйста, отправьте картинку.")
                return
            banner = message.photo[-1].file_id
            await EventsRepository.update_event(session, ev.id, banner_file_id=banner)
        elif field == "title":
            title = (message.text or "").strip()
            if len(title) < 3 or len(title) > 180:
                await message.answer("Название должно быть 3–180 символов.")
                return
            await EventsRepository.update_event(session, ev.id, title=title)
        elif field == "description":
            desc = (message.text or "").strip()
            if len(desc) < 5:
                await message.answer("Описание слишком короткое.")
                return
            await EventsRepository.update_event(session, ev.id, description=desc)
        elif field == "price":
            price = (message.text or "").strip()
            if len(price) < 1 or len(price) > 64:
                await message.answer("Цена должна быть 1–64 символа.")
                return
            await EventsRepository.update_event(session, ev.id, price=price)
        elif field == "datetime":
            dt = parse_event_datetime(message.text or "")
            if not dt:
                await message.answer("Не понял дату/время. Формат: `ДД.ММ.ГГГГ ЧЧ:ММ`.", parse_mode="HTML")
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
async def admin_events_delete_ask(callback: CallbackQuery, callback_data: AdminEventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
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
async def admin_events_delete_confirm(callback: CallbackQuery, callback_data: AdminEventsCallbackData, state: FSMContext, session: AsyncSession) -> None:
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

