"""
Обработчики админ-панели (только для администраторов)
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import Config
from repositories.database import get_session
from repositories.user_repository import UserRepository
from repositories.swipe_repository import SwipeRepository
from repositories.admin_archive_repository import AdminArchiveRepository, AdminUserArchive
from keyboards.admin import (
    get_admin_keyboard,
    get_admin_clear_confirm_keyboard,
    get_admin_users_page_keyboard,
    get_admin_user_view_keyboard,
    AdminCallbackData,
    USERS_PAGE_PREFIX,
    USER_VIEW_PREFIX,
    ADM_BAN_PREFIX,
    ADM_WRITE_PREFIX,
    ADM_PROFILE_PREFIX,
)
from texts.messages import (
    ADMIN_ACCESS_DENIED,
    ADMIN_PANEL_TITLE,
    ADMIN_STATS_TEMPLATE,
    ADMIN_CLEAR_SWIPES_CONFIRM,
    ADMIN_CLEAR_SWIPES_DONE,
    ADMIN_CLEAR_SWIPES_CANCELLED,
)

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    config = Config()
    return user_id in config.ADMIN_IDS


async def _get_stats_text() -> str:
    """Формирование текста статистики из БД"""
    async for session in get_session():
        try:
            users_total = await UserRepository.get_total_count(session)
            users_registered = await UserRepository.get_registered_count(session)
            swipe_stats = await SwipeRepository.get_swipe_stats(session)
        except Exception as e:
            logger.exception("Ошибка при получении статистики для админа: %s", e)
            return f"❌ Ошибка при загрузке статистики: {e}"
        break

    return ADMIN_STATS_TEMPLATE.format(
        users_total=users_total,
        users_registered=users_registered,
        swipes_total=swipe_stats["total"],
        swipes_likes=swipe_stats["likes"],
        swipes_dislikes=swipe_stats["dislikes"],
        swipes_skips=swipe_stats["skips"],
        swipes_bookmarks=swipe_stats["bookmarks"],
    )


@router.message(F.text == "/admin")
async def cmd_admin(message: Message, state: FSMContext) -> None:
    """Команда /admin — панель администратора со статистикой"""
    if not message.from_user:
        return
    if not _is_admin(message.from_user.id):
        await message.answer(ADMIN_ACCESS_DENIED)
        return

    await state.clear()
    stats_text = await _get_stats_text()
    text = f"{ADMIN_PANEL_TITLE}\n\n{stats_text}"
    await message.answer(text, reply_markup=get_admin_keyboard())


@router.callback_query(AdminCallbackData.filter(F.action == "refresh"))
async def admin_refresh(callback: CallbackQuery, state: FSMContext) -> None:
    """Обновить статистику в админ-панели"""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    await state.clear()
    stats_text = await _get_stats_text()
    text = f"{ADMIN_PANEL_TITLE}\n\n{stats_text}"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_keyboard())
    await callback.answer()


@router.callback_query(AdminCallbackData.filter(F.action == "clear_swipes"))
async def admin_clear_swipes_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос подтверждения очистки всех свайпов"""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    try:
        await callback.message.edit_text(
            ADMIN_CLEAR_SWIPES_CONFIRM,
            reply_markup=get_admin_clear_confirm_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            ADMIN_CLEAR_SWIPES_CONFIRM,
            reply_markup=get_admin_clear_confirm_keyboard(),
        )
    await callback.answer()


@router.callback_query(AdminCallbackData.filter(F.action == "clear_confirm"))
async def admin_clear_swipes_do(callback: CallbackQuery, state: FSMContext) -> None:
    """Выполнить очистку всех свайпов (лайки, дизлайки, пропуски, закладки)"""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    deleted = 0
    async for session in get_session():
        try:
            deleted = await SwipeRepository.clear_all_swipes(session)
        except Exception as e:
            logger.exception("Ошибка при очистке свайпов: %s", e)
            await callback.answer("Ошибка при очистке", show_alert=True)
            return
        break

    stats_text = await _get_stats_text()
    text = f"{ADMIN_PANEL_TITLE}\n\n{ADMIN_CLEAR_SWIPES_DONE.format(count=deleted)}\n\n{stats_text}"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_keyboard())
    await callback.answer("Готово")
    await state.clear()


@router.callback_query(AdminCallbackData.filter(F.action == "clear_cancel"))
async def admin_clear_swipes_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена очистки — вернуть панель со статистикой"""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    stats_text = await _get_stats_text()
    text = f"{ADMIN_PANEL_TITLE}\n\n{stats_text}"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_keyboard())
    await callback.answer(ADMIN_CLEAR_SWIPES_CANCELLED)
    await state.clear()


@router.callback_query(AdminCallbackData.filter(F.action == "back"))
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в админ-панель (со списка пользователей)."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await state.clear()
    stats_text = await _get_stats_text()
    text = f"{ADMIN_PANEL_TITLE}\n\n{stats_text}"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_keyboard())
    await callback.answer()


def _format_archive_user(r: AdminUserArchive) -> str:
    """Текст с аккуратной информацией из архива по одному пользователю."""
    lines = [
        f"🆔 <b>ID в архиве:</b> {r.id}",
        f"📱 <b>Telegram ID:</b> {r.telegram_id}",
        f"👤 <b>Имя:</b> {r.name or '—'}",
        f"📧 <b>Username:</b> @{r.username}" if (r.username and r.username.strip()) else "📧 <b>Username:</b> —",
        f"📞 <b>Телефон:</b> {r.phone or '—'}",
        f"🎂 <b>Возраст:</b> {r.age or '—'}",
        f"👶 <b>Несовершеннолетний:</b> {'Да' if r.is_minor else 'Нет'}",
        f"📅 <b>Дата регистрации (архив):</b> {r.archived_at.strftime('%d.%m.%Y %H:%M') if r.archived_at else '—'}",
        "",
        f"📝 <b>Краткое описание:</b>\n{r.short_description or '—'}",
        "",
        f"📄 <b>Полное описание:</b>\n{r.full_description or '—'}",
        "",
        f"⭐ <b>Качества:</b> {r.qualities or '—'}",
    ]
    return "\n".join(lines).replace("@None", "—")


PER_PAGE = 15


@router.callback_query(AdminCallbackData.filter(F.action == "users"))
async def admin_users_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать первую страницу списка пользователей (имена как кнопки)."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    async for session in get_session():
        total = await AdminArchiveRepository.get_total_count(session)
        records = await AdminArchiveRepository.get_page(session, page=0, per_page=PER_PAGE)
        break
    else:
        await callback.message.answer("❌ Ошибка загрузки архива.")
        return
    if not records:
        try:
            await callback.message.edit_text(
                "👥 <b>Архив пользователей</b>\n\nПока ни одной записи.",
                reply_markup=get_admin_users_page_keyboard([], 0, total, PER_PAGE),
            )
        except Exception:
            await callback.message.answer(
                "👥 <b>Архив пользователей</b>\n\nПока ни одной записи.",
                reply_markup=get_admin_users_page_keyboard([], 0, total, PER_PAGE),
            )
        return
    text = f"👥 <b>Архив пользователей</b>\n\nСтраница 1, всего записей: {total}. Нажми на имя для деталей."
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_page_keyboard(records, 0, total, PER_PAGE),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_users_page_keyboard(records, 0, total, PER_PAGE),
        )


@router.callback_query(F.data.startswith(USERS_PAGE_PREFIX))
async def admin_users_page(callback: CallbackQuery, state: FSMContext) -> None:
    """Пагинация: Назад / Далее по страницам архива."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    try:
        page = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return
    await callback.answer()
    async for session in get_session():
        total = await AdminArchiveRepository.get_total_count(session)
        records = await AdminArchiveRepository.get_page(session, page=page, per_page=PER_PAGE)
        break
    else:
        return
    text = f"👥 <b>Архив пользователей</b>\n\nСтраница {page + 1}, всего записей: {total}. Нажми на имя для деталей."
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_page_keyboard(records, page, total, PER_PAGE),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_users_page_keyboard(records, page, total, PER_PAGE),
        )


def _format_admin_user_view(record, user) -> str:
    """Текст карточки пользователя для админа: архив + живой статус и бан."""
    lines = [
        "👤 <b>Пользователь</b>",
        "",
        f"📱 <b>Telegram ID:</b> <code>{record.telegram_id}</code>",
        f"👤 <b>Имя:</b> {record.name or '—'}",
        f"📧 <b>Username:</b> @{record.username}" if (record.username and record.username.strip()) else "📧 <b>Username:</b> —",
        f"🎂 <b>Возраст:</b> {record.age or '—'}",
        f"🔒 <b>Бан:</b> {(user.ban_status or 'none') if user else '—'}",
        "",
        "📝 <b>Кратко:</b> " + (record.short_description[:80] + "…" if record.short_description and len(record.short_description) > 80 else (record.short_description or "—")),
    ]
    return "\n".join(lines).replace("@None", "—")


@router.callback_query(F.data.startswith(USER_VIEW_PREFIX))
async def admin_user_view(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр пользователя: инфо, кнопки бан / написать / анкета."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    try:
        archive_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return
    await callback.answer()
    record = None
    user = None
    async for session in get_session():
        record = await AdminArchiveRepository.get_by_id(session, archive_id)
        if record:
            user = await UserRepository.get_by_telegram_id(session, record.telegram_id)
        break
    if not record:
        await callback.message.answer("❌ Запись не найдена.")
        return
    ban_status = (user.ban_status or "none") if user else "none"
    text = _format_admin_user_view(record, user)
    kb = get_admin_user_view_keyboard(record.telegram_id, ban_status)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


# --- Цикл бана: none -> shadow -> full -> none ---
@router.callback_query(F.data.startswith(ADM_BAN_PREFIX))
async def admin_user_ban_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    try:
        telegram_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return
    await callback.answer()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, telegram_id)
        if not user:
            await callback.message.answer("❌ Пользователь не найден в базе.")
            return
        current = (user.ban_status or "none").strip().lower()
        if current == "none":
            next_status = "shadow"
        elif current == "shadow":
            next_status = "full"
        else:
            next_status = "none"
        await UserRepository.update(session, user, ban_status=next_status)
        record = await AdminArchiveRepository.get_first_by_telegram_id(session, telegram_id)
        user = await UserRepository.get_by_telegram_id(session, telegram_id)
        text = _format_admin_user_view(record, user) if record else f"👤 ID: {telegram_id}\n🔒 Бан: {next_status}"
        kb = get_admin_user_view_keyboard(telegram_id, next_status)
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
        break


# --- Написать пользователю: FSM ---
ADMIN_WRITE_TO_KEY = "admin_write_to"


@router.callback_query(F.data.startswith(ADM_WRITE_PREFIX))
async def admin_user_write_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    try:
        telegram_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return
    await callback.answer()
    await state.update_data(**{ADMIN_WRITE_TO_KEY: telegram_id})
    await callback.message.answer(
        "✉️ Введите сообщение для пользователя (текстом). Отправьте его в чат.\nОтмена: /cancel"
    )


async def _admin_write_filter(event, data: dict) -> bool:
    """Фильтр: только когда админ в режиме «Написать пользователю»."""
    state = data.get("state")
    if not state:
        return False
    d = await state.get_data()
    return d.get(ADMIN_WRITE_TO_KEY) is not None


@router.message(F.text == "/cancel", F.func(_admin_write_filter))
async def admin_write_cancel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.update_data(**{ADMIN_WRITE_TO_KEY: None})
    await message.answer("Отправка отменена.")


@router.message(F.text, F.func(_admin_write_filter))
async def admin_user_write_send(message: Message, state: FSMContext) -> None:
    """Если админ в режиме «Написать» — отправить сообщение пользователю."""
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    telegram_id = data.get(ADMIN_WRITE_TO_KEY)
    if telegram_id is None:
        return
    await state.update_data(**{ADMIN_WRITE_TO_KEY: None})
    try:
        await message.bot.send_message(
            telegram_id,
            "📩 <b>Сообщение от администрации:</b>\n\n" + message.text,
        )
        await message.answer("✅ Сообщение отправлено пользователю.")
    except Exception as e:
        logger.exception("Ошибка отправки сообщения пользователю: %s", e)
        await message.answer("❌ Не удалось отправить сообщение.")


# --- Посмотреть анкету пользователя ---
@router.callback_query(F.data.startswith(ADM_PROFILE_PREFIX))
async def admin_user_profile_view(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    try:
        telegram_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return
    await callback.answer()
    from handlers.swipe import format_user_profile
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, telegram_id)
        if not user:
            await callback.message.answer("❌ Пользователь не найден.")
            return
        profile_text = format_user_profile(user, compatibility=None)
        if user.photo_id:
            await callback.message.answer_photo(
                photo=user.photo_id,
                caption=profile_text,
            )
        else:
            await callback.message.answer(profile_text)
        break


def register_handlers(dp) -> None:
    """Регистрация обработчиков админ-панели"""
    dp.include_router(router)
