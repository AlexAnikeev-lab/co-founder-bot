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
)
from utils.match_logger import log_match_comparison
from utils.compatibility_logger import log_compatibility_calculation, log_compatibility_show_minimal
from keyboards.menu import get_main_menu_keyboard
from keyboards.common import get_back_button
from texts.i18n import t, text_options
from texts.messages import (
    PARTNERS_MAIN_TEST_REQUIRED,
    FULL_DESCRIPTION_HINT_SNIPPET,
    CARD_EXPAND_BTN,
    CARD_COLLAPSE_BTN,
)
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_

router = Router()
logger = logging.getLogger(__name__)

# Текст уведомления «вас лайкнули»
LIKE_NOTIFICATION_TEXT = (
    "🤝 <b>Кто-то проявил интерес</b>\n\n"
    "{swiper_name} отметил(а) вашу анкету.\n\n"
    "Нажмите «Посмотреть», чтобы открыть анкету и ответить."
)


async def _send_like_notification(
    bot: Bot,
    chat_id: int,
    swiper_name: str,
    swiper_user_id: int,
) -> bool:
    """
    Отправить уведомление «вас лайкнули» в чат chat_id.
    chat_id — telegram_id пользователя, которому отправляем (тот, кого лайкнули).
    Возвращает True при успехе. При ошибке логирует и возвращает False.
    """
    try:
        view_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Посмотреть", callback_data=f"view_liker:{swiper_user_id}")]
        ])
        await bot.send_message(
            chat_id=chat_id,
            text=LIKE_NOTIFICATION_TEXT.format(swiper_name=swiper_name),
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


def format_user_profile(
    user: User,
    compatibility: Optional[int] = None,
    expanded: bool = False,
    compatibility_explanation: Optional[str] = None,
) -> str:
    """
    Форматирование анкеты пользователя для показа.

    Формат:
    👤 [Имя] | [Возраст] лет
    (пустая строка)
    💚 Совместимость: X%
    ⭐ Главные качества: ...
    Описание (превью или полностью при expanded=True)
    При expanded и compatibility_explanation — блок «Почему такая совместимость».
    """
    from texts.messages import CARD_WHY_COMPATIBILITY_HEADING

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

    # Строка 1: [icon] Имя | Возраст лет
    name_part = user.name or "Без имени"
    age_part = f"{user.age} лет" if user.age else ""
    if age_part:
        text_parts.append(f"{icon} {name_part} | {age_part}")
    else:
        text_parts.append(f"{icon} {name_part}")

    text_parts.append("")  # Пустая строка

    # Совместимость
    if compatibility is not None:
        text_parts.append(f"🔗 Совместимость: {compatibility}%")

    # Главные качества
    if user.qualities:
        qualities_list = [q.strip() for q in user.qualities.split(",") if q.strip()]
        if qualities_list:
            qualities_text = "\n".join([f"• {q}" for q in qualities_list[:3]])
            text_parts.append(f"⭐ <b>Главные качества:</b>\n{qualities_text}")

    # Описание: в карточке всегда краткое; при развороте добавляем полное (цитата Telegram)
    if user.short_description:
        text_parts.append(f"<blockquote>{html.escape(user.short_description)}</blockquote>")
    if expanded:
        display_full = _clean_full_description(user.full_description)
        if display_full:
            text_parts.append("")
            text_parts.append("<b>Подробнее:</b>")
            text_parts.append(f"<blockquote>{html.escape(display_full)}</blockquote>")

    # При развороте — пояснение совместимости по результатам тестов
    if expanded and compatibility_explanation:
        text_parts.append("")
        text_parts.append(f"<b>{CARD_WHY_COMPATIBILITY_HEADING}</b>")
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
                no_users_text = (
                    "🤝 <b>Поиск партнеров</b>\n\n"
                    "Вы просмотрели всех доступных пользователей.\n"
                    "Попробуйте позже, когда появятся новые анкеты!"
                )
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

            profile_text = format_user_profile(next_user, compatibility)
            if in_partners:
                swipe_kb = get_swipe_keyboard_expand_only(next_user.telegram_id, expanded=False, from_notification=False)
            else:
                swipe_kb = get_swipe_keyboard(next_user.telegram_id)

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
            await message_or_callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.message(F.text.in_(text_options("menu_partners")), _FilterNotInPartners())
@router.callback_query(F.data == "dating")
async def cmd_dating(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Раздел Партнеры (язык ru/en)."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id
        try:
            await message.delete()
        except Exception:
            pass

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
                text="📋 Пройти тест",
                callback_data="start_test:main"
            ))
            builder.add(get_back_button("main_menu", lang))
            builder.adjust(1)
            await message.answer(
                PARTNERS_MAIN_TEST_REQUIRED,
                reply_markup=builder.as_markup()
            )
            return

        missing_fields = []
        if not user.short_description:
            missing_fields.append("краткое описание")
        if not user.full_description:
            missing_fields.append("полное описание")
        if not user.qualities:
            missing_fields.append("3 главных качества")

        if missing_fields:
            fields_text = ", ".join(missing_fields)
            builder = InlineKeyboardBuilder()
            builder.add(get_back_button("main_menu", lang))
            await message.answer(
                f"🤝 <b>Поиск партнеров</b>\n\n"
                f"Для использования раздела необходимо заполнить:\n"
                f"• {fields_text}\n\n"
                f"Перейдите в профиль и заполните недостающие данные.",
                reply_markup=builder.as_markup()
            )
            return

        if (user.ban_status or "none") == "full":
            await message.answer(
                "⛔ <b>Доступ ограничен</b>\n\nОбратитесь в поддержку.",
                reply_markup=get_main_menu_keyboard(is_minor=user.is_minor, lang=lang),
            )
            return

        await state.update_data(in_partners=True)
        await message.answer(
            "🤝 <b>Партнеры</b>\n\nИспользуйте кнопки ниже для действий с анкетой.",
            reply_markup=get_partners_reply_keyboard(),
        )
        await show_next_profile(message, user_id, user, state=state, in_partners=True)
        break


def _partners_text_to_action(text: str) -> Optional[str]:
    """Сопоставление текста reply-кнопки с действием свайпа."""
    m = {
        PARTNERS_BTN_LIKE: "like",
        PARTNERS_BTN_BOOKMARK: "bookmark",
        PARTNERS_BTN_DISLIKE: "dislike",
    }
    return m.get(text)


@router.message(
    F.text.in_([PARTNERS_BTN_LIKE, PARTNERS_BTN_BOOKMARK, PARTNERS_BTN_DISLIKE]),
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
            await SwipeRepository.create_swipe(session, swiper_user_id, swiped_user_id, action)

            if action == "like":
                swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                # Уведомление о лайке не отправляем, если у лайкнувшего теневой или полный бан
                if swiper_user and (swiper_user.ban_status or "none") in ("none",):
                    swiper_name = swiper_user.name or "Пользователь"
                    await _send_like_notification(
                        message.bot, swiped_user_id, swiper_name, swiper_user_id
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
                        [InlineKeyboardButton(text="💬 Перейти в ЛС", url=link_to_other)]
                    ])
                    await message.answer(
                        "🎉 <b>БУУУУМ — это мэтч!</b>\n\n"
                        "У вас взаимный интерес. Удачно пообщаться!",
                        reply_markup=match_kb,
                    )
                    link_to_swiper = _get_dm_link(swiper_user) if swiper_user else f"tg://user?id={swiper_user_id}"
                    match_kb_other = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💬 Перейти в ЛС", url=link_to_swiper)]
                    ])
                    try:
                        await message.bot.send_message(
                            swiped_user_id,
                            "🎉 <b>БУУУУМ — это мэтч!</b>\n\n"
                            "У вас взаимный интерес. Удачно пообщаться!",
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
        await message.answer("Произошла ошибка. Попробуйте ещё раз или выйдите из раздела Партнеры.")


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
                await callback.answer("Анкета недоступна.", show_alert=True)
                return

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
            )
            if is_notif:
                kb = get_swipe_keyboard_from_notification(swiped_user_id, expanded=is_expand)
            else:
                kb = get_swipe_keyboard_expand_only(swiped_user_id, expanded=is_expand, from_notification=False)

            msg = callback.message
            if msg.photo:
                await msg.edit_caption(caption=caption_or_text, reply_markup=kb)
            else:
                await msg.edit_text(text=caption_or_text, reply_markup=kb)
            break
    except Exception as e:
        logger.error("Ошибка при развороте/сворачивании анкеты: %s", e, exc_info=True)
        await callback.answer("Не удалось обновить анкету.", show_alert=True)


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
            if not liker or not liker.short_description or not liker.full_description or not liker.qualities:
                viewer = await UserRepository.get_by_telegram_id(session, viewer_id)
                lang = getattr(viewer, "language", None) or "ru" if viewer else "ru"
                await callback.message.edit_text(
                    "Анкета этого пользователя недоступна.",
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
            profile_text = format_user_profile(liker, compatibility)
            try:
                await callback.message.delete()
            except Exception:
                pass
            if liker.photo_id:
                await callback.message.answer_photo(
                    photo=liker.photo_id,
                    caption=profile_text,
                    reply_markup=get_swipe_keyboard_from_notification(liker_id),
                )
            else:
                await callback.message.answer(
                    profile_text,
                    reply_markup=get_swipe_keyboard_from_notification(liker_id),
                )
            break
    except Exception as e:
        logger.error("Ошибка при показе анкеты лайкнувшего: %s", e, exc_info=True)
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)


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
                        [InlineKeyboardButton(text="💬 Перейти в ЛС", url=link_to_other)],
                        [get_back_button("main_menu", lang)],
                    ])
                    await callback.message.answer(
                        "🎉 <b>БУУУУМ — это мэтч!</b>\n\n"
                        "У вас взаимный интерес. Удачно пообщаться!",
                        reply_markup=match_kb,
                    )
                    # Второму пользователю — уведомление о мэтче
                    link_to_swiper = _get_dm_link(swiper_user) if swiper_user else f"tg://user?id={swiper_user_id}"
                    match_kb_other = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💬 Перейти в ЛС", url=link_to_swiper)]
                    ])
                    try:
                        await callback.bot.send_message(
                            swiped_user_id,
                            "🎉 <b>БУУУУМ — это мэтч!</b>\n\n"
                            "У вас взаимный интерес. Удачно пообщаться!",
                            reply_markup=match_kb_other,
                        )
                    except Exception as e:
                        logger.error("Ошибка отправки уведомления о мэтче (notif): %s", e)
                else:
                    await callback.message.answer(
                        "🤝 Вы проявили интерес. Если будет совпадение — мы сообщим!",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]]),
                    )
            else:
                await callback.message.answer(
                    "Вы ответили на анкету.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("main_menu", lang)]]),
                )
            break
    except Exception as e:
        logger.error("Ошибка при ответе из уведомления: %s", e, exc_info=True)
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


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
            empty_text = (
                "⭐ <b>Избранные</b>\n\n"
                "В избранном никого не осталось. Добавляйте анкеты кнопкой 🏷 в разделе «🤝 Партнёры»."
            )
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
        profile_text = format_user_profile(user, compatibility, expanded=False)
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
            # Сохраняем действие
            await SwipeRepository.create_swipe(
                session,
                swiper_user_id,
                swiped_user_id,
                action
            )
            
            # Если это лайк — уведомление не отправляем при теневом/полном бане лайкнувшего
            if action == "like":
                swiper_user = await UserRepository.get_by_telegram_id(session, swiper_user_id)
                if swiper_user and (swiper_user.ban_status or "none") in ("none",):
                    swiper_name = swiper_user.name or "Пользователь"
                    await _send_like_notification(
                        callback.bot, swiped_user_id, swiper_name, swiper_user_id
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
                            [InlineKeyboardButton(text="💬 Перейти в ЛС", url=link_to_other)]
                        ])
                        await callback.message.edit_text(
                            "🎉 <b>БУУУУМ — это мэтч!</b>\n\n"
                            "У вас взаимный интерес. Удачно пообщаться!",
                            reply_markup=match_kb_swiper,
                        )
                    except Exception:
                        try:
                            await callback.message.delete()
                        except Exception:
                            pass
                        await callback.message.answer(
                            "🎉 <b>БУУУУМ — это мэтч!</b>\n\n"
                            "У вас взаимный интерес. Удачно пообщаться!",
                            reply_markup=match_kb_swiper,
                        )
                    try:
                        other_name = swiper_user.name or "Пользователь"
                        link_to_swiper = _get_dm_link(swiper_user)
                        match_kb_swiped = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="💬 Перейти в ЛС", url=link_to_swiper)]
                        ])
                        await callback.bot.send_message(
                            swiped_user_id,
                            "🎉 <b>БУУУУМ — это мэтч!</b>\n\n"
                            "У вас взаимный интерес. Удачно пообщаться!",
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
                                text = format_user_profile(nu, comp)
                                if nu.photo_id:
                                    await callback.message.answer_photo(
                                        photo=nu.photo_id,
                                        caption=text,
                                        reply_markup=get_swipe_keyboard(nu.telegram_id),
                                    )
                                else:
                                    await callback.message.answer(
                                        text,
                                        reply_markup=get_swipe_keyboard(nu.telegram_id),
                                    )
                            else:
                                await callback.message.answer(
                                    "🤝 Вы просмотрели всех доступных пользователей. Попробуйте позже!",
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
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)


def register_handlers(dp) -> None:
    """Регистрация обработчиков свайпов"""
    dp.include_router(router)
