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
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.database import get_session
from repositories.user_repository import User, UserRepository
from repositories.test_repository import TestResult, TestResultRepository
from repositories.swipe_repository import SwipeRepository
from services.compatibility_service import CompatibilityService
from services.settings import get_bookmarks_per_week_limit, get_likes_per_week_limit
from middlewares.delete_previous import protect_message
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
from utils.profile_translator import (
    translate_qualities_for_language,
    translate_text_for_language,
)
from utils.telegram_media import send_profile_card
from utils.user_display import format_age_label, get_display_age
from utils.qualities import all_qualities_filled
from keyboards.menu import get_main_menu_keyboard
from services.partners_prerequisites import (
    collect_missing_prerequisites,
    send_partners_prerequisites,
)
from texts.i18n import t, text_options
from texts.messages import FULL_DESCRIPTION_HINT_SNIPPET
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_

router = Router()
logger = logging.getLogger(__name__)


def _remove_expand_controls(reply_markup: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup | None:
    """Удаляет кнопки expand/collapse из inline-клавиатуры, сохраняя остальные."""
    if not reply_markup or not getattr(reply_markup, "inline_keyboard", None):
        return reply_markup

    filtered_rows: list[list[InlineKeyboardButton]] = []
    for row in reply_markup.inline_keyboard:
        filtered_row: list[InlineKeyboardButton] = []
        for btn in row:
            cb = getattr(btn, "callback_data", None) or ""
            if (
                cb.startswith("expand_profile")
                or cb.startswith("collapse_profile")
                or cb.startswith("adm_expand_profile")
                or cb.startswith("adm_collapse_profile")
                or cb.startswith("expand_favorites")
                or cb.startswith("collapse_favorites")
            ):
                continue
            filtered_row.append(btn)
        if filtered_row:
            filtered_rows.append(filtered_row)

    if not filtered_rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=filtered_rows)


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
    («Максимум 500 символов», «Расскажи подробнее о себе»), считаем описание пустым.
    """
    if not raw or not raw.strip():
        return ""
    text = raw.strip()
    # Если это явно подсказка (или пользователь вставил её в начало) — не показываем
    if FULL_DESCRIPTION_HINT_SNIPPET in text and "Расскажи подробнее о себе" in text:
        return ""
    # Удаляем только вставленные фразы подсказки, оставляя остальной текст
    for phrase in (
        "Максимум 500 символов.",
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
    short_description_override: Optional[str] = None,
    full_description_override: Optional[str] = None,
    qualities_override: Optional[str] = None,
    show_translation_note: bool = False,
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
    display_age = get_display_age(user)
    age_part = format_age_label(display_age, lang) if display_age is not None else ""
    if age_part:
        text_parts.append(f"{icon} {name_part} | {age_part}")
    else:
        text_parts.append(f"{icon} {name_part}")
    city_part = (getattr(user, "city", None) or "").strip()
    if city_part:
        text_parts.append(f"🏙 <b>{t(lang, 'card_city')}:</b> {html.escape(city_part)}")

    text_parts.append("")

    if compatibility is not None:
        text_parts.append(f"🔗 {t(lang, 'card_compatibility')}: {compatibility}%")
        text_parts.append("")

    qualities_raw = qualities_override if qualities_override is not None else user.qualities
    short_description = (
        short_description_override if short_description_override is not None else user.short_description
    )
    full_description_raw = (
        full_description_override if full_description_override is not None else user.full_description
    )

    qualities_display = _parse_qualities_display(qualities_raw, lang)
    if qualities_display:
        heading = t(lang, "card_qualities_heading")
        qualities_text = "\n".join(qualities_display)
        text_parts.append(f"⭐ <b>{heading}:</b>")
        text_parts.append(qualities_text)

    if short_description:
        text_parts.append(f"<blockquote>{html.escape(short_description)}</blockquote>")
    if expanded:
        display_full = _clean_full_description(full_description_raw)
        if display_full:
            text_parts.append("")
            text_parts.append(f"<b>{t(lang, 'card_more')}:</b>")
            text_parts.append(f"<blockquote>{html.escape(display_full)}</blockquote>")

    if expanded and compatibility_explanation:
        text_parts.append("")
        text_parts.append(f"<b>{t(lang, 'card_why_compatibility')}</b>")
        text_parts.append(compatibility_explanation)

    if show_translation_note:
        author_lang = getattr(user, "language", None) or "ru"
        if author_lang != lang:
            lang_name = t(lang, f"lang_name_{author_lang}")
            text_parts.append("")
            text_parts.append(f"<i>{t(lang, 'profile_translated_note').format(lang_name=lang_name)}</i>")

    return "\n".join(text_parts)


def _needs_translation(user: User, viewer_lang: str) -> bool:
    author_lang = getattr(user, "language", None) or "ru"
    return author_lang != viewer_lang


async def build_translated_profile_text(
    user: User,
    viewer_lang: str,
    compatibility: Optional[int] = None,
    expanded: bool = False,
    compatibility_explanation: Optional[str] = None,
) -> str:
    """Перевод полей анкеты под язык просмотра и сборка текста карточки."""
    if _needs_translation(user, viewer_lang):
        translated_short = await translate_text_for_language(user.short_description, viewer_lang)
        translated_full = await translate_text_for_language(user.full_description, viewer_lang)
        translated_qualities = await translate_qualities_for_language(user.qualities, viewer_lang)
        return format_user_profile(
            user,
            compatibility,
            expanded=expanded,
            compatibility_explanation=compatibility_explanation,
            lang=viewer_lang,
            short_description_override=translated_short,
            full_description_override=translated_full,
            qualities_override=translated_qualities,
            show_translation_note=True,
        )
    return format_user_profile(
        user,
        compatibility,
        expanded=expanded,
        compatibility_explanation=compatibility_explanation,
        lang=viewer_lang,
    )


# Максимум кандидатов для расчёта совместимости (устраняет N+1 и тяжёлые запросы при 400+ пользователях)
SWIPE_CANDIDATES_LIMIT = 80
PREMIUM_LIMIT_MULTIPLIER = 2  # "всё х2" для подписчиков


async def get_next_user_for_swipe(
    session,
    current_user_id: int,
    current_user: User,
    last_shown_id: Optional[int] = None,
) -> Optional[tuple[User, int]]:
    """
    Следующая анкета для ленты.
    1) ещё не свайпнутые;
    2) повтор: все, кроме лайков и избранного (дизлайк/пропуск снова в ленте);
    3) повтор: все, кроме избранного (полный круг).
  На каждом шаге не показываем подряд ту же анкету, если есть другие кандидаты.
    """
    exclusion_rounds: list[Optional[tuple[str, ...]]] = [
        None,
        ("like", "bookmark"),
        ("bookmark",),
    ]
    for round_actions in exclusion_rounds:
        if round_actions is None:
            excluded_ids = None
        else:
            excluded_ids = await SwipeRepository.get_swiped_user_ids_with_actions(
                session, current_user_id, round_actions
            )
        result = await _get_next_user_with_excluded(
            session,
            current_user_id,
            current_user,
            excluded_ids=excluded_ids,
            skip_user_id=last_shown_id,
        )
        if result is not None:
            return result
    return None


async def _get_likes_left_text(
    session: AsyncSession,
    user_id: int,
    lang: str,
    is_premium: bool = False,
) -> str:
    """
    Текст про оставшиеся лайки на неделю для пользователя.
    Учитывает глобальный лимит и количество лайков за последние 7 дней.
    """
    base_limit = get_likes_per_week_limit()
    limit = base_limit * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
    if limit <= 0:
        return t(lang, "likes_unlimited_info")
    count_likes = await SwipeRepository.count_in_last_7_days(session, user_id, "like")
    remaining = max(0, limit - count_likes)
    if remaining > 0:
        return t(lang, "likes_left_info", remaining=remaining, limit=limit)
    return t(lang, "likes_no_left_info", limit=limit)


def _pick_from_ranked_candidates(
    ranked: list[tuple[User, int]],
    skip_user_id: Optional[int],
) -> Optional[tuple[User, int]]:
    """Берёт лучшего по совместимости, но не ту же анкету подряд, если есть альтернатива."""
    if not ranked:
        return None
    if skip_user_id is not None and len(ranked) > 1:
        for user, score in ranked:
            if user.telegram_id != skip_user_id:
                return (user, score)
    return ranked[0]


async def _get_next_user_with_excluded(
    session,
    current_user_id: int,
    current_user: User,
    excluded_ids: Optional[list] = None,
    skip_user_id: Optional[int] = None,
) -> Optional[tuple[User, int]]:
    """Следующий пользователь для свайпа, исключая только переданные id (если None — все, на кого уже свайпнули)."""
    test_result = await TestResultRepository.get_by_user_id(session, current_user_id)
    if not test_result or not test_result.main_test_completed:
        return await _get_any_user(
            session, current_user_id, excluded_ids=excluded_ids, skip_user_id=skip_user_id
        )

    current_profile = _get_user_profile(test_result)
    if not current_profile:
        return await _get_any_user(
            session, current_user_id, excluded_ids=excluded_ids, skip_user_id=skip_user_id
        )

    if excluded_ids is None:
        swiped_ids = await SwipeRepository.get_swiped_user_ids(session, current_user_id)
    else:
        swiped_ids = list(excluded_ids)
    swiped_ids.append(current_user_id)

    query = (
        select(User)
        .where(
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
        .limit(SWIPE_CANDIDATES_LIMIT)
    )
    result = await session.execute(query)
    all_users = list(result.scalars().all())

    if not all_users:
        return None

    candidate_ids = [u.telegram_id for u in all_users]
    test_results_map = await TestResultRepository.get_by_user_ids(session, candidate_ids)

    users_with_compatibility = []
    for user in all_users:
        user_tr = test_results_map.get(user.telegram_id)
        if not user_tr:
            users_with_compatibility.append((user, 0))
            continue
        user_profile = _get_user_profile(user_tr)
        if not user_profile:
            users_with_compatibility.append((user, 0))
            continue
        compatibility = CompatibilityService.calculate_compatibility(
            current_profile, user_profile
        )
        users_with_compatibility.append((user, compatibility))

    users_with_compatibility.sort(key=lambda x: x[1], reverse=True)
    return _pick_from_ranked_candidates(users_with_compatibility, skip_user_id)


async def _get_any_user(
    session,
    current_user_id: int,
    excluded_ids: Optional[list] = None,
    skip_user_id: Optional[int] = None,
) -> Optional[tuple[User, int]]:
    """Получение любого пользователя без учета совместимости. excluded_ids: если None — исключаем всех, на кого уже свайпнули."""
    if excluded_ids is None:
        swiped_ids = await SwipeRepository.get_swiped_user_ids(session, current_user_id)
    else:
        swiped_ids = list(excluded_ids)
    swiped_ids.append(current_user_id)

    query = (
        select(User)
        .where(
            and_(
                User.telegram_id.notin_(swiped_ids),
                User.is_registered == True,
                User.is_minor == False,
                (User.ban_status.is_(None)) | (User.ban_status == "none"),
            )
        )
        .limit(SWIPE_CANDIDATES_LIMIT)
    )

    result = await session.execute(query)
    candidates = list(result.scalars().all())
    if not candidates:
        return None
    if skip_user_id is not None and len(candidates) > 1:
        for user in candidates:
            if user.telegram_id != skip_user_id:
                return (user, 0)
    return (candidates[0], 0)


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
    session: AsyncSession,
    message_or_callback: Message | CallbackQuery,
    user_id: int,
    current_user: User,
    state: Optional[FSMContext] = None,
    in_partners: bool = False,
) -> None:
    """Показ следующей анкеты (язык из current_user). Текущую карточку не удаляем — остаётся с выбранным действием."""
    lang = getattr(current_user, "language", None) or "ru"
    try:
        if isinstance(message_or_callback, CallbackQuery):
            message = message_or_callback.message
            is_callback = True
        else:
            message = message_or_callback
            is_callback = False

        chat_id = message.chat.id if message.chat else None
        if chat_id:
            if is_callback:
                protect_message(chat_id, message.message_id)
            elif state:
                data = await state.get_data()
                keep_id = data.get("last_bot_message_id")
                if keep_id:
                    protect_message(chat_id, keep_id)

        last_shown_id = None
        if state:
            last_shown_id = (await state.get_data()).get("current_partner_id")
        next_user_data = await get_next_user_for_swipe(
            session, user_id, current_user, last_shown_id=last_shown_id
        )

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
        profile_text = await build_translated_profile_text(next_user, lang, compatibility)
        if in_partners:
            swipe_kb = get_swipe_keyboard_expand_only(
                next_user.telegram_id, expanded=False, from_notification=False, lang=lang
            )
        else:
            swipe_kb = get_swipe_keyboard(next_user.telegram_id, lang=lang, has_super_like=has_super_like)

        sent = await send_profile_card(
            message,
            photo_id=next_user.photo_id,
            text=profile_text,
            reply_markup=swipe_kb,
        )
        if state and in_partners and sent:
            await state.update_data(last_bot_message_id=sent.message_id)
    except Exception as e:
        logger.error(f"Ошибка при показе профиля: {e}", exc_info=True)
        if isinstance(message_or_callback, CallbackQuery):
            _lang = "ru"
            if hasattr(message_or_callback, "from_user") and message_or_callback.from_user:
                try:
                    u = await UserRepository.get_by_telegram_id(session, message_or_callback.from_user.id)
                    if u:
                        _lang = getattr(u, "language", None) or "ru"
                except Exception:
                    pass
            await message_or_callback.answer(t(_lang, "error_try_later"), show_alert=True)


@router.message(F.text.in_(text_options("menu_partners")), _FilterNotInPartners())
@router.callback_query(F.data == "dating")
async def cmd_dating(
    event: Message | CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
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

    user = await UserRepository.get_by_telegram_id(session, user_id)
    if not user:
        await message.answer(t("ru", "not_registered_use_start"))
        return

    lang = getattr(user, "language", None) or "ru"
    test_result = await TestResultRepository.get_by_user_id(session, user_id)
    missing = collect_missing_prerequisites(user, test_result)
    if missing:
        await send_partners_prerequisites(
            message, state, user, test_result, section_title_key="partners_title"
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

    likes_text = await _get_likes_left_text(session, user_id, lang, is_premium=bool(getattr(user, "subscription_active", False)))
    await message.answer(
        f"{t(lang, 'partners_title')}\n\n{t(lang, 'partners_intro')}\n\n{likes_text}",
        reply_markup=get_partners_reply_keyboard(lang, has_super_like=has_super_like),
    )
    await show_next_profile(session, message, user_id, user, state=state, in_partners=True)


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
async def handle_partners_reply_action(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """
    Обработка нажатий [🤝] [🌟] [👎] в разделе Партнеры.
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
        current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
        lang = getattr(current_user, "language", None) or "ru" if current_user else "ru"
        is_premium = bool(getattr(current_user, "subscription_active", False))
        if action == "super_like":
            if not current_user or not getattr(current_user, "subscription_active", False) or getattr(current_user, "super_like_used", False):
                base_limit = get_likes_per_week_limit()
                limit = base_limit * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
                await message.answer(t(lang, "limit_likes_week", limit=limit))
                if current_user:
                    await show_next_profile(session, message, swiper_user_id, current_user, state=state, in_partners=True)
                return
        if action == "like":
            limit = get_likes_per_week_limit() * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
            count_likes = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "like")
            if limit > 0 and count_likes >= limit:
                await message.answer(t(lang, "limit_likes_week", limit=limit))
                await show_next_profile(session, message, swiper_user_id, current_user, state=state, in_partners=True)
                return
        elif action == "bookmark":
            favorites_limit = get_bookmarks_per_week_limit() * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
            favorites_ids = await SwipeRepository.get_bookmarked_user_ids(session, swiper_user_id)
            already_bookmarked = swiped_user_id in favorites_ids
            if favorites_limit > 0 and (not already_bookmarked) and len(favorites_ids) >= favorites_limit:
                await message.answer(t(lang, "limit_favorites_total", limit=favorites_limit))
                await show_next_profile(session, message, swiper_user_id, current_user, state=state, in_partners=True)
                return

        await SwipeRepository.create_swipe(session, swiper_user_id, swiped_user_id, action)

        if action == "super_like":
            await UserRepository.update(session, current_user, super_like_used=True)
            swiped_user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
            link = _get_dm_link(swiped_user) if swiped_user else f"tg://user?id={swiped_user_id}"
            super_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link)],
                [get_back_button("main_menu", lang)],
            ])
            await message.answer(
                t(lang, "super_like_message"),
                reply_markup=super_kb,
            )
            await show_next_profile(session, message, swiper_user_id, current_user, state=state, in_partners=True)
            return
        if action == "like":
            swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
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
                    [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link_to_other)],
                    [get_back_button("main_menu", lang)],
                ])
                match_msg = t(lang, "match_title") + "\n\n" + t(lang, "match_message")
                await message.answer(match_msg, reply_markup=match_kb)
                link_to_swiper = _get_dm_link(swiper_user) if swiper_user else f"tg://user?id={swiper_user_id}"
                swiped_user_obj = await UserRepository.get_by_telegram_id(session, swiped_user_id)
                other_lang = (getattr(swiped_user_obj, "language", None) or "ru") if swiped_user_obj else "ru"
                match_kb_other = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=t(other_lang, "btn_go_to_dm"), url=link_to_swiper)],
                    [get_back_button("main_menu", other_lang)],
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

        # Показать информацию об оставшихся лайках после успешного лайка
        if action == "like":
            likes_text = await _get_likes_left_text(session, swiper_user_id, lang, is_premium=is_premium)
            await message.answer(likes_text)

        current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
        if current_user:
            await show_next_profile(session, message, swiper_user_id, current_user, state=state, in_partners=True)
    except Exception as e:
        logger.error("Ошибка при обработке действия из reply-клавиатуры Партнеры: %s", e, exc_info=True)
        err_lang = "ru"
        try:
            u = await UserRepository.get_by_telegram_id(session, swiper_user_id)
            if u:
                err_lang = getattr(u, "language", None) or "ru"
        except Exception:
            pass
        await message.answer(t(err_lang, "partners_error_try_again"))


@router.callback_query(F.data.startswith("expand_profile"))
@router.callback_query(F.data.startswith("collapse_profile"))
@router.callback_query(F.data.startswith("adm_expand_profile"))
@router.callback_query(F.data.startswith("adm_collapse_profile"))
async def handle_expand_collapse_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показать дополнительный блок по кнопке «Подробнее».
    При нажатии «Подробнее» отправляется отдельное сообщение ниже карточки
    с полным описанием и блоком «Почему такая совместимость».
    """
    await callback.answer()
    try:
        raw = callback.data or ""
        is_expand = (
            raw.startswith("expand_profile:")
            or raw.startswith("expand_profile_notif:")
            or raw.startswith("adm_expand_profile:")
        )
        if not is_expand:
            return
        if raw.startswith("adm_expand_profile:"):
            from config import Config

            if callback.from_user.id not in Config().ADMIN_IDS:
                await callback.answer(t("ru", "error_try_later"), show_alert=True)
                return
            swiped_user_id = int(raw.split(":", 1)[1])
        else:
            parts = raw.split(":")
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
                                compatibility, details, lang=lang
                            )

            details_parts: list[str] = []
            translated_full = await translate_text_for_language(user.full_description, lang)
            display_full = _clean_full_description(translated_full)
            if display_full:
                details_parts.append(f"<b>{t(lang, 'card_more')}:</b>")
                details_parts.append(f"<blockquote>{html.escape(display_full)}</blockquote>")

            if compatibility_explanation:
                details_parts.append(f"<b>{t(lang, 'card_why_compatibility')}</b>")
                details_parts.append(compatibility_explanation)

            cleaned_markup = _remove_expand_controls(callback.message.reply_markup)
            try:
                await callback.message.edit_reply_markup(reply_markup=cleaned_markup)
            except Exception:
                pass

            if details_parts:
                detail_msg = await callback.message.answer("\n\n".join(details_parts))
                if raw.startswith("adm_expand_profile:"):
                    data = await state.get_data()
                    profile_ids = list(data.get("admin_profile_message_ids") or [])
                    profile_ids.append(detail_msg.message_id)
                    await state.update_data(admin_profile_message_ids=profile_ids)
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


@router.callback_query(F.data.startswith("expand_favorites:"))
@router.callback_query(F.data.startswith("collapse_favorites:"))
async def handle_expand_collapse_favorites(callback: CallbackQuery) -> None:
    """Показать дополнительный блок по кнопке «Подробнее» в избранном."""
    await callback.answer()
    try:
        raw = callback.data or ""
        is_expand = raw.startswith("expand_favorites:")
        if not is_expand:
            return

        parts = raw.split(":")
        if len(parts) != 3:
            return
        swiped_user_id = int(parts[1])
        viewer_id = callback.from_user.id

        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
            viewer = await UserRepository.get_by_telegram_id(session, viewer_id)
            lang = (getattr(viewer, "language", None) or "ru") if viewer else "ru"
            if not user:
                await callback.answer(t(lang, "profile_unavailable"), show_alert=True)
                return

            compatibility = None
            compatibility_explanation = None
            tr_viewer = await TestResultRepository.get_by_user_id(session, viewer_id)
            tr_shown = await TestResultRepository.get_by_user_id(session, swiped_user_id)
            if tr_viewer and tr_shown and tr_viewer.main_test_completed and tr_shown.main_test_completed:
                pv = _get_user_profile(tr_viewer, include_label=True)
                pl = _get_user_profile(tr_shown, include_label=True)
                if pv and pl:
                    compatibility, details = CompatibilityService.calculate_compatibility_detailed(pv, pl)
                    if compatibility is not None:
                        compatibility_explanation = CompatibilityService.get_compatibility_explanation(
                            compatibility, details, lang=lang
                        )

            details_parts: list[str] = []
            translated_full = await translate_text_for_language(user.full_description, lang)
            display_full = _clean_full_description(translated_full)
            if display_full:
                details_parts.append(f"<b>{t(lang, 'card_more')}:</b>")
                details_parts.append(f"<blockquote>{html.escape(display_full)}</blockquote>")

            if compatibility_explanation:
                details_parts.append(f"<b>{t(lang, 'card_why_compatibility')}</b>")
                details_parts.append(compatibility_explanation)

            cleaned_markup = _remove_expand_controls(callback.message.reply_markup)
            try:
                await callback.message.edit_reply_markup(reply_markup=cleaned_markup)
            except Exception:
                pass

            if details_parts:
                await callback.message.answer("\n\n".join(details_parts))
            break
    except Exception as e:
        logger.error("Ошибка при развороте карточки в избранном: %s", e, exc_info=True)
        _err_lang = "ru"
        async for _s in get_session():
            _u = await UserRepository.get_by_telegram_id(_s, callback.from_user.id)
            if _u:
                _err_lang = getattr(_u, "language", None) or "ru"
            break
        await callback.answer(t(_err_lang, "error_try_later"), show_alert=True)


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
            if (
                not liker
                or not liker.short_description
                or not liker.full_description
                or not all_qualities_filled(liker.qualities)
            ):
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
            profile_text = await build_translated_profile_text(liker, lang, compatibility)
            try:
                await callback.message.delete()
            except Exception:
                pass
            await send_profile_card(
                callback.message,
                photo_id=liker.photo_id,
                text=profile_text,
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
    is_premium = False
    async for _s in get_session():
        u = await UserRepository.get_by_telegram_id(_s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
            is_premium = bool(getattr(u, "subscription_active", False))
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
                limit = get_likes_per_week_limit() * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
                count_likes = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "like")
                if limit > 0 and count_likes >= limit:
                    await callback.answer(t(lang, "limit_likes_week", limit=limit), show_alert=True)
                    return
            elif action == "bookmark":
                favorites_limit = get_bookmarks_per_week_limit() * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
                favorites_ids = await SwipeRepository.get_bookmarked_user_ids(session, swiper_user_id)
                already_bookmarked = swiped_user_id in favorites_ids
                if favorites_limit > 0 and (not already_bookmarked) and len(favorites_ids) >= favorites_limit:
                    await callback.answer(t(lang, "limit_favorites_total", limit=favorites_limit), show_alert=True)
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
                        [InlineKeyboardButton(text=t(other_lang, "btn_go_to_dm"), url=link_to_swiper)],
                        [get_back_button("main_menu", other_lang)],
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
                    likes_text = await _get_likes_left_text(session, swiper_user_id, lang, is_premium=is_premium)
                    await callback.message.answer(likes_text)
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
        profile_text = await build_translated_profile_text(
            user, lang, compatibility, expanded=False
        )
        total = len(new_ids)
        kb = get_favorites_keyboard(uid, 0, total, expanded=False, lang=lang)
        if send_new_message:
            protect_message(msg.chat.id, msg.message_id)
            sent = await send_profile_card(
                msg,
                photo_id=user.photo_id,
                text=profile_text,
                reply_markup=kb,
            )
            await state.update_data(last_bot_message_id=sent.message_id)
        else:
            edited = False
            if msg.photo and user.photo_id:
                try:
                    from aiogram.types import InputMediaPhoto
                    await msg.edit_media(
                        InputMediaPhoto(media=user.photo_id, caption=profile_text, parse_mode="HTML"),
                    )
                    await msg.edit_reply_markup(reply_markup=kb)
                    edited = True
                except Exception:
                    edited = False
            if not edited:
                try:
                    await msg.delete()
                except Exception:
                    pass
                sent = await send_profile_card(
                    msg,
                    photo_id=user.photo_id,
                    text=profile_text,
                    reply_markup=kb,
                )
                await state.update_data(last_bot_message_id=sent.message_id)
        break


@router.callback_query(F.data.startswith("swipe_"))
async def handle_swipe_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка действий свайпа (лайк, дизлайк, пропуск, заметка). При лайке/дизлайке из избранного — убираем из списка и показываем следующего."""
    lang = "ru"
    async for _s in get_session():
        u = await UserRepository.get_by_telegram_id(_s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    try:
        parts = callback.data.split(":")
        if len(parts) != 2:
            await callback.answer()
            return
        action = parts[0].replace("swipe_", "")
        swiped_user_id = int(parts[1])
        swiper_user_id = callback.from_user.id
        data = await state.get_data()
        in_favorites = data.get("in_favorites", False)

        async for session in get_session():
            current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
            lang = getattr(current_user, "language", None) or "ru" if current_user else "ru"
            is_premium = bool(getattr(current_user, "subscription_active", False))
            if action == "super_like":
                if not current_user or not getattr(current_user, "subscription_active", False) or getattr(current_user, "super_like_used", False):
                    base_limit = get_likes_per_week_limit()
                    limit = base_limit * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
                    await callback.answer(t(lang, "limit_likes_week", limit=limit), show_alert=True)
                    return
            if action == "like":
                limit = get_likes_per_week_limit() * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
                count_likes = await SwipeRepository.count_in_last_7_days(session, swiper_user_id, "like")
                if limit > 0 and count_likes >= limit:
                    await callback.answer(t(lang, "limit_likes_week", limit=limit), show_alert=True)
                    return
            elif action == "bookmark":
                favorites_limit = get_bookmarks_per_week_limit() * (PREMIUM_LIMIT_MULTIPLIER if is_premium else 1)
                favorites_ids = await SwipeRepository.get_bookmarked_user_ids(session, swiper_user_id)
                already_bookmarked = swiped_user_id in favorites_ids
                if favorites_limit > 0 and (not already_bookmarked) and len(favorites_ids) >= favorites_limit:
                    await callback.answer(t(lang, "limit_favorites_total", limit=favorites_limit), show_alert=True)
                    return

            await callback.answer()
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
                    [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link)],
                    [get_back_button("main_menu", lang)],
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
                            [InlineKeyboardButton(text=t(lang, "btn_go_to_dm"), url=link_to_other)],
                            [get_back_button("main_menu", lang)],
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
                    protect_message(callback.message.chat.id, callback.message.message_id)
                    current_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                    if current_user:
                        async for sess in get_session():
                            next_data = await get_next_user_for_swipe(
                                sess, swiper_user_id, current_user, last_shown_id=swiped_user_id
                            )
                            if next_data:
                                nu, comp = next_data
                                text = await build_translated_profile_text(nu, lang, comp)
                                await send_profile_card(
                                    callback.message,
                                    photo_id=nu.photo_id,
                                    text=text,
                                    reply_markup=get_swipe_keyboard(
                                        nu.telegram_id,
                                        lang=lang,
                                        has_super_like=getattr(current_user, "subscription_active", False)
                                        and not getattr(current_user, "super_like_used", False),
                                    ),
                                )
                            else:
                                await callback.message.answer(
                                    f"{t(lang, 'partners_title')}\n\n{t(lang, 'partners_no_users')}",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]]),
                                )
                            break
                    break
                # Не мэтч — показываем следующую анкету как обычно
            if action == "like":
                likes_text = await _get_likes_left_text(session, swiper_user_id, lang, is_premium=is_premium)
                await callback.message.answer(likes_text)
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
