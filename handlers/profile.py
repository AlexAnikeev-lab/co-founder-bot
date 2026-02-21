"""
Обработчики профиля пользователя
"""

import html
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext

from keyboards.menu import get_profile_keyboard, get_profile_reply_keyboard
from keyboards.common import get_profile_language_keyboard
from texts.i18n import t, text_options
from states.registration import ProfileEditStates
from repositories.user_repository import UserRepository
from repositories.test_repository import TestResultRepository
from repositories.database import get_session
from utils.errors import handle_error
from utils.validators import (
    validate_name,
    validate_photo,
    validate_short_description,
    validate_full_description,
    validate_single_quality,
)

logger = logging.getLogger(__name__)
router = Router()


async def send_profile_view(
    message: Message, user_id: int, state: FSMContext, edit_message_id: int | None = None
) -> None:
    """Отправить экран профиля. Если передан edit_message_id — редактируем сообщение (текст/подпись, картинку, кнопки); удаление+отправка только если иначе нельзя (например текст→фото)."""
    await state.update_data(in_profile=True, profile_screen="profile")
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if not user or not user.is_registered:
            if edit_message_id:
                try:
                    _lang = "ru"
                    async for s in get_session():
                        u = await UserRepository.get_by_telegram_id(s, user_id)
                        if u:
                            _lang = getattr(u, "language", None) or "ru"
                        break
                    err = t(_lang, "profile_not_found")
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=edit_message_id,
                        text=err,
                    )
                except Exception:
                    await message.answer(t("ru", "profile_not_found"))
            else:
                await message.answer(t("ru", "profile_not_found"))
            return
        lang = getattr(user, "language", None) or "ru"
        ns = t(lang, "not_specified")
        profile_text = (
            f"{t(lang, 'profile_section')}\n\n"
            f"<b>{t(lang, 'profile_name')}:</b> {user.name or ns}\n"
            f"<b>{t(lang, 'profile_age')}:</b> {user.age or ns}\n\n"
        )
        if user.short_description:
            profile_text += f"<b>{t(lang, 'profile_about')}:</b>\n"
            profile_text += f"<blockquote>{html.escape(user.short_description)}</blockquote>\n\n"
        if user.qualities:
            qualities_list = user.qualities.split(",")
            profile_text += f"<b>{t(lang, 'profile_qualities')}:</b>\n"
            for q in qualities_list:
                profile_text += f"• {q.strip()}\n"
            profile_text += "\n"
        if user.full_description:
            profile_text += f"<b>{t(lang, 'profile_more')}:</b>\n"
            profile_text += f"<blockquote>{html.escape(user.full_description)}</blockquote>"
        kb = get_profile_keyboard(user.is_minor, lang)
        if edit_message_id:
            # С фото: сначала пробуем edit_message_media (если сообщение уже с фото); иначе удаляем и шлём с фото.
            # Без фото: редактируем текст и кнопки.
            edited = False
            if user.photo_id:
                try:
                    await message.bot.edit_message_media(
                        chat_id=message.chat.id,
                        message_id=edit_message_id,
                        media=InputMediaPhoto(media=user.photo_id, caption=profile_text),
                        reply_markup=kb,
                    )
                    await state.update_data(last_bot_message_id=edit_message_id)
                    edited = True
                except Exception:
                    pass
                if not edited:
                    # Сообщение было текстовым — в Telegram нельзя добавить фото через edit, удаляем и шлём с фото
                    try:
                        await message.bot.delete_message(chat_id=message.chat.id, message_id=edit_message_id)
                    except Exception:
                        pass
                    msg = await message.answer_photo(
                        photo=user.photo_id,
                        caption=profile_text,
                        reply_markup=kb,
                    )
                    await state.update_data(last_bot_message_id=msg.message_id)
            else:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=edit_message_id,
                        text=profile_text,
                        reply_markup=kb,
                    )
                    await state.update_data(last_bot_message_id=edit_message_id)
                except Exception:
                    try:
                        await message.bot.edit_message_caption(
                            chat_id=message.chat.id,
                            message_id=edit_message_id,
                            caption=profile_text,
                            reply_markup=kb,
                        )
                        await state.update_data(last_bot_message_id=edit_message_id)
                    except Exception:
                        try:
                            await message.bot.delete_message(chat_id=message.chat.id, message_id=edit_message_id)
                        except Exception:
                            pass
                        msg = await message.answer(profile_text, reply_markup=kb)
                        await state.update_data(last_bot_message_id=msg.message_id)
        else:
            if user.photo_id:
                msg = await message.answer_photo(
                    photo=user.photo_id,
                    caption=profile_text,
                    reply_markup=kb,
                )
            else:
                msg = await message.answer(profile_text, reply_markup=kb)
            await state.update_data(last_bot_message_id=msg.message_id)
            await message.answer(
                t(lang, "choose_section"),
                reply_markup=get_profile_reply_keyboard(user.is_minor, lang),
            )
        break


@router.message(F.text.in_(text_options("menu_profile")))
@router.callback_query(F.data == "profile")
async def show_profile(event, state: FSMContext) -> None:
    """Показать профиль и меню: Тесты, Люди, Premium, Назад (язык ru/en)."""
    try:
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

            if not user or not user.is_registered:
                await message.answer(t("ru", "not_registered_use_start"))
                return

            data = await state.get_data()
            profile_screen = data.get("profile_screen")
            last_mid = data.get("last_bot_message_id")
            if profile_screen in ("tests", "people", "edit") and last_mid:
                await state.update_data(in_profile=True, profile_screen="profile")
                await send_profile_view(message, user_id, state, edit_message_id=last_mid)
                return

            await state.update_data(in_profile=True, profile_screen="profile")

            lang = getattr(user, "language", None) or "ru"
            ns = t(lang, "not_specified")
            profile_text = f"{t(lang, 'profile_section')}\n\n"
            profile_text += f"<b>{t(lang, 'profile_name')}:</b> {user.name or ns}\n"
            profile_text += f"<b>{t(lang, 'profile_age')}:</b> {user.age or ns}\n\n"
            if user.short_description:
                profile_text += f"<b>{t(lang, 'profile_about')}:</b>\n"
                profile_text += f"<blockquote>{html.escape(user.short_description)}</blockquote>\n\n"
            if user.qualities:
                qualities_list = user.qualities.split(",")
                profile_text += f"<b>{t(lang, 'profile_qualities')}:</b>\n"
                for quality in qualities_list:
                    profile_text += f"• {quality.strip()}\n"
                profile_text += "\n"
            if user.full_description:
                profile_text += f"<b>{t(lang, 'profile_more')}:</b>\n"
                profile_text += f"<blockquote>{html.escape(user.full_description)}</blockquote>"

            if user.photo_id:
                msg = await message.answer_photo(
                    photo=user.photo_id,
                    caption=profile_text,
                    reply_markup=get_profile_keyboard(user.is_minor, lang),
                )
            else:
                msg = await message.answer(
                    profile_text,
                    reply_markup=get_profile_keyboard(user.is_minor, lang),
                )
            await state.update_data(last_bot_message_id=msg.message_id)
            await message.answer(t(lang, "choose_section"), reply_markup=get_profile_reply_keyboard(user.is_minor, lang))
            break

    except Exception as e:
        logger.error(f"Ошибка в show_profile: {e}", exc_info=True)
        await handle_error(None, e, "show_profile")


@router.message(F.text.in_(text_options("profile_people")))
async def profile_reply_people(message: Message, state: FSMContext) -> None:
    """Раздел Люди по кнопке из меню профиля."""
    try:
        await message.delete()
    except Exception:
        pass
    await state.update_data(profile_screen="people")
    from keyboards.menu import get_people_keyboard
    text = (
        "👥 <b>Люди</b>\n\n"
        "Здесь ты можешь искать единомышленников, "
        "смотреть избранных и совпадения."
    )
    sent = await message.answer(text, reply_markup=get_people_keyboard())
    await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактирование профиля (язык ru/en)."""
    await callback.answer()
    await state.update_data(profile_screen="edit")
    from keyboards.profile import get_edit_profile_keyboard
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break
    try:
        await callback.message.edit_text(
            t(lang, "edit_profile_title"),
            reply_markup=get_edit_profile_keyboard(lang),
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            t(lang, "edit_profile_title"),
            reply_markup=get_edit_profile_keyboard(lang),
        )
        await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "delete_profile")
async def delete_profile_confirm(callback: CallbackQuery) -> None:
    """Подтверждение удаления профиля (язык ru/en)."""
    await callback.answer()
    from keyboards.profile import get_delete_confirm_keyboard
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break
    text = t(lang, "delete_confirm_title")
    try:
        await callback.message.edit_text(text, reply_markup=get_delete_confirm_keyboard(lang))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=get_delete_confirm_keyboard(lang))


@router.callback_query(F.data == "delete_profile_confirm")
async def delete_profile_yes(callback: CallbackQuery) -> None:
    """Удаление профиля подтверждено"""
    try:
        await callback.answer()
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
            if user:
                user_id = callback.from_user.id
                await TestResultRepository.delete_by_user_id(session, user_id)
                await UserRepository.delete(session, user)
                try:
                    await callback.message.edit_text("✅ Профиль удалён. Используй /start для новой регистрации.")
                except Exception:
                    await callback.message.answer("✅ Профиль удалён. Используй /start для новой регистрации.")
            else:
                try:
                    await callback.message.edit_text("❌ Профиль не найден.")
                except Exception:
                    await callback.message.answer("❌ Профиль не найден.")
            break
    except Exception as e:
        logger.error(f"Ошибка в delete_profile_yes: {e}", exc_info=True)
        try:
            await callback.message.edit_text("❌ Ошибка при удалении профиля.")
        except Exception:
            await callback.message.answer("❌ Ошибка при удалении профиля.")


@router.callback_query(F.data == "delete_profile_cancel")
async def delete_profile_no(callback: CallbackQuery) -> None:
    """Отмена удаления профиля"""
    await callback.answer()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            try:
                await callback.message.edit_text("Отмена. Профиль сохранён.", reply_markup=get_profile_keyboard(user.is_minor, lang))
            except Exception:
                await callback.message.answer("Отмена. Профиль сохранён.", reply_markup=get_profile_keyboard(user.is_minor, lang))
        else:
            try:
                await callback.message.edit_text("❌ Профиль не найден.")
            except Exception:
                await callback.message.answer("❌ Профиль не найден.")
        break


@router.callback_query(F.data == "profile_change_language")
async def profile_change_language(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать выбор языка в профиле."""
    await callback.answer()
    text = t("ru", "language_question")
    try:
        await callback.message.edit_text(text, reply_markup=get_profile_language_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_profile_language_keyboard())


@router.callback_query(F.data.in_({"profile_set_lang_ru", "profile_set_lang_en"}))
async def profile_set_language(callback: CallbackQuery, state: FSMContext) -> None:
    """Смена языка в профиле: сохранить и обновить экран профиля."""
    await callback.answer()
    lang = "ru" if callback.data == "profile_set_lang_ru" else "en"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            await UserRepository.update(session, user, language=lang)
            await send_profile_view(
                callback.message,
                callback.from_user.id,
                state,
                edit_message_id=callback.message.message_id,
            )
        break
    # Краткое подтверждение можно отправить отдельно, но т.к. мы уже отредактировали в профиль — не дублируем


@router.callback_query(F.data == "people")
async def show_people(callback: CallbackQuery, state: FSMContext) -> None:
    """Раздел Люди - подменю с поиском, избранными и совпадениями"""
    await callback.answer()
    await state.update_data(profile_screen="people")
    from keyboards.menu import get_people_keyboard
    
    text = (
        "👥 <b>Люди</b>\n\n"
        "Здесь ты можешь искать единомышленников, "
        "смотреть избранных и совпадения."
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "search_people")
async def search_people(callback: CallbackQuery, state: FSMContext) -> None:
    """Поиск людей"""
    await callback.answer()
    await state.update_data(profile_screen="search")
    from keyboards.menu import get_people_keyboard
    
    text = (
        "🔍 <b>Поиск людей</b>\n\n"
        "Функция в разработке."
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=sent.message_id)


async def _show_favorite_at_index(
    callback: CallbackQuery,
    state: FSMContext,
    favorites_ids: list,
    index: int,
    lang: str = "ru",
) -> None:
    """Показать анкету из избранного по индексу (редактируем текущее сообщение или отправляем новое)."""
    from handlers.swipe import format_user_profile
    from keyboards.swipe import get_favorites_keyboard
    from services.compatibility_service import CompatibilityService
    from handlers.swipe import _get_user_profile

    if index < 0 or index >= len(favorites_ids):
        return
    uid = favorites_ids[index]
    viewer_id = callback.from_user.id
    msg = callback.message

    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, uid)
        if not user:
            return
        compatibility = None
        tr_viewer = await TestResultRepository.get_by_user_id(session, viewer_id)
        tr_shown = await TestResultRepository.get_by_user_id(session, uid)
        if tr_viewer and tr_shown and tr_viewer.main_test_completed and tr_shown.main_test_completed:
            pv = _get_user_profile(tr_viewer, include_label=True)
            pl = _get_user_profile(tr_shown, include_label=True)
            if pv and pl:
                compatibility, _ = CompatibilityService.calculate_compatibility_detailed(pv, pl)
        profile_text = format_user_profile(user, compatibility, expanded=False)
        total = len(favorites_ids)
        kb = get_favorites_keyboard(uid, index, total, expanded=False, lang=lang)
        new_id = msg.message_id
        try:
            if msg.photo and user.photo_id:
                await msg.edit_media(
                    InputMediaPhoto(media=user.photo_id, caption=profile_text, parse_mode="HTML"),
                )
                await msg.edit_reply_markup(reply_markup=kb)
            else:
                try:
                    await msg.delete()
                except Exception:
                    pass
                if user.photo_id:
                    sent = await msg.answer_photo(
                        photo=user.photo_id,
                        caption=profile_text,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                else:
                    sent = await msg.answer(profile_text, reply_markup=kb, parse_mode="HTML")
                new_id = sent.message_id
        except Exception:
            try:
                await msg.delete()
            except Exception:
                pass
            if user.photo_id:
                sent = await msg.answer_photo(
                    photo=user.photo_id,
                    caption=profile_text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            else:
                sent = await msg.answer(profile_text, reply_markup=kb, parse_mode="HTML")
            new_id = sent.message_id
        await state.update_data(
            in_favorites=True,
            favorites_ids=favorites_ids,
            favorites_index=index,
            current_partner_id=uid,
            last_bot_message_id=new_id,
        )
        break


@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery, state: FSMContext) -> None:
    """Избранные — список добавленных в закладки; показ по одной анкете с кнопками Назад/Далее."""
    await callback.answer()
    await state.update_data(profile_screen="favorites")
    from keyboards.menu import get_people_keyboard
    from repositories.swipe_repository import SwipeRepository
    from handlers.swipe import format_user_profile
    from keyboards.swipe import get_favorites_keyboard

    user_id = callback.from_user.id
    lang = "ru"
    async for session in get_session():
        u = await UserRepository.get_by_telegram_id(session, user_id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break

    try:
        async for session in get_session():
            favorites_ids = await SwipeRepository.get_bookmarked_user_ids(session, user_id)
            if not favorites_ids:
                text = (
                    "⭐ <b>Избранные</b>\n\n"
                    "Здесь будут люди, которых ты добавил в избранное (кнопка 🏷 в поиске партнёров)."
                )
                try:
                    await callback.message.edit_text(text, reply_markup=get_people_keyboard(lang))
                except Exception:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=get_people_keyboard(lang))
                await state.update_data(in_favorites=False, favorites_ids=[], favorites_index=0)
                return
            await state.update_data(
                in_favorites=True,
                favorites_ids=favorites_ids,
                favorites_index=0,
                current_partner_id=favorites_ids[0],
            )
            uid = favorites_ids[0]
            user = await UserRepository.get_by_telegram_id(session, uid)
            if not user:
                await callback.message.edit_text(
                    "⭐ <b>Избранные</b>\n\nНе удалось загрузить анкету.",
                    reply_markup=get_people_keyboard(lang),
                )
                return
            from services.compatibility_service import CompatibilityService
            from handlers.swipe import _get_user_profile
            compatibility = None
            tr_viewer = await TestResultRepository.get_by_user_id(session, user_id)
            tr_shown = await TestResultRepository.get_by_user_id(session, uid)
            if tr_viewer and tr_shown and tr_viewer.main_test_completed and tr_shown.main_test_completed:
                pv = _get_user_profile(tr_viewer, include_label=True)
                pl = _get_user_profile(tr_shown, include_label=True)
                if pv and pl:
                    compatibility, _ = CompatibilityService.calculate_compatibility_detailed(pv, pl)
            profile_text = format_user_profile(user, compatibility, expanded=False)
            total = len(favorites_ids)
            kb = get_favorites_keyboard(uid, 0, total, expanded=False, lang=lang)
            try:
                await callback.message.delete()
            except Exception:
                pass
            if user.photo_id:
                sent = await callback.message.answer_photo(
                    photo=user.photo_id,
                    caption=profile_text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            else:
                sent = await callback.message.answer(profile_text, reply_markup=kb, parse_mode="HTML")
            await state.update_data(last_bot_message_id=sent.message_id)
            break
    except Exception as e:
        logger.error("Ошибка загрузки избранного: %s", e, exc_info=True)
        await callback.message.edit_text(
            "⭐ <b>Избранные</b>\n\nНе удалось загрузить список. Попробуйте позже.",
            reply_markup=get_people_keyboard(lang),
        )


@router.callback_query(F.data.startswith("favorites_prev:"))
async def favorites_prev(callback: CallbackQuery, state: FSMContext) -> None:
    """Листание избранного назад."""
    await callback.answer()
    data = await state.get_data()
    favorites_ids = data.get("favorites_ids") or []
    if not favorites_ids:
        return
    try:
        index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        return
    new_index = max(0, index - 1)
    lang = (await state.get_data()).get("language", "ru")
    async for _ in get_session():
        u = await UserRepository.get_by_telegram_id(_, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _show_favorite_at_index(callback, state, favorites_ids, new_index, lang=lang)


@router.callback_query(F.data.startswith("favorites_next:"))
async def favorites_next(callback: CallbackQuery, state: FSMContext) -> None:
    """Листание избранного вперёд."""
    await callback.answer()
    data = await state.get_data()
    favorites_ids = data.get("favorites_ids") or []
    if not favorites_ids:
        return
    try:
        index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        return
    new_index = min(len(favorites_ids) - 1, index + 1)
    lang = (await state.get_data()).get("language", "ru")
    async for _ in get_session():
        u = await UserRepository.get_by_telegram_id(_, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _show_favorite_at_index(callback, state, favorites_ids, new_index, lang=lang)


@router.callback_query(F.data.startswith("expand_favorites:"))
@router.callback_query(F.data.startswith("collapse_favorites:"))
async def handle_expand_collapse_favorites(callback: CallbackQuery, state: FSMContext) -> None:
    """Развернуть/свернуть описание в карточке избранного."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) != 3:
        return
    try:
        swiped_user_id = int(parts[1])
        index = int(parts[2])
    except (ValueError, IndexError):
        return
    is_expand = callback.data.startswith("expand_favorites:")
    data = await state.get_data()
    favorites_ids = data.get("favorites_ids") or []
    if index < 0 or index >= len(favorites_ids) or favorites_ids[index] != swiped_user_id:
        return
    lang = data.get("language", "ru")
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, swiped_user_id)
        if not user:
            return
        from handlers.swipe import format_user_profile
        from keyboards.swipe import get_favorites_keyboard
        from services.compatibility_service import CompatibilityService
        from handlers.swipe import _get_user_profile
        compatibility = None
        compatibility_explanation = None
        viewer_id = callback.from_user.id
        tr_viewer = await TestResultRepository.get_by_user_id(session, viewer_id)
        tr_shown = await TestResultRepository.get_by_user_id(session, swiped_user_id)
        if tr_viewer and tr_shown and tr_viewer.main_test_completed and tr_shown.main_test_completed:
            pv = _get_user_profile(tr_viewer, include_label=True)
            pl = _get_user_profile(tr_shown, include_label=True)
            if pv and pl:
                compatibility, details = CompatibilityService.calculate_compatibility_detailed(pv, pl)
                if is_expand and compatibility is not None:
                    compatibility_explanation = CompatibilityService.get_compatibility_explanation(
                        compatibility, details
                    )
        profile_text = format_user_profile(
            user, compatibility, expanded=is_expand, compatibility_explanation=compatibility_explanation
        )
        total = len(favorites_ids)
        kb = get_favorites_keyboard(swiped_user_id, index, total, expanded=is_expand, lang=lang)
        msg = callback.message
        if msg.photo:
            await msg.edit_caption(caption=profile_text, reply_markup=kb, parse_mode="HTML")
        else:
            await msg.edit_text(text=profile_text, reply_markup=kb, parse_mode="HTML")
        break


@router.callback_query(F.data == "matches")
async def show_matches(callback: CallbackQuery, state: FSMContext) -> None:
    """Совпадения — список людей с взаимным лайком и кнопка «Перейти в ЛС»"""
    await callback.answer()
    await state.update_data(profile_screen="matches")
    from keyboards.menu import get_people_keyboard
    from repositories.database import get_session
    from repositories.swipe_repository import SwipeRepository
    from repositories.user_repository import UserRepository
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    user_id = callback.from_user.id
    builder = InlineKeyboardBuilder()

    try:
        async for session in get_session():
            match_ids = await SwipeRepository.get_mutual_matches(session, user_id)
            if not match_ids:
                text = (
                    "🤝 <b>Совпадения</b>\n\n"
                    "Здесь будут люди, с которыми у тебя взаимный интерес.\n\n"
                    "Пока ни с кем нет совпадений. Лайкайте анкеты в разделе «🤝 Партнёры» — когда кто-то ответит лайком, вы оба появятся здесь."
                )
                builder.adjust(1)
                break
            # Загружаем пользователей по id
            lines = ["🤝 <b>Совпадения</b>\n\nЛюди, с которыми у вас взаимный интерес:\n"]
            for mid in match_ids:
                u = await UserRepository.get_by_telegram_id(session, mid)
                if u:
                    name = u.name or "Пользователь"
                    lines.append(f"• {name}")
                    uname = (u.username or "").strip().lstrip("@")
                    url = f"https://t.me/{uname}" if uname else f"tg://user?id={u.telegram_id}"
                    builder.add(
                        InlineKeyboardButton(text=f"💬 {name} — в ЛС", url=url)
                    )
            builder.adjust(1)
            text = "\n".join(lines)
            break
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Ошибка загрузки совпадений: %s", e, exc_info=True)
        text = "Не удалось загрузить список. Попробуйте позже."
        builder.adjust(1)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=builder.as_markup(),
        )
        await state.update_data(last_bot_message_id=sent.message_id)


# Обработчики редактирования полей профиля

@router.callback_query(F.data == "edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования имени"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    from texts.messages import EDIT_CURRENT_COPYABLE
    text = "✏️ <b>Изменение имени</b>\n\nВведи новое имя:"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user and user.name:
            text += f"\n\n{EDIT_CURRENT_COPYABLE}\n<code>{html.escape(user.name)}</code>"
        break
    try:
        await callback.message.edit_text(text, reply_markup=get_cancel_button())
    except Exception:
        await callback.message.answer(text, reply_markup=get_cancel_button())
    await state.set_state(ProfileEditStates.editing_name)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_name)
async def process_edit_name(message: Message, state: FSMContext) -> None:
    """Обработка нового имени"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    if not validate_name(message.text):
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Имя: от 2 до 50 символов, только буквы.\n\n✏️ <b>Изменение имени</b>\n\nВведи новое имя:",
                    reply_markup=None
                )
            except Exception:
                pass
        return
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, name=message.text)
            await state.clear()
            await send_profile_view(message, message.from_user.id, state, edit_message_id=last_msg_id)
        break


@router.callback_query(F.data == "edit_photo")
async def start_edit_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования фото"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    try:
        await callback.message.edit_text(
            "📸 <b>Изменение фото</b>\n\n"
            "Отправь новое фото:",
            reply_markup=get_cancel_button()
        )
    except Exception:
        await callback.message.answer(
            "📸 <b>Изменение фото</b>\n\n"
            "Отправь новое фото:",
            reply_markup=get_cancel_button()
        )
    await state.set_state(ProfileEditStates.editing_photo)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_photo, F.photo)
async def process_edit_photo(message: Message, state: FSMContext) -> None:
    """Обработка нового фото"""
    try:
        await message.delete()
    except Exception:
        pass
    
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, photo_id=photo_id)
            await state.clear()
            await send_profile_view(message, message.from_user.id, state, edit_message_id=last_msg_id)
        break


@router.callback_query(F.data == "edit_short_description")
async def start_edit_short_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования краткого описания"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    from texts.messages import SHORT_DESCRIPTION_REQUEST, EDIT_CURRENT_COPYABLE
    text = SHORT_DESCRIPTION_REQUEST
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user and user.short_description:
            text += f"\n\n{EDIT_CURRENT_COPYABLE}\n<code>{html.escape(user.short_description)}</code>"
        break
    try:
        await callback.message.edit_text(text, reply_markup=get_cancel_button())
    except Exception:
        await callback.message.answer(text, reply_markup=get_cancel_button())
    await state.set_state(ProfileEditStates.editing_short_description)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_short_description)
async def process_edit_short_description(message: Message, state: FSMContext) -> None:
    """Обработка нового краткого описания"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    if not validate_short_description(message.text):
        if last_msg_id:
            try:
                from texts.messages import SHORT_DESCRIPTION_REQUEST
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Краткое описание: от 10 до 200 символов.\n\n" + SHORT_DESCRIPTION_REQUEST,
                    reply_markup=None
                )
            except Exception:
                pass
        return
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, short_description=message.text)
            await state.clear()
            await send_profile_view(message, message.from_user.id, state, edit_message_id=last_msg_id)
        break


@router.callback_query(F.data == "edit_full_description")
async def start_edit_full_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования полного описания"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    from texts.messages import FULL_DESCRIPTION_REQUEST, EDIT_CURRENT_COPYABLE
    text = FULL_DESCRIPTION_REQUEST
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user and user.full_description:
            text += f"\n\n{EDIT_CURRENT_COPYABLE}\n<pre>{html.escape(user.full_description)}</pre>"
        break
    try:
        await callback.message.edit_text(text, reply_markup=get_cancel_button())
    except Exception:
        await callback.message.answer(text, reply_markup=get_cancel_button())
    await state.set_state(ProfileEditStates.editing_full_description)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_full_description)
async def process_edit_full_description(message: Message, state: FSMContext) -> None:
    """Обработка нового полного описания"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    if not validate_full_description(message.text):
        if last_msg_id:
            try:
                from texts.messages import FULL_DESCRIPTION_REQUEST
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Полное описание: от 20 до 1000 символов.\n\n" + FULL_DESCRIPTION_REQUEST,
                    reply_markup=None
                )
            except Exception:
                pass
        return
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, full_description=message.text)
            await state.clear()
            await send_profile_view(message, message.from_user.id, state, edit_message_id=last_msg_id)
        break


def _get_qualities_list(user_qualities: str | None) -> list[str]:
    """Разбить строку качеств на список из 3 элементов (добить пустыми при необходимости)."""
    if not user_qualities or not user_qualities.strip():
        return ["", "", ""]
    parts = [p.strip() for p in user_qualities.split(",", 2)]
    while len(parts) < 3:
        parts.append("")
    return parts[:3]


async def _start_edit_quality(
    callback: CallbackQuery,
    state: FSMContext,
    quality_index: int,
    request_text: str,
    edit_state: type,
) -> None:
    """Запрос одного качества (1–3)."""
    await callback.answer()
    from keyboards.common import get_cancel_button
    from texts.messages import EDIT_CURRENT_COPYABLE
    text = request_text
    try:
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
            if user and user.qualities:
                parts = _get_qualities_list(user.qualities)
                current = parts[quality_index] or "—"
                text = f"{request_text}\n\n{EDIT_CURRENT_COPYABLE}\n<code>{html.escape(current)}</code>"
            break
        await callback.message.edit_text(text, reply_markup=get_cancel_button())
    except Exception:
        await callback.message.answer(text, reply_markup=get_cancel_button())
    await state.set_state(edit_state)
    await state.update_data(last_bot_message_id=callback.message.message_id, editing_quality_index=quality_index)


@router.callback_query(F.data == "edit_quality_1")
async def start_edit_quality_1(callback: CallbackQuery, state: FSMContext) -> None:
    from texts.messages import QUALITY_1_REQUEST
    await _start_edit_quality(callback, state, 0, QUALITY_1_REQUEST, ProfileEditStates.editing_quality_1)


@router.callback_query(F.data == "edit_quality_2")
async def start_edit_quality_2(callback: CallbackQuery, state: FSMContext) -> None:
    from texts.messages import QUALITY_2_REQUEST
    await _start_edit_quality(callback, state, 1, QUALITY_2_REQUEST, ProfileEditStates.editing_quality_2)


@router.callback_query(F.data == "edit_quality_3")
async def start_edit_quality_3(callback: CallbackQuery, state: FSMContext) -> None:
    from texts.messages import QUALITY_3_REQUEST
    await _start_edit_quality(callback, state, 2, QUALITY_3_REQUEST, ProfileEditStates.editing_quality_3)


async def _process_edit_quality(
    message: Message, state: FSMContext, request_text: str
) -> None:
    """Сохранить одно качество и обновить профиль."""
    try:
        await message.delete()
    except Exception:
        pass
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    idx = data.get("editing_quality_index", 0)

    if not validate_single_quality(message.text):
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Укажи качество от 2 до 50 символов.\n\n" + request_text,
                    reply_markup=None,
                )
            except Exception:
                pass
        return

    new_value = message.text.strip()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            parts = _get_qualities_list(user.qualities)
            parts[idx] = new_value
            qualities_str = ",".join(parts)
            await UserRepository.update(session, user, qualities=qualities_str)
            await state.clear()
            await send_profile_view(message, message.from_user.id, state, edit_message_id=last_msg_id)
        break


@router.message(ProfileEditStates.editing_quality_1)
async def process_edit_quality_1(message: Message, state: FSMContext) -> None:
    from texts.messages import QUALITY_1_REQUEST
    await _process_edit_quality(message, state, QUALITY_1_REQUEST)


@router.message(ProfileEditStates.editing_quality_2)
async def process_edit_quality_2(message: Message, state: FSMContext) -> None:
    from texts.messages import QUALITY_2_REQUEST
    await _process_edit_quality(message, state, QUALITY_2_REQUEST)


@router.message(ProfileEditStates.editing_quality_3)
async def process_edit_quality_3(message: Message, state: FSMContext) -> None:
    from texts.messages import QUALITY_3_REQUEST
    await _process_edit_quality(message, state, QUALITY_3_REQUEST)


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
