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
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from keyboards.admin import (
    get_admin_activity_keyboard,
    get_admin_new_users_keyboard,
    get_admin_broadcast_keyboard,
    get_admin_keyboard,
    get_admin_clear_confirm_keyboard,
    get_admin_limits_keyboard,
    get_admin_users_page_keyboard,
    get_admin_live_users_page_keyboard,
    get_admin_user_view_keyboard,
    get_admin_premium_confirm_keyboard,
    AdminCallbackData,
    AdminPremiumCallbackData,
    USERS_LIVE_PAGE_PREFIX,
    USERS_PAGE_PREFIX,
    USERS_PREMIUM_PAGE_PREFIX,
    USER_LIVE_VIEW_PREFIX,
    USER_VIEW_PREFIX,
    ADM_BAN_PREFIX,
    ADM_WRITE_PREFIX,
    ADM_PROFILE_PREFIX,
    ADM_SWIPES_PREFIX,
)
from services.settings import get_likes_per_week_limit, set_likes_per_week_limit
from texts.messages import (
    ADMIN_ACCESS_DENIED,
    ADMIN_PANEL_TITLE,
    ADMIN_STATS_TEMPLATE,
    ADMIN_CLEAR_SWIPES_CONFIRM,
    ADMIN_CLEAR_SWIPES_DONE,
    ADMIN_CLEAR_SWIPES_CANCELLED,
    ADMIN_PREMIUM_GIVE_CONFIRM,
    ADMIN_PREMIUM_REMOVE_CONFIRM,
    ADMIN_PREMIUM_GIVE_DONE,
    ADMIN_PREMIUM_REMOVE_DONE,
)
from texts.i18n import t
from aiogram.filters import StateFilter
from states.admin import AdminSearchStates, AdminBroadcastStates, AdminWriteToUserStates

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


@router.message(F.text == "/test_payment_group")
async def cmd_test_payment_group(message: Message) -> None:
    """Тест: отправить служебное сообщение в группу оплаты из /test_payment_group (только для админа)."""
    if not message.from_user:
        return
    if not _is_admin(message.from_user.id):
        await message.answer(ADMIN_ACCESS_DENIED)
        return
    cfg = Config()
    if cfg.PAYMENT_GROUP_ID is None:
        await message.answer("PAYMENT_GROUP_ID не задан в .env — отправлять некуда.")
        return
    try:
        await message.bot.send_message(
            chat_id=cfg.PAYMENT_GROUP_ID,
            text="🧪 Тестовое сообщение в группу оплаты от /test_payment_group.",
        )
        await message.answer(f"✅ Тестовое сообщение отправлено в чат {cfg.PAYMENT_GROUP_ID}.")
    except Exception as e:
        logger.error("Ошибка отправки тестового сообщения в группу оплаты: %s", e, exc_info=True)
        await message.answer(f"❌ Не удалось отправить сообщение в PAYMENT_GROUP_ID={cfg.PAYMENT_GROUP_ID}. Проверь права бота в группе.")


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


LIMITS_TITLE = "⚙️ <b>Лимиты</b>\n\nОбычные лайки (🤝) — сколько раз в неделю пользователь может поставить лайк (0 = без лимита)."


@router.callback_query(AdminCallbackData.filter(F.action == "limits"))
async def admin_limits(callback: CallbackQuery, state: FSMContext) -> None:
    """Экран настройки лимитов (лайков в неделю)."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    current = get_likes_per_week_limit()
    text = f"{LIMITS_TITLE}\n\nТекущий лимит лайков в неделю: <b>{current if current > 0 else 'без лимита'}</b>"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_limits_keyboard(current))
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_limits_keyboard(current))
    await callback.answer()


@router.callback_query(AdminCallbackData.filter(F.action.startswith("set_likes_limit_")))
async def admin_set_likes_limit(callback: CallbackQuery, callback_data: AdminCallbackData, state: FSMContext) -> None:
    """Установить лимит лайков в неделю (0 = без лимита)."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    try:
        suffix = callback_data.action.replace("set_likes_limit_", "")
        n = int(suffix)
    except ValueError:
        await callback.answer("Ошибка значения", show_alert=True)
        return

    set_likes_per_week_limit(max(0, n))
    current = get_likes_per_week_limit()
    text = f"{LIMITS_TITLE}\n\nТекущий лимит лайков в неделю: <b>{current if current > 0 else 'без лимита'}</b>"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_limits_keyboard(current))
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_limits_keyboard(current))
    label = "без лимита" if current == 0 else str(current)
    await callback.answer(f"Лимит лайков установлен: {label}")


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


# --- Поиск пользователя ---
ADMIN_SEARCH_KEY = "admin_search"
BROADCAST_KEY = "admin_broadcast"


@router.callback_query(AdminCallbackData.filter(F.action == "search"))
async def admin_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало поиска: запрос ввода."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    from states.admin import AdminSearchStates
    await state.set_state(AdminSearchStates.waiting_for_search_query)
    text = (
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введи Telegram ID, username (без @), номер телефона или имя.\n"
        "Отмена: /cancel"
    )
    try:
        await callback.message.edit_text(text)
    except Exception:
        await callback.message.answer(text)


async def _admin_fsm_filter(event, *args, **kwargs) -> bool:
    """Админ в одном из FSM состояний (поиск, рассылка)."""
    from states.admin import AdminSearchStates, AdminBroadcastStates
    state = kwargs.get("state")
    if not state:
        return False
    s = await state.get_state()
    return s in (
        AdminSearchStates.waiting_for_search_query,
        AdminBroadcastStates.waiting_for_message,
        AdminBroadcastStates.waiting_for_confirm,
    )


@router.message(F.text == "/cancel", F.func(_admin_fsm_filter))
async def admin_fsm_cancel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    stats_text = await _get_stats_text()
    await message.answer(f"{ADMIN_PANEL_TITLE}\n\n{stats_text}", reply_markup=get_admin_keyboard())


@router.message(AdminSearchStates.waiting_for_search_query, F.text)
async def admin_search_process(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    query = (message.text or "").strip()
    if not query:
        await message.answer("Введи запрос для поиска.")
        return
    users = []
    async for session in get_session():
        users = await UserRepository.search_users(session, query)
        break
    if not users:
        await message.answer(f"❌ По запросу «{query}» никого не найдено.")
        return
    if len(users) == 1:
        u = users[0]
        record = None
        async for session in get_session():
            record = await AdminArchiveRepository.get_first_by_telegram_id(session, u.telegram_id)
            break
        ban_status = (u.ban_status or "none") if u else "none"
        has_premium = bool(getattr(u, "subscription_active", False))
        text = _format_admin_user_view(record or u, u)
        kb = get_admin_user_view_keyboard(u.telegram_id, ban_status, has_premium=has_premium)
        await message.answer(text, reply_markup=kb)
    else:
        lines = [f"Найдено {len(users)} человек. Нажми для деталей:"]
        builder = InlineKeyboardBuilder()
        for u in users[:20]:
            label = (u.name or f"ID{u.telegram_id}").strip()[:30]
            builder.add(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{USER_LIVE_VIEW_PREFIX}{u.telegram_id}",
                )
            )
        builder.adjust(1)
        builder.add(InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack()))
        await message.answer("\n".join(lines), reply_markup=builder.as_markup())


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
    """Показать первую страницу списка актуальных пользователей (живые профили)."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    async for session in get_session():
        total = await UserRepository.get_registered_count(session)
        records = await UserRepository.get_registered_page(
            session, page=0, per_page=PER_PAGE
        )
        break
    else:
        await callback.message.answer("❌ Ошибка загрузки списка пользователей.")
        return
    if not records:
        try:
            await callback.message.edit_text(
                "👥 <b>Пользователи</b>\n\nПока ни одного актуального профиля.",
                reply_markup=get_admin_live_users_page_keyboard(
                    [], 0, total, PER_PAGE
                ),
            )
        except Exception:
            await callback.message.answer(
                "👥 <b>Пользователи</b>\n\nПока ни одного актуального профиля.",
                reply_markup=get_admin_live_users_page_keyboard(
                    [], 0, total, PER_PAGE
                ),
            )
        return
    text = (
        "👥 <b>Пользователи</b>\n\n"
        f"Страница 1, всего актуальных профилей: {total}.\n"
        "Нажми на имя для деталей."
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_live_users_page_keyboard(
                records, 0, total, PER_PAGE
            ),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_live_users_page_keyboard(
                records, 0, total, PER_PAGE
            ),
        )


@router.callback_query(F.data.startswith(USERS_LIVE_PAGE_PREFIX))
async def admin_users_page(callback: CallbackQuery, state: FSMContext) -> None:
    """Пагинация: Назад / Далее по страницам актуальных пользователей."""
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
        total = await UserRepository.get_registered_count(session)
        records = await UserRepository.get_registered_page(
            session, page=page, per_page=PER_PAGE
        )
        break
    else:
        return
    text = (
        "👥 <b>Пользователи</b>\n\n"
        f"Страница {page + 1}, всего актуальных профилей: {total}.\n"
        "Нажми на имя для деталей."
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_live_users_page_keyboard(
                records, page, total, PER_PAGE
            ),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_live_users_page_keyboard(
                records, page, total, PER_PAGE
            ),
        )


# --- Активность ---
@router.callback_query(AdminCallbackData.filter(F.action == "activity"))
async def admin_activity_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    text = "📈 <b>Активность пользователей</b>\n\nВыбери период:"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_activity_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_activity_keyboard())


@router.callback_query(AdminCallbackData.filter(F.action.in_(("activity_7", "activity_30", "inactive_30"))))
async def admin_activity_show(callback: CallbackQuery, callback_data: AdminCallbackData, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    action = callback_data.action
    days = 7 if "7" in action else 30
    is_inactive = "inactive" in action
    users = []
    async for session in get_session():
        if is_inactive:
            users = await UserRepository.get_inactive_more_than_days(session, days)
        else:
            users = await UserRepository.get_active_in_last_days(session, days)
        break
    label = f"Не заходили {days}+ дней" if is_inactive else f"Активные за {days} дней"
    text = f"📈 <b>{label}</b>\n\nВсего: {len(users)}. Нажми на имя для деталей."
    builder = InlineKeyboardBuilder()
    for u in users[:15]:
        builder.add(
            InlineKeyboardButton(
                text=(u.name or f"ID{u.telegram_id}")[:30],
                callback_data=f"{USER_LIVE_VIEW_PREFIX}{u.telegram_id}",
            )
        )
    builder.adjust(1)
    builder.add(InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack()))
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())


# --- Новые за период ---
@router.callback_query(AdminCallbackData.filter(F.action == "new_users"))
async def admin_new_users_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    text = "🆕 <b>Новые пользователи</b>\n\nВыбери период:"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_new_users_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_new_users_keyboard())


@router.callback_query(AdminCallbackData.filter(F.action.in_(("new_1", "new_7", "new_30"))))
async def admin_new_users_show(callback: CallbackQuery, callback_data: AdminCallbackData, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    action = callback_data.action
    days = 1 if action == "new_1" else (7 if action == "new_7" else 30)
    users = []
    async for session in get_session():
        users = await UserRepository.get_registered_since(session, days)
        break
    label = {1: "Сегодня", 7: "За неделю", 30: "За месяц"}.get(days, f"{days} дней")
    text = f"🆕 <b>Новые за {label}</b>\n\nВсего: {len(users)}. Нажми на имя для деталей."
    builder = InlineKeyboardBuilder()
    for u in users[:15]:
        builder.add(
            InlineKeyboardButton(
                text=(u.name or f"ID{u.telegram_id}")[:30],
                callback_data=f"{USER_LIVE_VIEW_PREFIX}{u.telegram_id}",
            )
        )
    builder.adjust(1)
    builder.add(InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack()))
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())


# --- Массовая рассылка ---
@router.callback_query(AdminCallbackData.filter(F.action == "broadcast"))
async def admin_broadcast_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    text = "📢 <b>Массовая рассылка</b>\n\nВыбери кому отправить:"
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_broadcast_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_broadcast_keyboard())


def _get_broadcast_recipients_filter(action: str):
    """По action возвращает список telegram_id получателей."""
    async def _get(session):
        if "broadcast_all" in action:
            users = await UserRepository.get_all_registered_for_export(session)
        elif "broadcast_active_7" in action:
            users = await UserRepository.get_active_in_last_days(session, 7)
        elif "broadcast_active_30" in action:
            users = await UserRepository.get_active_in_last_days(session, 30)
        elif "broadcast_premium" in action:
            users = []
            all_u = await UserRepository.get_all_registered_for_export(session)
            users = [u for u in all_u if getattr(u, "subscription_active", False)]
        elif "broadcast_new_7" in action:
            users = await UserRepository.get_registered_since(session, 7)
        else:
            users = await UserRepository.get_all_registered_for_export(session)
        return [u.telegram_id for u in users]
    return _get


@router.callback_query(AdminCallbackData.filter(F.action.startswith("broadcast_")))
async def admin_broadcast_choose(callback: CallbackQuery, callback_data: AdminCallbackData, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    action = callback_data.action
    await state.update_data(broadcast_filter=action)
    await state.set_state(AdminBroadcastStates.waiting_for_message)
    text = "📢 Введи текст сообщения для рассылки (поддерживается HTML).\nОтмена: /cancel"
    try:
        await callback.message.edit_text(text)
    except Exception:
        await callback.message.answer(text)


@router.message(AdminBroadcastStates.waiting_for_message, F.text)
async def admin_broadcast_send(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    action = data.get("broadcast_filter") or "broadcast_all"
    await state.clear()
    recipients = []
    async for session in get_session():
        getter = _get_broadcast_recipients_filter(action)
        recipients = await getter(session)
        break
    if not recipients:
        await message.answer("❌ Нет получателей.")
        return
    sent = 0
    errors: list[str] = []
    for tid in recipients:
        try:
            await message.bot.send_message(
                tid,
                message.text or "",
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            err_text = str(e).replace("<", "").replace(">", "")[:200]
            errors.append(f"ID {tid}: {err_text}")
            logger.warning("Рассылка не доставлена tid=%s: %s", tid, e)
    report = f"✅ Отправлено: {sent}. Не доставлено: {len(errors)}."
    if errors:
        report += "\n\n❌ Ошибки:\n" + "\n".join(errors[:15])
        if len(errors) > 15:
            report += f"\n... и ещё {len(errors) - 15}"
    await message.answer(report)


# --- Премиум по дате ---
@router.callback_query(AdminCallbackData.filter(F.action == "premium_expiring"))
async def admin_premium_expiring(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    users = []
    async for session in get_session():
        users = await UserRepository.get_premium_expiring_in_days(session, 30)
        break
    text = f"📅 <b>Премиум истекает в ближайшие 30 дней</b>\n\nВсего: {len(users)}."
    if not users:
        text += "\n\nНет таких пользователей."
    builder = InlineKeyboardBuilder()
    for u in users[:15]:
        exp = getattr(u, "subscription_until", None)
        exp_str = exp.strftime("%d.%m.%Y") if exp else "?"
        builder.add(
            InlineKeyboardButton(
                text=f"{(u.name or f'ID{u.telegram_id}')[:25]} до {exp_str}",
                callback_data=f"{USER_LIVE_VIEW_PREFIX}{u.telegram_id}",
            )
        )
    builder.adjust(1)
    builder.add(InlineKeyboardButton(text="🔙 К админ-панели", callback_data=AdminCallbackData(action="back").pack()))
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())


# --- Экспорт в CSV ---
@router.callback_query(AdminCallbackData.filter(F.action == "export_csv"))
async def admin_export_csv(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    import csv
    import io
    users = []
    async for session in get_session():
        users = await UserRepository.get_all_registered_for_export(session)
        break
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["telegram_id", "name", "username", "phone", "age", "created_at", "updated_at", "subscription_active"])
    for u in users:
        writer.writerow([
            u.telegram_id,
            u.name or "",
            u.username or "",
            u.phone or "",
            u.age or "",
            u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
            u.updated_at.strftime("%Y-%m-%d %H:%M") if u.updated_at else "",
            "1" if getattr(u, "subscription_active", False) else "0",
        ])
    content = output.getvalue().encode("utf-8-sig")
    file = BufferedInputFile(content, filename="users_export.csv")
    try:
        await callback.message.answer_document(document=file, caption=f"Экспорт: {len(users)} пользователей")
    except Exception as e:
        logger.exception("Ошибка экспорта CSV: %s", e)
        await callback.message.answer(f"❌ Ошибка экспорта: {e}")


@router.callback_query(AdminCallbackData.filter(F.action == "users_archive"))
async def admin_users_archive_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать первую страницу архива пользователей (актуальные и удалённые)."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()
    async for session in get_session():
        total = await AdminArchiveRepository.get_total_count(session)
        records = await AdminArchiveRepository.get_page(
            session, page=0, per_page=PER_PAGE
        )
        break
    else:
        await callback.message.answer("❌ Ошибка загрузки архива.")
        return
    if not records:
        try:
            await callback.message.edit_text(
                "👥 <b>Архив пользователей</b>\n\nПока ни одной записи.",
                reply_markup=get_admin_users_page_keyboard(
                    [], 0, total, PER_PAGE, prefix=USERS_PAGE_PREFIX
                ),
            )
        except Exception:
            await callback.message.answer(
                "👥 <b>Архив пользователей</b>\n\nПока ни одной записи.",
                reply_markup=get_admin_users_page_keyboard(
                    [], 0, total, PER_PAGE, prefix=USERS_PAGE_PREFIX
                ),
            )
        return
    text = (
        "👥 <b>Архив пользователей</b>\n\n"
        f"Страница 1, всего записей: {total}. "
        "Актуальные и удалённые пользователи.\n"
        "Нажми на имя для деталей."
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records, 0, total, PER_PAGE, prefix=USERS_PAGE_PREFIX
            ),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records, 0, total, PER_PAGE, prefix=USERS_PAGE_PREFIX
            ),
        )


@router.callback_query(F.data.startswith(USERS_PAGE_PREFIX))
async def admin_users_archive_page(callback: CallbackQuery, state: FSMContext) -> None:
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
        records = await AdminArchiveRepository.get_page(
            session, page=page, per_page=PER_PAGE
        )
        break
    else:
        return
    text = (
        "👥 <b>Архив пользователей</b>\n\n"
        f"Страница {page + 1}, всего записей: {total}. "
        "Актуальные и удалённые пользователи.\n"
        "Нажми на имя для деталей."
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records, page, total, PER_PAGE, prefix=USERS_PAGE_PREFIX
            ),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records, page, total, PER_PAGE, prefix=USERS_PAGE_PREFIX
            ),
        )


@router.callback_query(AdminCallbackData.filter(F.action == "users_premium_matches"))
async def admin_users_premium_matches_list(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """
    Показать первую страницу списка пользователей архива,
    у которых активная подписка и есть хотя бы один мэтч.
    """
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return
    await callback.answer()

    async for session in get_session():
        # telegram_id с хотя бы одним взаимным лайком
        matched_ids = await SwipeRepository.get_users_with_mutual_matches(session)
        # только те, у кого активная подписка
        premium_users = await UserRepository.get_premium_by_telegram_ids(
            session, matched_ids
        )
        premium_ids = [u.telegram_id for u in premium_users]
        records_all = await AdminArchiveRepository.get_by_telegram_ids_sorted(
            session, premium_ids
        )
        break
    else:
        await callback.message.answer("❌ Ошибка загрузки архива.")
        return

    total = len(records_all)
    if not records_all:
        try:
            await callback.message.edit_text(
                "👥 <b>Архив пользователей</b>\n\n"
                "Фильтр: 💎 премиум с мэтчами.\n\n"
                "Пока ни одной записи.",
                reply_markup=get_admin_users_page_keyboard(
                    [], 0, total, PER_PAGE, prefix=USERS_PREMIUM_PAGE_PREFIX
                ),
            )
        except Exception:
            await callback.message.answer(
                "👥 <b>Архив пользователей</b>\n\n"
                "Фильтр: 💎 премиум с мэтчами.\n\n"
                "Пока ни одной записи.",
                reply_markup=get_admin_users_page_keyboard(
                    [], 0, total, PER_PAGE, prefix=USERS_PREMIUM_PAGE_PREFIX
                ),
            )
        return

    # Первая страница
    page = 0
    records_page = records_all[page * PER_PAGE : (page + 1) * PER_PAGE]
    text = (
        "👥 <b>Архив пользователей</b>\n\n"
        "Фильтр: 💎 премиум с мэтчами.\n\n"
        f"Страница 1, всего записей: {total}. "
        "Актуальные и удалённые пользователи.\n"
        "Нажми на имя для деталей."
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records_page, page, total, PER_PAGE, prefix=USERS_PREMIUM_PAGE_PREFIX
            ),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records_page, page, total, PER_PAGE, prefix=USERS_PREMIUM_PAGE_PREFIX
            ),
        )


@router.callback_query(F.data.startswith(USERS_PREMIUM_PAGE_PREFIX))
async def admin_users_premium_matches_page(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Пагинация по архиву с фильтром «премиум + мэтчи»."""
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
        matched_ids = await SwipeRepository.get_users_with_mutual_matches(session)
        premium_users = await UserRepository.get_premium_by_telegram_ids(
            session, matched_ids
        )
        premium_ids = [u.telegram_id for u in premium_users]
        records_all = await AdminArchiveRepository.get_by_telegram_ids_sorted(
            session, premium_ids
        )
        break
    else:
        return

    total = len(records_all)
    records_page = records_all[page * PER_PAGE : (page + 1) * PER_PAGE]
    text = (
        "👥 <b>Архив пользователей</b>\n\n"
        "Фильтр: 💎 премиум с мэтчами.\n\n"
        f"Страница {page + 1}, всего записей: {total}. "
        "Актуальные и удалённые пользователи.\n"
        "Нажми на имя для деталей."
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records_page,
                page,
                total,
                PER_PAGE,
                prefix=USERS_PREMIUM_PAGE_PREFIX,
            ),
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_users_page_keyboard(
                records_page,
                page,
                total,
                PER_PAGE,
                prefix=USERS_PREMIUM_PAGE_PREFIX,
            ),
        )


def _format_admin_user_view(record, user) -> str:
    """Текст карточки пользователя для админа: контакты, статус и полная анкета."""
    import html
    from utils.user_display import format_age_label, get_display_age

    live = user
    telegram_id = (
        getattr(live, "telegram_id", None)
        or getattr(record, "telegram_id", None)
        or "—"
    )
    name = (getattr(live, "name", None) or getattr(record, "name", None) or "—")
    username = getattr(live, "username", None) or getattr(record, "username", None) or ""
    phone = getattr(live, "phone", None) or getattr(record, "phone", None) or ""
    city = getattr(live, "city", None) or getattr(record, "city", None) or ""
    archived_at = getattr(record, "archived_at", None)

    display_age = get_display_age(live) if live else getattr(record, "age", None)
    age_str = format_age_label(display_age, "ru") if display_age is not None else "—"

    lines = [
        "👤 <b>Пользователь</b>",
        "",
        f"📱 <b>Telegram ID:</b> <code>{telegram_id}</code>",
        f"👤 <b>Имя:</b> {html.escape(str(name))}",
        (
            f"📧 <b>Username:</b> @{username}"
            if (username and str(username).strip())
            else "📧 <b>Username:</b> —"
        ),
        f"📞 <b>Телефон:</b> {phone or '—'}",
        f"🎂 <b>Возраст:</b> {age_str}",
        f"🏙 <b>Город:</b> {html.escape(city) if city else '—'}",
        f"🔒 <b>Бан:</b> {(live.ban_status or 'none') if live else '—'}",
        f"💎 <b>Премиум:</b> {'активен' if (live and getattr(live, 'subscription_active', False)) else 'нет'}",
    ]
    if archived_at:
        lines.append(f"📅 <b>Архив:</b> {archived_at.strftime('%d.%m.%Y %H:%M')}")

    short_desc = getattr(live, "short_description", None) or getattr(record, "short_description", None)
    full_desc = getattr(live, "full_description", None) or getattr(record, "full_description", None)
    qualities = getattr(live, "qualities", None) or getattr(record, "qualities", None)

    lines.append("")
    lines.append(f"📝 <b>Краткое описание:</b>\n{html.escape(short_desc) if short_desc else '—'}")
    lines.append("")
    if qualities:
        lines.append("⭐ <b>Качества:</b>")
        for ln in str(qualities).split("\n"):
            ln = ln.strip()
            if not ln:
                continue
            if "|" in ln:
                em, txt = ln.split("|", 1)
                lines.append(f"{em.strip()} {html.escape(txt.strip())}")
            else:
                lines.append(html.escape(ln))
        lines.append("")
    lines.append(f"📄 <b>Полное описание:</b>\n{html.escape(full_desc) if full_desc else '—'}")

    return "\n".join(lines).replace("@None", "—")


@router.callback_query(F.data.startswith(USER_VIEW_PREFIX))
async def admin_user_view(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр пользователя из архива: инфо, кнопки бан / написать / анкета."""
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
    has_premium = bool(user and getattr(user, "subscription_active", False))
    kb = get_admin_user_view_keyboard(record.telegram_id, ban_status, has_premium=has_premium)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith(USER_LIVE_VIEW_PREFIX))
async def admin_live_user_view(callback: CallbackQuery, state: FSMContext) -> None:
    """Просмотр актуального пользователя по telegram_id (через архив + live-данные)."""
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
    record = None
    user = None
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, telegram_id)
        record = await AdminArchiveRepository.get_first_by_telegram_id(
            session, telegram_id
        )
        break
    if not user and not record:
        await callback.message.answer("❌ Пользователь не найден.")
        return
    ban_status = (user.ban_status or "none") if user else "none"
    text = _format_admin_user_view(record, user)
    has_premium = bool(user and getattr(user, "subscription_active", False))
    kb = get_admin_user_view_keyboard(telegram_id, ban_status, has_premium=has_premium)
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
        has_premium = bool(user and getattr(user, "subscription_active", False))
        text = _format_admin_user_view(record, user) if record else f"👤 ID: {telegram_id}\n🔒 Бан: {next_status}"
        kb = get_admin_user_view_keyboard(telegram_id, next_status, has_premium=has_premium)
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
    await state.set_state(AdminWriteToUserStates.waiting_for_message)
    await callback.message.answer(
        "✉️ Введите сообщение для пользователя (текстом). Отправьте его в чат.\nОтмена: /cancel"
    )


@router.message(F.text == "/cancel", StateFilter(AdminWriteToUserStates.waiting_for_message))
async def admin_write_cancel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("Отправка отменена.")


@router.message(StateFilter(AdminWriteToUserStates.waiting_for_message), F.text)
async def admin_user_write_send(message: Message, state: FSMContext) -> None:
    """Если админ в режиме «Написать» — отправить сообщение пользователю."""
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    telegram_id = data.get(ADMIN_WRITE_TO_KEY)
    if telegram_id is None:
        return
    text_to_send = "📩 <b>Сообщение от администрации:</b>\n\n" + (message.text or "")
    try:
        await message.bot.send_message(
            chat_id=telegram_id,
            text=text_to_send,
            parse_mode="HTML",
        )
        await state.clear()
        await message.answer("✅ Сообщение отправлено пользователю.")
    except Exception as e:
        err_msg = str(e).replace("<", "").replace(">", "")[:300]
        logger.exception("Ошибка отправки сообщения пользователю tid=%s: %s", telegram_id, e)
        await state.clear()
        await message.answer(f"❌ Не удалось отправить пользователю (ID {telegram_id}): {err_msg}")


# --- Свайпы/мэтчи пользователя ---
@router.callback_query(F.data.startswith(ADM_SWIPES_PREFIX))
async def admin_user_swipes_view(callback: CallbackQuery, state: FSMContext) -> None:
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
    stats = {}
    match_names = []
    async for session in get_session():
        stats = await SwipeRepository.get_swipe_stats_for_user(session, telegram_id)
        for mid in stats.get("match_ids", [])[:15]:
            u = await UserRepository.get_by_telegram_id(session, mid)
            if u:
                match_names.append(f"• {u.name or f'ID{mid}'} (ID: {mid})")
        break
    text = (
        "📊 <b>Свайпы и мэтчи</b>\n\n"
        f"❤️ Лайков поставлено: {stats.get('likes_given', 0)}\n"
        f"❤️ Лайков получено: {stats.get('likes_received', 0)}\n"
        f"👎 Дизлайков: {stats.get('dislikes_given', 0)}\n"
        f"🤝 Мэтчей: {len(stats.get('match_ids', []))}\n"
    )
    if match_names:
        text += "\n<b>С кем мэтч:</b>\n" + "\n".join(match_names)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=AdminCallbackData(action="users").pack()))
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())


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
    from handlers.swipe import build_translated_profile_text, _get_user_profile
    from repositories.test_repository import TestResultRepository
    from services.compatibility_service import CompatibilityService

    admin_id = callback.from_user.id
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, telegram_id)
        if not user:
            await callback.message.answer("❌ Пользователь не найден.")
            return
        viewer_lang = "ru"
        admin_user = await UserRepository.get_by_telegram_id(session, admin_id)
        if admin_user:
            viewer_lang = getattr(admin_user, "language", None) or "ru"

        compatibility = None
        tr_viewer = await TestResultRepository.get_by_user_id(session, admin_id)
        tr_shown = await TestResultRepository.get_by_user_id(session, telegram_id)
        if tr_viewer and tr_shown and tr_viewer.main_test_completed and tr_shown.main_test_completed:
            pv = _get_user_profile(tr_viewer)
            pl = _get_user_profile(tr_shown)
            if pv and pl:
                compatibility, _ = CompatibilityService.calculate_compatibility_detailed(pv, pl)

        from utils.telegram_media import send_profile_card

        profile_text = await build_translated_profile_text(
            user, viewer_lang, compatibility, expanded=False
        )
        await send_profile_card(
            callback.message,
            photo_id=user.photo_id,
            text=profile_text,
            parse_mode="HTML",
        )
        break


@router.callback_query(AdminPremiumCallbackData.filter(F.action.in_(("ask_give", "ask_remove"))))
async def admin_premium_ask(callback: CallbackQuery, callback_data: AdminPremiumCallbackData, state: FSMContext) -> None:
    """Запрос подтверждения выдачи / снятия премиум-подписки."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    await callback.answer()
    give = callback_data.action == "ask_give"
    text = ADMIN_PREMIUM_GIVE_CONFIRM if give else ADMIN_PREMIUM_REMOVE_CONFIRM
    kb = get_admin_premium_confirm_keyboard(callback_data.telegram_id, give=give)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(AdminPremiumCallbackData.filter(F.action.in_(("confirm_give", "confirm_remove"))))
async def admin_premium_confirm(callback: CallbackQuery, callback_data: AdminPremiumCallbackData, state: FSMContext) -> None:
    """Выдать или снять премиум-подписку после подтверждения."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    await callback.answer()
    give = callback_data.action == "confirm_give"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback_data.telegram_id)
        if not user:
            await callback.message.answer("❌ Пользователь не найден.")
            return
        if give:
            await UserRepository.update(
                session,
                user,
                subscription_active=True,
                subscription_until=None,
                super_like_used=False,
            )
            done_text = ADMIN_PREMIUM_GIVE_DONE
            # Уведомление пользователю о вручении подписки админом
            try:
                lang = getattr(user, "language", None) or "ru"
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=t(lang, "subscription_admin_give"),
                )
            except Exception as e:
                logger.error("Не удалось отправить уведомление о подписке (админ) user_id=%s: %s", user.telegram_id, e)
        else:
            await UserRepository.update(
                session,
                user,
                subscription_active=False,
            )
            done_text = ADMIN_PREMIUM_REMOVE_DONE

        record = await AdminArchiveRepository.get_first_by_telegram_id(session, callback_data.telegram_id)
        user = await UserRepository.get_by_telegram_id(session, callback_data.telegram_id)
        ban_status = (user.ban_status or "none") if user else "none"
        has_premium = bool(user and getattr(user, "subscription_active", False))
        text = _format_admin_user_view(record, user) if record else done_text
        kb = get_admin_user_view_keyboard(callback_data.telegram_id, ban_status, has_premium=has_premium)
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
        break


@router.callback_query(AdminPremiumCallbackData.filter(F.action == "cancel"))
async def admin_premium_cancel(callback: CallbackQuery, callback_data: AdminPremiumCallbackData, state: FSMContext) -> None:
    """Отмена операции с премиум-подпиской — возврат к карточке пользователя."""
    if not callback.from_user or not callback.message:
        return
    if not _is_admin(callback.from_user.id):
        await callback.answer(ADMIN_ACCESS_DENIED, show_alert=True)
        return

    await callback.answer()
    record = None
    user = None
    async for session in get_session():
        record = await AdminArchiveRepository.get_first_by_telegram_id(session, callback_data.telegram_id)
        user = await UserRepository.get_by_telegram_id(session, callback_data.telegram_id)
        break
    if not user and not record:
        await callback.message.answer("❌ Пользователь не найден.")
        return
    if not record:
        from types import SimpleNamespace
        record = SimpleNamespace(
            telegram_id=callback_data.telegram_id,
            name=getattr(user, "name", None),
            username=getattr(user, "username", None),
            phone=getattr(user, "phone", None),
            age=getattr(user, "age", None),
            archived_at=None,
        )

    ban_status = (user.ban_status or "none") if user else "none"
    has_premium = bool(user and getattr(user, "subscription_active", False))
    text = _format_admin_user_view(record, user)
    kb = get_admin_user_view_keyboard(callback_data.telegram_id, ban_status, has_premium=has_premium)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


def register_handlers(dp) -> None:
    """Регистрация обработчиков админ-панели"""
    dp.include_router(router)
