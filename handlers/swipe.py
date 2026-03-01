"""
Обработчики для свайпов (поиск партнеров)
"""

import html
import logging
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import BaseFilter
from repositories.database import get_session
from repositories.user_repository import User, UserRepository
from repositories.test_repository import TestResult, TestResultRepository
from repositories.swipe_repository import SwipeRepository
from services.compatibility_service import CompatibilityService
from keyboards.swipe import (
    get_swipe_keyboard,
    get_swipe_keyboard_from_notification,
    get_swipe_keyboard_expand_only,
    get_partners_reply_keyboard,
    PARTNERS_BTN_LIKE,
    PARTNERS_BTN_BOOKMARK,
    PARTNERS_BTN_DISLIKE,
    PARTNERS_BTN_SUPER_LIKE,
)
from utils.match_logger import log_match_comparison
from utils.compatibility_logger import log_compatibility_calculation, log_compatibility_show_minimal
from keyboards.menu import get_main_menu_keyboard
from keyboards.common import get_back_button
from texts.i18n import t, text_options
from texts.messages import FULL_DESCRIPTION_HINT_SNIPPET
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_

router = Router()
logger = logging.getLogger(__name__)

async def _send_like_notification(
    bot: Bot,
    chat_id: int,
    swiper_name: str,
    swiper_user_id: int,
    lang: str = "ru",
) -> bool:
    """
    Отправить уведомление «вас лайкнули» в чат chat_id.
    lang — язык получателя (кого лайкнули).
    """
    try:
        view_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "like_notification_btn_view"), callback_data=f"view_liker:{swiper_user_id}")]
        ])
        notif_text = t(lang, "like_notification_text").format(swiper_name=swiper_name)
        await bot.send_message(
            chat_id=chat_id,
            text=notif_text,
            reply_markup=view_kb,
            parse_mode="HTML",
        )
        logger.info("Уведомление о лайке отправлено: chat_id=%s, от swiper_id=%s", chat_id, swiper_user_id)
        return True
    except Exception as e:
        logger.error(
            "Не удалось отправить уведомление о лайке chat_id=%s (возможно, пользователь не начинал бота или заблокировал): %s",
            chat_id,
            e,
            exc_info=True,
        )
        return False


class _FilterInPartners(BaseFilter):
    """Сообщение обрабатываем только если пользователь в разделе Партнёры и смотрит анкету (лайк/закладка/дизлайк)."""

    async def __call__(self, event: Message, **kwargs: object) -> bool:
        state: FSMContext | None = kwargs.get("state") if kwargs else None
        if not state:
            return False
        d = await state.get_data()
        return bool(d.get("in_partners") and d.get("current_partner_id"))


class _FilterNotInPartners(BaseFilter):
    """Вход в раздел Партнёры по кнопке меню — только когда ещё не внутри раздела."""

    async def __call__(self, event: Message | CallbackQuery, **kwargs: object) -> bool:
        if isinstance(event, CallbackQuery):
            return True
        state: FSMContext | None = kwargs.get("state") if kwargs else None
        if not state:
            return True
        d = await state.get_data()
        return not d.get("in_partners")


def _clean_full_description(raw: Optional[str]) -> str:
    """
    Возвращает описание для показа. Если в тексте сохранена подсказка регистрации
    («Максимум 1000 символов», «Расскажи подробнее о себе»), считаем описание пустым.
    """
    if not raw or not raw.strip():
        return ""
    text = raw.strip()
    # Если это явно подсказка (или пользователь вставил её в начало) — не показываем
    if FULL_DESCRIPTION_HINT_SNIPPET in text and "Расскажи подробнее о себе" in text:
        return ""
    # Удаляем только вставленные фразы подсказки, оставляя остальной текст
    for phrase in (
        "Максимум 1000 символов.",
        "Расскажи подробнее о себе, своем опыте, интересах и целях.",
        "Что ты хочешь создать? Какие у тебя навыки?",
    ):
        text = text.replace(phrase, "").strip()
    for tag in ("<i>", "</i>", "<b>", "</b>"):
        text = text.replace(tag, "")
    return text.strip()


def _parse_qualities_display(qualities_raw: str | None, lang: str) -> list[str]:
    """Разбор qualities: формат 'emoji|text\\n...' или старый 'q1, q2, q3'. Возвращает список строк для отображения (emoji + текст или '• q')."""
    from texts.i18n import t
    if not qualities_raw or not qualities_raw.strip():
        return []
    lines = [ln.strip() for ln in qualities_raw.strip().split("\n") if ln.strip()]
    out = []
    for line in lines[:3]:
        if "|" in line:
            emoji, text = line.split("|", 1)
            out.append(f"{emoji.strip()} {text.strip()}")
        else:
            out.append(line)
    if out:
        return out
    # старый формат: через запятую
    parts = [q.strip() for q in qualities_raw.split(",") if q.strip()][:3]
    return [f"• {q}" for q in parts]


def format_user_profile(
    user: User,
    compatibility: Optional[int] = None,
    expanded: bool = False,
    compatibility_explanation: Optional[str] = None,
    lang: str = "ru",
) -> str:
    """
    Форматирование анкеты пользователя для показа.
    lang — язык просматривающего (для подписей карточки).
    """
    from texts.i18n import t

    text_parts = []

    # Иконка по совместимости: 80–100% 🟢, 50–80% 🟡, иначе 🔴
    if compatibility is not None:
        if compatibility >= 80:
            icon = "🟢"
        elif compatibility >= 50:
            icon = "🟡"
        else:
            icon = "🔴"
    else:
        icon = "🔴"

    name_part = user.name or t(lang, "card_no_name")
    years_label = t(lang, "card_years")
    age_part = f"{user.age} {years_label}" if user.age else ""
    if age_part:
        text_parts.append(f"{icon} {name_part} | {age_part}")
    else:
        text_parts.append(f"{icon} {name_part}")

    text_parts.append("")

    if compatibility is not None:
        text_parts.append(f"🔗 {t(lang, 'card_compatibility')}: {compatibility}%")

    qualities_display = _parse_qualities_display(user.qualities, lang)
    if qualities_display:
        heading = t(lang, "card_qualities_heading")
        qualities_text = "\n".join(qualities_display)
        text_parts.append(f"⭐ <b>{heading}:</b>\n{qualities_text}")

    if user.short_description:
        text_parts.append(f"<blockquote>{html.escape(user.short_description)}</blockquote>")
    if expanded:
        display_full = _clean_full_description(user.full_description)
        if display_full:
            text_parts.append("")
            text_parts.append(f"<b>{t(lang, 'card_more')}:</b>")
            text_parts.append(f"<blockquote>{html.escape(display_full)}</blockquote>")

    if expanded and compatibility_explanation:
        text_parts.append("")
        text_parts.append(f"<b>{t(lang, 'card_why_compatibility')}</b>")
        text_parts.append(compatibility_explanation)

    return "\n".join(text_parts)


async def get_next_user_for_swipe(
    session,
    current_user_id: int,
    current_user: User
) -> Optional[tuple[User, int]]:
    """
    Получение следующего пользователя для свайпа с учетом совместимости
    
    Returns:
        Tuple (User, compatibility_score) или None
    """
    # Получаем профиль текущего пользователя
    test_result = await TestResultRepository.get_by_user_id(session, current_user_id)
    if not test_result or not test_result.main_test_completed:
        # Если нет основного теста, показываем всех без сортировки
        return await _get_any_user(session, current_user_id)
    
    # Получаем профиль текущего пользователя
    current_profile = _get_user_profile(test_result)
    if not current_profile:
        return await _get_any_user(session, current_user_id)
    
    # Получаем список уже просмотренных пользователей
    swiped_ids = await SwipeRepository.get_swiped_user_ids(session, current_user_id)
    swiped_ids.append(current_user_id)  # Исключаем себя
    
    # Получаем всех пользователей, которых еще не свайпали (исключаем теневой/полный бан)
    query = select(User).where(
        and_(
            User.telegram_id.notin_(swiped_ids),
            User.is_registered == True,
            User.is_minor == False,
            User.short_description.isnot(None),
            User.full_description.isnot(None),
            User.qualities.isnot(None),
            (User.ban_status.is_(None)) | (User.ban_status == "none"),
        )
    )
    
    result = await session.execute(query)
    all_users = list(result.scalars().all())
    
    if not all_users:
        return None
    
    # Рассчитываем совместимость для каждого пользователя
    users_with_compatibility = []
    
    for user in all_users:
        user_test_result = await TestResultRepository.get_by_user_id(session, user.telegram_id)
        if not user_test_result or not user_test_result.main_test_completed:
            # Если у пользователя нет теста, совместимость = 0
            users_with_compatibility.append((user, 0))
            continue
        
        user_profile = _get_user_profile(user_test_result)
        if not user_profile:
            users_with_compatibility.append((user, 0))
            continue
        
        compatibility = CompatibilityService.calculate_compatibility(
            current_profile,
            user_profile
        )
        users_with_compatibility.append((user, compatibility))
    
    # Сортируем по совместимости (от большего к меньшему)
    users_with_compatibility.sort(key=lambda x: x[1], reverse=True)

    # Возвращаем первого пользователя
    if not users_with_compatibility:
        return None
    winner_user, winner_compatibility = users_with_compatibility[0]
    return (winner_user, winner_compatibility)


async def _get_any_user(session, current_user_id: int) -> Optional[tuple[User, int]]:
    """Получение любого пользователя без учета совместимости"""
    swiped_ids = await SwipeRepository.get_swiped_user_ids(session, current_user_id)
    swiped_ids.append(current_user_id)
    
    query = select(User).where(
        and_(
            User.telegram_id.notin_(swiped_ids),
            User.is_registered == True,
            User.is_minor == False,
            (User.ban_status.is_(None)) | (User.ban_status == "none"),
        )
    ).limit(1)
    
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    return (user, 0) if user else None


def _get_dm_link(user: User) -> str:
    """Ссылка для перехода в ЛС: t.me/username или tg://user?id="""
    if user.username:
        uname = user.username.strip().lstrip("@")
        if uname:
            return f"https://t.me/{uname}"
    return f"tg://user?id={user.telegram_id}"


def _get_user_profile(test_result: TestResult, include_label: bool = False) -> Optional[dict]:
    """Получение профиля пользователя из результатов теста"""
    if not test_result:
        return None
    
    profile = {
        "hustler_percent": test_result.hustler_percent or 0,
        "hacker_percent": test_result.hacker_percent or 0,
        "hipster_percent": test_result.hipster_percent or 0,
        "ethics_score": test_result.ethics_score or 0,
        "goals_score": test_result.goals_score or 0,
        "risk_score": test_result.risk_score or 0,
        "decision_score": test_result.decision_score or 0,
        "comm_score": test_result.comm_score or 0,
    }
    if include_label and test_result.profile_label:
        profile["profile_label"] = test_result.profile_label
    return profile


async def show_next_profile(
    message_or_callback: Message | CallbackQuery,
    user_id: int,
    current_user: User,
    state: Optional[FSMContext] = None,
    in_partners: bool = False,
) -> None:
    """
    Показ следующей анкеты (язык из current_user).
    """
    lang = getattr(current_user, "language", None) or "ru"
    try:
        if isinstance(message_or_callback, CallbackQuery):
            message = message_or_callback.message
            is_callback = True
        else:
            message = message_or_callback
            is_callback = False

        async for session in get_session():
            next_user_data = await get_next_user_for_swipe(session, user_id, current_user)

            if not next_user_data:
                no_users_text = f"{t(lang, 'partners_title')}\n\n{t(lang, 'partners_no_users')}"
                if in_partners and state:
                    await state.update_data(in_partners=False, current_partner_id=None)
                    await message.answer(
                        no_users_text + "\n\n" + t(lang, "choose_menu_item"),
                        reply_markup=get_main_menu_keyboard(current_user.is_minor, lang),
                    )
                else:
                    no_users_kb = InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]])
                    await message.answer(no_users_text, reply_markup=no_users_kb)
                return

            next_user, compatibility = next_user_data
            if in_partners and state:
                await state.update_data(current_partner_id=next_user.telegram_id)

            try:
                tr_viewer = await TestResultRepository.get_by_user_id(session, user_id)
                tr_shown = await TestResultRepository.get_by_user_id(session, next_user.telegram_id)
                pv = _get_user_profile(tr_viewer) if tr_viewer else None
                pl = _get_user_profile(tr_shown) if tr_shown else None
                if pv and pl:
                    log_compatibility_calculation(
                        viewer_telegram_id=user_id,
                        shown_user_telegram_id=next_user.telegram_id,
                        profile_viewer=pv,
                        profile_shown=pl,
                        viewer_name=current_user.name,
                        shown_name=next_user.name,
                    )
                else:
                    log_compatibility_show_minimal(
                        viewer_telegram_id=user_id,
                        shown_user_telegram_id=next_user.telegram_id,
                        compatibility_percent=compatibility,
                        reason="нет полных профилей теста для расчёта",
                    )
            except Exception as e:
                logger.exception("Ошибка записи расчёта совместимости в .txt: %s", e)

            lang = getattr(current_user, "language", None) or "ru"
            has_super_like = getattr(current_user, "subscription_active", False) and not getattr(current_user, "super_like_used", False)
            profile_text = format_user_profile(next_user, compatibility, lang=lang)
            if in_partners:
                swipe_kb = get_swipe_keyboard_expand_only(
                    next_user.telegram_id, expanded=False, from_notification=False, lang=lang
                )
            else:
                swipe_kb = get_swipe_keyboard(next_user.telegram_id, lang=lang, has_super_like=has_super_like)

            if next_user.photo_id:
                await message.answer_photo(
                    photo=next_user.photo_id,
                    caption=profile_text,
                    reply_markup=swipe_kb,
                )
            else:
                await message.answer(
                    profile_text,
                    reply_markup=swipe_kb,
                )
            break
    except Exception as e:
        logger.error(f"Ошибка при показе профиля: {e}", exc_info=True)
        if isinstance(message_or_callback, CallbackQuery):
            _lang = "ru"
            if hasattr(message_or_callback, "from_user") and message_or_callback.from_user:
                async for _s in get_session():
                    u = await UserRepository.get_by_telegram_id(_s, message_or_callback.from_user.id)
                    if u:
                        _lang = getattr(u, "language", None) or "ru"
                    break
            await message_or_callback.answer(t(_lang, "error_try_later"), show_alert=True)


@router.message(F.text.in_(text_options("menu_partners")), _FilterNotInPartners())
@router.callback_query(F.data == "dating")
async def cmd_dating(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Раздел Партнеры (язык ru/en). При переходе удаляем предыдущее меню."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
        try:
            await message.delete()
        except Exception:
            pass
    else:
        message = event
        user_id = event.from_user.id
        try:
            await message.delete()
        except Exception:
            pass
    data = await state.get_data()
    chat_id = message.chat.id
    bot = message.bot
    for mid in (data.get("last_bot_message_id"), data.get("profile_section_message_id")):
        if mid:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
    await state.update_data(profile_section_message_id=None)

    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if not user:
            await message.answer(t("ru", "not_registered_use_start"))
            return

        lang = getattr(user, "language", None) or "ru"
        test_result = await TestResultRepository.get_by_user_id(session, user_id)
        if not test_result or not test_result.main_test_completed:
            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(
                text=t(lang, "partners_btn_take_test"),
                callback_data="start_test:main"
            ))
            builder.add(get_back_button("main_menu", lang))
            builder.adjust(1)
            await message.answer(
                f"{t(lang, 'partners_title')}\n\n{t(lang, 'partners_main_test_required')}",
                reply_markup=builder.as_markup()
            )
            return

        missing_fields = []
        if not user.short_description:
            missing_fields.append(t(lang, "partners_field_short_desc"))
        if not user.full_description:
            missing_fields.append(t(lang, "partners_field_full_desc"))
        if not user.qualities:
            missing_fields.append(t(lang, "partners_field_qualities"))

        if missing_fields:
            fields_text = ", ".join(missing_fields)
            builder = InlineKeyboardBuilder()
            builder.add(get_back_button("main_menu", lang))
            await message.answer(
                f"{t(lang, 'partners_title')}\n\n{t(lang, 'partners_fill_profile').format(fields=fields_text)}",
                reply_markup=builder.as_markup()
            )
            return

        if (user.ban_status or "none") == "full":
            await message.answer(
                t(lang, "partners_access_denied"),
                reply_markup=get_main_menu_keyboard(is_minor=user.is_minor, lang=lang),
            )
            return

        has_super_like = getattr(user, "subscription_active", False) and not getattr(user, "super_like_used", False)
        await state.update_data(in_partners=True)
        await message.answer(
            f"{t(lang, 'partners_title')}\n\n{t(lang, 'partners_intro')}",
            reply_markup=get_partners_reply_keyboard(lang, has_super_like=has_super_like),
        )
        await show_next_profile(message, user_id, user, state=state, in_partners=True)
        break


def _partners_text_to_action(text: str) -> Optional[str]:
    """Сопоставление текста reply-кнопки с действием свайпа."""
    m = {
        PARTNERS_BTN_SUPER_LIKE: "super_like",
        PARTNERS_BTN_LIKE: "like",
        PARTNERS_BTN_BOOKMARK: "bookmark",
        PARTNERS_BTN_DISLIKE: "dislike",
    }
    return m.get(text)


@router.message(
    F.text.in_([PARTNERS_BTN_SUPER_LIKE, PARTNERS_BTN_LIKE, PARTNERS_BTN_BOOKMARK, PARTNERS_BTN_DISLIKE]),
    _FilterInPartners(),
)
async def handle_partners_reply_action(message: Message, state: FSMContext) -> None:
    """
    Обработка нажатий [🤝] [🏷] [👎] в разделе Партнеры.
    Действие применяется к текущей анкете (current_partner_id из state), затем показывается следующая.
    """
    try:
        await message.delete()
    except Exception:
        pass
    data = await state.get_data()
    if not data.get("in_partners") or not data.get("current_partner_id"):
        return
    action = _partners_text_to_action(message.text)
    if not action:
        return
    swiped_user_id = int(data["current_partner_id"])
    swiper_user_id = message.from_user.id if message.from_user else 0

    try:
        async for session in get_session():
            current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
            lang = getattr(current_user, "language", None) or "ru" if current_user else "ru"
            # Супер-лайк: только у подписчика и если ещё не использован
            if action == "super_like":
                if not current_user or not getattr(current_user, "subscription_active", False) or getattr(current_user, "super_like_used", False):
                    await message.answer(t(lang, "limit_likes_week"))
                    if current_user:
                        await show_next_profile(message, swiper_user_id, current_user, state=state, in_partners=True)
                    return
            # Лимиты: 1 лайк в неделю, 5 добавлений в избранное в неделю
            if action == "like":
                count_likes = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "like")
                if count_likes >= 1:
                    await message.answer(t(lang, "limit_likes_week"))
                    await show_next_profile(message, swiper_user_id, current_user, state=state, in_partners=True)
                    return
            elif action == "bookmark":
                count_bookmarks = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "bookmark")
                if count_bookmarks >= 5:
                    await message.answer(t(lang, "limit_bookmarks_week"))
                    await show_next_profile(message, swiper_user_id, current_user, state=state, in_partners=True)
                    return

            await SwipeRepository.create_swipe(session, swiper_user_id, swiped_user_id, action)

            if action == "super_like":
                await UserRepository.update(session, current_user, super_like_used=True)
                swiped_user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                link = _get_dm_link(swiped_user) if swiped_user else f"tg://user?id={swiped_user_id}"
                super_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link)]
                ])
                await message.answer(
                    t(lang, "super_like_message"),
                    reply_markup=super_kb,
                )
                await show_next_profile(message, swiper_user_id, current_user, state=state, in_partners=True)
                break
            if action == "like":
                swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                # Уведомление о лайке не отправляем, если у лайкнувшего теневой или полный бан
                if swiper_user and (swiper_user.ban_status or "none") in ("none",):
                    swiper_name = swiper_user.name or t(lang, "card_user_fallback")
                    swiped_user_obj = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                    notif_lang = (getattr(swiped_user_obj, "language", None) or "ru") if swiped_user_obj else "ru"
                    await _send_like_notification(
                        message.bot, swiped_user_id, swiper_name, swiper_user_id, lang=notif_lang
                    )

                mutual = await SwipeRepository.check_mutual_like(session, swiper_user_id, swiped_user_id)
                if mutual:
                    try:
                        tr_a = await TestResultRepository.get_by_user_id(session, swiper_user_id)
                        tr_b = await TestResultRepository.get_by_user_id(session, swiped_user_id)
                        profile_a = _get_user_profile(tr_a, include_label=True)
                        profile_b = _get_user_profile(tr_b, include_label=True)
                        if profile_a and profile_b:
                            final_score, details = CompatibilityService.calculate_compatibility_detailed(
                                profile_a, profile_b
                            )
                            swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                            name_a = (swiper_user.name or "Пользователь") if swiper_user else "Пользователь"
                            user_b = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                            name_b = (user_b.name or "Пользователь") if user_b else "Пользователь"
                            log_match_comparison(
                                user_a_id=swiper_user_id, user_a_name=name_a,
                                user_b_id=swiped_user_id, user_b_name=name_b,
                                final_score=final_score, details=details,
                            )
                    except Exception as e:
                        logger.error("Ошибка записи сравнения при совпадении (reply): %s", e, exc_info=True)

                    swiped_user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                    swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                    link_to_other = _get_dm_link(swiped_user) if swiped_user else f"tg://user?id={swiped_user_id}"
                    match_kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link_to_other)]
                    ])
                    match_msg = t(lang, "match_title") + "\n\n" + t(lang, "match_message")
                    await message.answer(match_msg, reply_markup=match_kb)
                    link_to_swiper = _get_dm_link(swiper_user) if swiper_user else f"tg://user?id={swiper_user_id}"
                    swiped_user_obj = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                    other_lang = (getattr(swiped_user_obj, "language", None) or "ru") if swiped_user_obj else "ru"
                    match_kb_other = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=t(other_lang, "btn_go_to_dm"), url=link_to_swiper)]
                    ])
                    match_msg_other = t(other_lang, "match_title") + "\n\n" + t(other_lang, "match_message")
                    try:
                        await message.bot.send_message(
                            swiped_user_id,
                            match_msg_other,
                            reply_markup=match_kb_other,
                        )
                    except Exception as e:
                        logger.error("Ошибка отправки уведомления о мэтче (reply): %s", e)

            current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
            if current_user:
                await show_next_profile(message, swiper_user_id, current_user, state=state, in_partners=True)
            break
    except Exception as e:
        logger.error("Ошибка при обработке действия из reply-клавиатуры Партнеры: %s", e, exc_info=True)
        err_lang = "ru"
        async for session in get_session():
            u = await UserRepository.get_by_telegram_id(session, swiper_user_id)
            if u:
                err_lang = getattr(u, "language", None) or "ru"
            break
        await message.answer(t(err_lang, "partners_error_try_again"))


def _is_notification_keyboard(callback_data: str) -> bool:
    """Проверка, что callback из уведомления (notif)."""
    return "expand_profile_notif" in callback_data or "collapse_profile_notif" in callback_data


@router.callback_query(F.data.startswith("expand_profile"))
@router.callback_query(F.data.startswith("collapse_profile"))
async def handle_expand_collapse_profile(callback: CallbackQuery) -> None:
    """
    Развернуть / свернуть описание в карточке анкеты.
    При развороте добавляется полное описание и блок «Почему такая совместимость» красивыми словами.
    """
    await callback.answer()
    try:
        raw = callback.data
        is_expand = raw.startswith("expand_profile:") or raw.startswith("expand_profile_notif:")
        is_notif = _is_notification_keyboard(raw)
        parts = callback.data.split(":")
        if len(parts) != 2:
            return
        swiped_user_id = int(parts[1])
        viewer_id = callback.from_user.id

        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
            if not user:
                viewer = await UserRepository.get_by_telegram_id(session, viewer_id)
                _lang = (getattr(viewer, "language", None) or "ru") if viewer else "ru"
                await callback.answer(t(_lang, "profile_unavailable"), show_alert=True)
                return
            viewer = await UserRepository.get_by_telegram_id(session, viewer_id)
            lang = getattr(viewer, "language", None) or "ru" if viewer else "ru"

            compatibility = None
            compatibility_explanation = None
            if user.telegram_id:
                tr_viewer = await TestResultRepository.get_by_user_id(session, viewer_id)
                tr_shown = await TestResultRepository.get_by_user_id(session, user.telegram_id)
                if tr_viewer and tr_shown and tr_viewer.main_test_completed and tr_shown.main_test_completed:
                    pv = _get_user_profile(tr_viewer, include_label=True)
                    pl = _get_user_profile(tr_shown, include_label=True)
                    if pv and pl:
                        compatibility, details = CompatibilityService.calculate_compatibility_detailed(pv, pl)
                        if is_expand and compatibility is not None:
                            compatibility_explanation = CompatibilityService.get_compatibility_explanation(
                                compatibility, details
                            )

            caption_or_text = format_user_profile(
                user,
                compatibility,
                expanded=is_expand,
                compatibility_explanation=compatibility_explanation,
                lang=lang,
            )
            if is_notif:
                kb = get_swipe_keyboard_from_notification(swiped_user_id, expanded=is_expand, lang=lang)
            else:
                kb = get_swipe_keyboard_expand_only(
                    swiped_user_id, expanded=is_expand, from_notification=False, lang=lang
                )

            msg = callback.message
            if msg.photo:
                await msg.edit_caption(caption=caption_or_text, reply_markup=kb)
            else:
                await msg.edit_text(text=caption_or_text, reply_markup=kb)
            break
    except Exception as e:
        logger.error("Ошибка при развороте/сворачивании анкеты: %s", e, exc_info=True)
        _err_lang = "ru"
        async for _s in get_session():
            _u = await UserRepository.get_by_telegram_id(_s, callback.from_user.id)
            if _u:
                _err_lang = getattr(_u, "language", None) or "ru"
            break
        await callback.answer(t(_err_lang, "edit_quality_emoji_error"), show_alert=True)


@router.callback_query(F.data.startswith("view_liker:"))
async def handle_view_liker(callback: CallbackQuery) -> None:
    """Показать анкету того, кто лайкнул (кнопка «Посмотреть» из уведомления)"""
    await callback.answer()
    try:
        parts = callback.data.split(":")
        if len(parts) != 2:
            return
        liker_id = int(parts[1])
        viewer_id = callback.from_user.id
        async for session in get_session():
            liker = await UserRepository.get_by_telegram_id(session, liker_id)
            viewer = await UserRepository.get_by_telegram_id(session, viewer_id)
            lang = (getattr(viewer, "language", None) or "ru") if viewer else "ru"
            if not liker or not liker.short_description or not liker.full_description or not liker.qualities:
                await callback.message.edit_text(
                    t(lang, "profile_unavailable"),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]]),
                )
                return
            # Совместимость: профиль текущего и лайкнувшего
            compatibility = None
            tr_viewer = await TestResultRepository.get_by_user_id(session, viewer_id)
            tr_liker = await TestResultRepository.get_by_user_id(session, liker_id)
            if tr_viewer and tr_liker and tr_viewer.main_test_completed and tr_liker.main_test_completed:
                pv = _get_user_profile(tr_viewer)
                pl = _get_user_profile(tr_liker)
                if pv and pl:
                    compatibility, _ = CompatibilityService.calculate_compatibility_detailed(pv, pl)
                    log_compatibility_calculation(
                        viewer_telegram_id=viewer_id,
                        shown_user_telegram_id=liker_id,
                        profile_viewer=pv,
                        profile_shown=pl,
                        viewer_name=callback.from_user.full_name,
                        shown_name=liker.name,
                    )
                else:
                    compatibility = 0
                    log_compatibility_show_minimal(
                        viewer_telegram_id=viewer_id,
                        shown_user_telegram_id=liker_id,
                        compatibility_percent=0,
                        reason="нет полных профилей теста (кнопка «Посмотреть»)",
                    )
            else:
                try:
                    log_compatibility_show_minimal(
                        viewer_telegram_id=viewer_id,
                        shown_user_telegram_id=liker_id,
                        compatibility_percent=0,
                        reason="нет полных профилей теста (кнопка «Посмотреть»)",
                    )
                except Exception:
                    pass
            profile_text = format_user_profile(liker, compatibility, lang=lang)
            try:
                await callback.message.delete()
            except Exception:
                pass
            if liker.photo_id:
                await callback.message.answer_photo(
                    photo=liker.photo_id,
                    caption=profile_text,
                    reply_markup=get_swipe_keyboard_from_notification(liker_id, lang=lang),
                )
            else:
                await callback.message.answer(
                    profile_text,
                    reply_markup=get_swipe_keyboard_from_notification(liker_id, lang=lang),
                )
            break
    except Exception as e:
        logger.error("Ошибка при показе анкеты лайкнувшего: %s", e, exc_info=True)
        _err_lang = "ru"
        async for _s in get_session():
            _u = await UserRepository.get_by_telegram_id(_s, callback.from_user.id)
            if _u:
                _err_lang = getattr(_u, "language", None) or "ru"
            break
        await callback.answer(t(_err_lang, "error_try_later"), show_alert=True)


@router.callback_query(F.data.startswith("swipe_notif_"))
async def handle_swipe_from_notification(callback: CallbackQuery) -> None:
    """
    Ответ на анкету из уведомления «Вас лайкнули» → «Посмотреть».
    """
    await callback.answer()
    lang = "ru"
    async for _s in get_session():
        u = await UserRepository.get_by_telegram_id(_s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    try:
        parts = callback.data.split(":")
        if len(parts) != 2:
            return
        action = parts[0].replace("swipe_notif_", "")
        swiped_user_id = int(parts[1])
        swiper_user_id = callback.from_user.id

        async for session in get_session():
            if action == "like":
                count_likes = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "like")
                if count_likes >= 1:
                    await callback.answer(t(lang, "limit_likes_week"), show_alert=True)
                    return
            elif action == "bookmark":
                count_bookmarks = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "bookmark")
                if count_bookmarks >= 5:
                    await callback.answer(t(lang, "limit_bookmarks_week"), show_alert=True)
                    return
            await SwipeRepository.create_swipe(
                session, swiper_user_id, swiped_user_id, action
            )

            if action == "like":
                swiped_user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                mutual = await SwipeRepository.check_mutual_like(
                    session, swiper_user_id, swiped_user_id
                )
                if mutual:
                    # Логирование совпадения
                    try:
                        swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                        tr_a = await TestResultRepository.get_by_user_id(session, swiper_user_id)
                        tr_b = await TestResultRepository.get_by_user_id(session, swiped_user_id)
                        profile_a = _get_user_profile(tr_a, include_label=True)
                        profile_b = _get_user_profile(tr_b, include_label=True)
                        if profile_a and profile_b:
                            final_score, details = CompatibilityService.calculate_compatibility_detailed(
                                profile_a, profile_b
                            )
                            name_a = (swiper_user.name or "Пользователь") if swiper_user else "Пользователь"
                            name_b = (swiped_user.name or "Пользователь") if swiped_user else "Пользователь"
                            log_match_comparison(
                                user_a_id=swiper_user_id, user_a_name=name_a,
                                user_b_id=swiped_user_id, user_b_name=name_b,
                                final_score=final_score, details=details,
                            )
                    except Exception as e:
                        logger.error("Ошибка записи сравнения при совпадении (notif): %s", e, exc_info=True)

                    # Сообщение о мэтче текущему пользователю (анкету не трогаем, только новое сообщение)
                    swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                    link_to_other = _get_dm_link(swiped_user) if swiped_user else f"tg://user?id={swiped_user_id}"
                    match_kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link_to_other)],
                        [get_back_button("main_menu", lang)],
                    ])
                    match_msg = t(lang, "match_title") + "\n\n" + t(lang, "match_message")
                    await callback.message.answer(match_msg, reply_markup=match_kb)
                    link_to_swiper = _get_dm_link(swiper_user) if swiper_user else f"tg://user?id={swiper_user_id}"
                    swiped_user_obj = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                    other_lang = (getattr(swiped_user_obj, "language", None) or "ru") if swiped_user_obj else "ru"
                    match_kb_other = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=t(other_lang, "btn_go_to_dm"), url=link_to_swiper)]
                    ])
                    match_msg_other = t(other_lang, "match_title") + "\n\n" + t(other_lang, "match_message")
                    try:
                        await callback.bot.send_message(
                            swiped_user_id,
                            match_msg_other,
                            reply_markup=match_kb_other,
                        )
                    except Exception as e:
                        logger.error("Ошибка отправки уведомления о мэтче (notif): %s", e)
                else:
                    await callback.message.answer(
                        t(lang, "like_sent_message"),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]]),
                    )
            else:
                await callback.message.answer(
                    t(lang, "swipe_action_done"),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]]),
                )
            break
    except Exception as e:
        logger.error("Ошибка при ответе из уведомления: %s", e, exc_info=True)
        await callback.answer(t(lang, "error_try_later"), show_alert=True)


async def _show_next_favorite_or_empty(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    send_new_message: bool = False,
) -> None:
    """После лайка/дизлайка из избранного: показать следующего из списка или экран «никого не осталось»."""
    from keyboards.menu import get_people_keyboard
    from keyboards.swipe import get_favorites_keyboard

    swiper_user_id = callback.from_user.id
    msg = callback.message
    async for session in get_session():
        new_ids = await SwipeRepository.get_bookmarked_user_ids(session, swiper_user_id)
        await state.update_data(
            favorites_ids=new_ids,
            in_favorites=bool(new_ids),
            favorites_index=0,
            current_partner_id=new_ids[0] if new_ids else None,
        )
        if not new_ids:
            empty_text = t(lang, "people_favorites") + "\n\n" + t(lang, "favorites_empty_all")
            try:
                await msg.delete()
            except Exception:
                pass
            await msg.answer(empty_text, reply_markup=get_people_keyboard(lang), parse_mode="HTML")
            return
        uid = new_ids[0]
        user = await UserRepository.get_by_telegram_id(session, uid)
        if not user:
            await state.update_data(in_favorites=False, favorites_ids=[])
            return
        compatibility = None
        tr_viewer = await TestResultRepository.get_by_user_id(session, swiper_user_id)
        tr_shown = await TestResultRepository.get_by_user_id(session, uid)
        if tr_viewer and tr_shown and tr_viewer.main_test_completed and tr_shown.main_test_completed:
            pv = _get_user_profile(tr_viewer, include_label=True)
            pl = _get_user_profile(tr_shown, include_label=True)
            if pv and pl:
                compatibility, _ = CompatibilityService.calculate_compatibility_detailed(pv, pl)
        profile_text = format_user_profile(user, compatibility, expanded=False, lang=lang)
        total = len(new_ids)
        kb = get_favorites_keyboard(uid, 0, total, expanded=False, lang=lang)
        if send_new_message:
            if user.photo_id:
                sent = await msg.answer_photo(
                    photo=user.photo_id,
                    caption=profile_text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            else:
                sent = await msg.answer(profile_text, reply_markup=kb, parse_mode="HTML")
            await state.update_data(last_bot_message_id=sent.message_id)
        else:
            try:
                if msg.photo and user.photo_id:
                    from aiogram.types import InputMediaPhoto
                    await msg.edit_media(
                        InputMediaPhoto(media=user.photo_id, caption=profile_text, parse_mode="HTML"),
                    )
                    await msg.edit_reply_markup(reply_markup=kb)
                else:
                    await msg.delete()
                    if user.photo_id:
                        sent = await msg.answer_photo(
                            photo=user.photo_id,
                            caption=profile_text,
                            reply_markup=kb,
                            parse_mode="HTML",
                        )
                    else:
                        sent = await msg.answer(profile_text, reply_markup=kb, parse_mode="HTML")
                    await state.update_data(last_bot_message_id=sent.message_id)
            except Exception:
                await msg.delete()
                if user.photo_id:
                    sent = await msg.answer_photo(
                        photo=user.photo_id,
                        caption=profile_text,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                else:
                    sent = await msg.answer(profile_text, reply_markup=kb, parse_mode="HTML")
                await state.update_data(last_bot_message_id=sent.message_id)
        break


@router.callback_query(F.data.startswith("swipe_"))
async def handle_swipe_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка действий свайпа (лайк, дизлайк, пропуск, заметка). При лайке/дизлайке из избранного — убираем из списка и показываем следующего."""
    await callback.answer()
    lang = "ru"
    async for _s in get_session():
        u = await UserRepository.get_by_telegram_id(_s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    try:
        parts = callback.data.split(":")
        if len(parts) != 2:
            return
        action = parts[0].replace("swipe_", "")
        swiped_user_id = int(parts[1])
        swiper_user_id = callback.from_user.id
        data = await state.get_data()
        in_favorites = data.get("in_favorites", False)

        async for session in get_session():
            current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
            lang = getattr(current_user, "language", None) or "ru" if current_user else "ru"
            if action == "super_like":
                if not current_user or not getattr(current_user, "subscription_active", False) or getattr(current_user, "super_like_used", False):
                    await callback.answer(t(lang, "limit_likes_week"), show_alert=True)
                    return
            if action == "like":
                count_likes = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "like")
                if count_likes >= 1:
                    await callback.answer(t(lang, "limit_likes_week"), show_alert=True)
                    return
            elif action == "bookmark":
                count_bookmarks = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "bookmark")
                if count_bookmarks >= 5:
                    await callback.answer(t(lang, "limit_bookmarks_week"), show_alert=True)
                    return

            await SwipeRepository.create_swipe(
                session,
                swiper_user_id,
                swiped_user_id,
                action
            )
            if action == "super_like":
                await UserRepository.update(session, current_user, super_like_used=True)
                swiped_user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                link = _get_dm_link(swiped_user) if swiped_user else f"tg://user?id={swiped_user_id}"
                super_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link)]
                ])
                await callback.message.answer(
                    t(lang, "super_like_message"),
                    reply_markup=super_kb,
                )
                if in_favorites:
                    await _show_next_favorite_or_empty(callback, state, lang, send_new_message=True)
                else:
                    if current_user:
                        await show_next_profile(callback, swiper_user_id, current_user)
                break
            # Если это лайк — уведомление не отправляем при теневом/полном бане лайкнувшего
            if action == "like":
                swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                if swiper_user and (swiper_user.ban_status or "none") in ("none",):
                    swiper_name = swiper_user.name or t(lang, "card_user_fallback")
                    swiped_user_obj = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                    notif_lang = (getattr(swiped_user_obj, "language", None) or "ru") if swiped_user_obj else "ru"
                    await _send_like_notification(
                        callback.bot, swiped_user_id, swiper_name, swiper_user_id, lang=notif_lang
                    )

                # Проверяем совпадение (взаимный лайк) — пишем подробное сравнение в доп. файл
                mutual = await SwipeRepository.check_mutual_like(
                    session, swiper_user_id, swiped_user_id
                )
                if mutual:
                    try:
                        tr_a = await TestResultRepository.get_by_user_id(session, swiper_user_id)
                        tr_b = await TestResultRepository.get_by_user_id(session, swiped_user_id)
                        profile_a = _get_user_profile(tr_a, include_label=True)
                        profile_b = _get_user_profile(tr_b, include_label=True)
                        if profile_a and profile_b:
                            final_score, details = CompatibilityService.calculate_compatibility_detailed(
                                profile_a, profile_b
                            )
                            name_a = (swiper_user.name or "Пользователь") if swiper_user else "Пользователь"
                            user_b = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                            name_b = (user_b.name or "Пользователь") if user_b else "Пользователь"
                            log_match_comparison(
                                user_a_id=swiper_user_id,
                                user_a_name=name_a,
                                user_b_id=swiped_user_id,
                                user_b_name=name_b,
                                final_score=final_score,
                                details=details,
                            )
                    except Exception as e:
                        logger.error("Ошибка записи сравнения при совпадении: %s", e, exc_info=True)

                    # Сообщение о мэтче обоим пользователям и кнопка «Перейти в ЛС»
                    swiped_user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                    try:
                        link_to_other = _get_dm_link(swiped_user) if swiped_user else f"tg://user?id={swiped_user_id}"
                        match_kb_swiper = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link_to_other)]
                        ])
                        match_msg = t(lang, "match_title") + "\n\n" + t(lang, "match_message")
                        await callback.message.edit_text(match_msg, reply_markup=match_kb_swiper)
                    except Exception:
                        try:
                            await callback.message.delete()
                        except Exception:
                            pass
                        await callback.message.answer(
                            t(lang, "match_title") + "\n\n" + t(lang, "match_message"),
                            reply_markup=match_kb_swiper,
                        )
                    try:
                        other_name = swiper_user.name or t(lang, "card_user_fallback")
                        link_to_swiper = _get_dm_link(swiper_user)
                        swiped_user_obj = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                        other_lang = (getattr(swiped_user_obj, "language", None) or "ru") if swiped_user_obj else "ru"
                        match_kb_swiped = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text=t(other_lang, "btn_go_to_dm"), url=link_to_swiper)]
                        ])
                        match_msg_other = t(other_lang, "match_title") + "\n\n" + t(other_lang, "match_message")
                        await callback.bot.send_message(
                            swiped_user_id,
                            match_msg_other,
                            reply_markup=match_kb_swiped,
                        )
                    except Exception as e:
                        logger.error("Ошибка отправки уведомления о мэтче второму пользователю: %s", e)
                    # Показываем следующую анкету в новом сообщении (текущее уже занято мэтчем)
                    if in_favorites:
                        await _show_next_favorite_or_empty(callback, state, lang, send_new_message=True)
                        break
                    current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                    if current_user:
                        async for sess in get_session():
                            next_data = await get_next_user_for_swipe(sess, swiper_user_id, current_user)
                            if next_data:
                                nu, comp = next_data
                                text = format_user_profile(nu, comp, lang=lang)
                                if nu.photo_id:
                                    await callback.message.answer_photo(
                                        photo=nu.photo_id,
                                        caption=text,
                                        reply_markup=get_swipe_keyboard(nu.telegram_id, lang=lang, has_super_like=getattr(current_user, "subscription_active", False) and not getattr(current_user, "super_like_used", False)),
                                    )
                                else:
                                    await callback.message.answer(
                                        text,
                                        reply_markup=get_swipe_keyboard(nu.telegram_id, lang=lang, has_super_like=getattr(current_user, "subscription_active", False) and not getattr(current_user, "super_like_used", False)),
                                    )
                            else:
                                await callback.message.answer(
                                    f"{t(lang, 'partners_title')}\n\n{t(lang, 'partners_no_users')}",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]]),
                                )
                            break
                    break
                # Не мэтч — показываем следующую анкету как обычно
            if action in ("like", "dislike") and in_favorites:
                await _show_next_favorite_or_empty(callback, state, lang, send_new_message=False)
                break
            current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
            if current_user:
                await show_next_profile(callback, swiper_user_id, current_user)
            
            break
            
    except Exception as e:
        logger.error(f"Ошибка при обработке свайпа: {e}", exc_info=True)
        await callback.answer(t(lang, "error_try_later"), show_alert=True)


def register_handlers(dp) -> None:
    """Регистрация обработчиков свайпов"""
    dp.include_router(router)
