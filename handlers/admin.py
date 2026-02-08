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
    AdminCallbackData,
    USERS_PAGE_PREFIX,
    USER_VIEW_PREFIX,
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
    """Запрос подтверждения очистки лайков и дизлайков"""
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
    """Выполнить очистку лайков и дизлайков"""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    deleted = 0
    async for session in get_session():
        try:
            deleted = await SwipeRepository.clear_likes_and_dislikes(session)
        except Exception as e:
            logger.exception("Ошибка при очистке лайков/дизлайков: %s", e)
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


@router.callback_query(F.data.startswith(USER_VIEW_PREFIX))
async def admin_user_view(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр одной записи архива — отдельное сообщение с полной информацией."""
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
    async for session in get_session():
        record = await AdminArchiveRepository.get_by_id(session, archive_id)
        break
    else:
        record = None
    if not record:
        await callback.message.answer("❌ Запись не найдена.")
        return
    text = "👤 <b>Данные из архива (на момент регистрации)</b>\n\n" + _format_archive_user(record)
    await callback.message.answer(text)


def register_handlers(dp) -> None:
    """Регистрация обработчиков админ-панели"""
    dp.include_router(router)
