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
    text_contains_emoji,
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
        if getattr(user, "city", None):
            profile_text = (
                f"{t(lang, 'profile_section')}\n\n"
                f"<b>{t(lang, 'profile_name')}:</b> {user.name or ns}\n"
                f"<b>{t(lang, 'profile_age')}:</b> {user.age or ns}\n"
                f"<b>{t(lang, 'profile_city')}:</b> {html.escape(user.city)}\n\n"
            )
        if user.short_description:
            profile_text += f"<b>{t(lang, 'profile_about')}:</b>\n"
            profile_text += f"<blockquote>{html.escape(user.short_description)}</blockquote>\n\n"
        if user.qualities:
            qualities_list = _get_qualities_list(user.qualities)
            profile_text += f"<b>{t(lang, 'profile_qualities')}:</b>\n"
            for q in qualities_list:
                if q:
                    profile_text += f"{q}\n"
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
                _lang = (getattr(user, "language", None) or "ru") if user else "ru"
                await message.answer(t(_lang, "not_registered_use_start"))
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
            if getattr(user, "city", None):
                profile_text += f"<b>{t(lang, 'profile_city')}:</b> {html.escape(user.city)}\n\n"
            if user.short_description:
                profile_text += f"<b>{t(lang, 'profile_about')}:</b>\n"
                profile_text += f"<blockquote>{html.escape(user.short_description)}</blockquote>\n\n"
            if user.qualities:
                qualities_list = _get_qualities_list(user.qualities)
                profile_text += f"<b>{t(lang, 'profile_qualities')}:</b>\n"
                for q in qualities_list:
                    if q:
                        profile_text += f"{q}\n"
                profile_text += "\n"
            if user.full_description:
                profile_text += f"<b>{t(lang, 'profile_more')}:</b>\n"
                profile_text += f"<blockquote>{html.escape(user.full_description)}</blockquote>"

            # При переходе в профиль удаляем предыдущее меню (Главное меню, «Выберите раздел» или сообщение с inline-кнопками)
            data = await state.get_data()
            ids_to_del = [data.get("last_bot_message_id"), data.get("profile_section_message_id"), message.message_id]
            for mid in ids_to_del:
                if mid:
                    try:
                        await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)
                    except Exception:
                        pass
            await state.update_data(profile_section_message_id=None)

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
            sec_msg = await message.answer(t(lang, "choose_section"), reply_markup=get_profile_reply_keyboard(user.is_minor, lang))
            await state.update_data(profile_section_message_id=sec_msg.message_id)
            break

    except Exception as e:
        logger.error(f"Ошибка в show_profile: {e}", exc_info=True)
        await handle_error(None, e, "show_profile")


@router.message(F.text.in_(text_options("profile_people")))
async def profile_reply_people(message: Message, state: FSMContext) -> None:
    """Раздел Люди по кнопке из меню профиля. Удаляем «Выберите раздел» и сообщение профиля."""
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
    await state.update_data(profile_section_message_id=None, profile_screen="people")
    from keyboards.menu import get_people_keyboard
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    text = t(lang, "people_title") + "\n\n" + t(lang, "people_intro")
    sent = await message.answer(text, reply_markup=get_people_keyboard(lang))
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
                lang = getattr(user, "language", None) or "ru"
                user_id = callback.from_user.id
                await TestResultRepository.delete_by_user_id(session, user_id)
                await UserRepository.delete(session, user)
                txt = t(lang, "profile_deleted")
                try:
                    await callback.message.edit_text(txt)
                except Exception:
                    await callback.message.answer(txt)
            else:
                lang = "ru"
                try:
                    await callback.message.edit_text(t("ru", "profile_not_found"))
                except Exception:
                    await callback.message.answer(t("ru", "profile_not_found"))
            break
    except Exception as e:
        logger.error(f"Ошибка в delete_profile_yes: {e}", exc_info=True)
        _err_lang = "ru"
        async for s in get_session():
            u = await UserRepository.get_by_telegram_id(s, callback.from_user.id)
            if u:
                _err_lang = getattr(u, "language", None) or "ru"
            break
        txt = t(_err_lang, "profile_delete_error")
        try:
            await callback.message.edit_text(txt)
        except Exception:
            await callback.message.answer(txt)


@router.callback_query(F.data == "delete_profile_cancel")
async def delete_profile_no(callback: CallbackQuery) -> None:
    """Отмена удаления профиля"""
    await callback.answer()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            txt = t(lang, "cancel_profile_saved")
            try:
                await callback.message.edit_text(txt, reply_markup=get_profile_keyboard(user.is_minor, lang))
            except Exception:
                await callback.message.answer(txt, reply_markup=get_profile_keyboard(user.is_minor, lang))
        else:
            txt = t("ru", "profile_not_found")
            try:
                await callback.message.edit_text(txt)
            except Exception:
                await callback.message.answer(txt)
        break


@router.callback_query(F.data == "profile_change_language")
async def profile_change_language(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать выбор языка в профиле (текст и кнопки на текущем языке)."""
    await callback.answer()
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break
    text = t(lang, "language_question")
    try:
        await callback.message.edit_text(text, reply_markup=get_profile_language_keyboard(lang))
    except Exception:
        await callback.message.answer(text, reply_markup=get_profile_language_keyboard(lang))


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
    """Раздел Люди — подменю. Удаляем сообщение «Выберите раздел»."""
    await callback.answer()
    await state.update_data(profile_screen="people")
    from keyboards.menu import get_people_keyboard
    data = await state.get_data()
    section_mid = data.get("profile_section_message_id")
    if section_mid:
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=section_mid)
        except Exception:
            pass
        await state.update_data(profile_section_message_id=None)
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    text = t(lang, "people_title") + "\n\n" + t(lang, "people_intro")
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_people_keyboard(lang)
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=get_people_keyboard(lang)
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
        profile_text = format_user_profile(user, compatibility, expanded=False, lang=lang)
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
                text = t(lang, "people_favorites") + "\n\n" + t(lang, "favorites_empty_text")
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
                    t(lang, "people_favorites") + "\n\n" + t(lang, "favorites_load_error"),
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
            profile_text = format_user_profile(user, compatibility, expanded=False, lang=lang)
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
        _lang = "ru"
        async for s in get_session():
            u = await UserRepository.get_by_telegram_id(s, user_id)
            if u:
                _lang = getattr(u, "language", None) or "ru"
            break
        await callback.message.edit_text(
            t(_lang, "people_favorites") + "\n\n" + t(_lang, "favorites_load_list_error"),
            reply_markup=get_people_keyboard(_lang),
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
                        compatibility, details, lang=lang
                    )
        profile_text = format_user_profile(
            user, compatibility, expanded=is_expand, compatibility_explanation=compatibility_explanation, lang=lang
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
                text = t(lang, "people_matches") + "\n\n" + t(lang, "matches_empty_text") + "\n\n" + t(lang, "matches_empty_hint")
                builder.adjust(1)
                break
            # Загружаем пользователей по id
            _u = await UserRepository.get_by_telegram_id(session, user_id)
            lang = (getattr(_u, "language", None) or "ru") if _u else "ru"
            lines = [t(lang, "people_matches") + "\n\n" + t(lang, "matches_list_title") + "\n"]
            for mid in match_ids:
                u = await UserRepository.get_by_telegram_id(session, mid)
                if u:
                    name = u.name or t(lang, "card_user_fallback")
                    lines.append(f"• {name}")
                    uname = (u.username or "").strip().lstrip("@")
                    url = f"https://t.me/{uname}" if uname else f"tg://user?id={u.telegram_id}"
                    builder.add(
                        InlineKeyboardButton(text=t(lang, "matches_btn_dm").format(name=name), url=url)
                    )
            builder.adjust(1)
            text = "\n".join(lines)
            break
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Ошибка загрузки совпадений: %s", e, exc_info=True)
        _lang = "ru"
        async for _s in get_session():
            _u = await UserRepository.get_by_telegram_id(_s, user_id)
            if _u:
                _lang = getattr(_u, "language", None) or "ru"
            break
        text = t(_lang, "favorites_load_list_error")
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
    lang = "ru"
    text = t(lang, "edit_name_title")
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            text = t(lang, "edit_name_title")
            if user.name:
                text += f"\n\n{t(lang, 'edit_current_copyable')}\n<code>{html.escape(user.name)}</code>"
        break
    target_message_id = callback.message.message_id
    try:
        await callback.message.edit_text(text, reply_markup=get_cancel_button(lang))
    except Exception:
        sent = await callback.message.answer(text, reply_markup=get_cancel_button(lang))
        target_message_id = sent.message_id
    await state.set_state(ProfileEditStates.editing_name)
    await state.update_data(last_bot_message_id=target_message_id)


@router.message(ProfileEditStates.editing_name)
async def process_edit_name(message: Message, state: FSMContext) -> None:
    """Обработка нового имени"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    if not validate_name(message.text):
        if last_msg_id:
            try:
                err_text = t(lang, "edit_name_error") + "\n\n" + t(lang, "edit_name_title")
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=err_text,
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
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break
    text = t(lang, "edit_photo_title") + "\n\n" + t(lang, "edit_photo_request")
    target_message_id = callback.message.message_id
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_cancel_button(lang)
        )
    except Exception:
        sent = await callback.message.answer(
            text,
            reply_markup=get_cancel_button(lang)
        )
        target_message_id = sent.message_id
    await state.set_state(ProfileEditStates.editing_photo)
    await state.update_data(last_bot_message_id=target_message_id)


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
    lang = "ru"
    text = ""
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            text = t(lang, "short_description_request")
            if user.short_description:
                text += f"\n\n{t(lang, 'edit_current_copyable')}\n<code>{html.escape(user.short_description)}</code>"
        else:
            text = t(lang, "short_description_request")
        break
    target_message_id = callback.message.message_id
    try:
        await callback.message.edit_text(text, reply_markup=get_cancel_button(lang))
    except Exception:
        sent = await callback.message.answer(text, reply_markup=get_cancel_button(lang))
        target_message_id = sent.message_id
    await state.set_state(ProfileEditStates.editing_short_description)
    await state.update_data(last_bot_message_id=target_message_id)


@router.message(ProfileEditStates.editing_short_description)
async def process_edit_short_description(message: Message, state: FSMContext) -> None:
    """Обработка нового краткого описания"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    if not validate_short_description(message.text):
        if last_msg_id:
            try:
                err_text = t(lang, "edit_short_desc_error") + "\n\n" + t(lang, "short_description_request")
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=err_text,
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
    lang = "ru"
    text = ""
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            text = t(lang, "full_description_request")
            if user.full_description:
                text += f"\n\n{t(lang, 'edit_current_copyable')}\n<pre>{html.escape(user.full_description)}</pre>"
        else:
            text = t(lang, "full_description_request")
        break
    target_message_id = callback.message.message_id
    try:
        await callback.message.edit_text(text, reply_markup=get_cancel_button(lang))
    except Exception:
        sent = await callback.message.answer(text, reply_markup=get_cancel_button(lang))
        target_message_id = sent.message_id
    await state.set_state(ProfileEditStates.editing_full_description)
    await state.update_data(last_bot_message_id=target_message_id)


@router.message(ProfileEditStates.editing_full_description)
async def process_edit_full_description(message: Message, state: FSMContext) -> None:
    """Обработка нового полного описания"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    if not validate_full_description(message.text):
        if last_msg_id:
            try:
                err_text = t(lang, "edit_full_desc_error") + "\n\n" + t(lang, "full_description_request")
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=err_text,
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


def _parse_qualities_to_slots(user_qualities: str | None) -> list[tuple[str, str]]:
    """Разобрать строку качеств в до 3 слотов (emoji, text). Формат 'emoji|text\\n' или старый 'q1, q2, q3'."""
    if not user_qualities or not user_qualities.strip():
        return [("•", ""), ("•", ""), ("•", "")]
    lines = [ln.strip() for ln in user_qualities.strip().split("\n") if ln.strip()]
    slots = []
    for line in lines[:3]:
        if "|" in line:
            emoji, text = line.split("|", 1)
            slots.append((emoji.strip() or "•", text.strip()))
        else:
            slots.append(("•", line))
    while len(slots) < 3:
        slots.append(("•", ""))
    return slots[:3]


def _build_qualities_from_slots(slots: list[tuple[str, str]]) -> str:
    """Собрать строку качеств из слотов (emoji, text). Пустые тексты пропускаются."""
    lines = [f"{e}|{t}" for e, t in slots if t]
    return "\n".join(lines) if lines else ""


def _get_qualities_list(user_qualities: str | None) -> list[str]:
    """Список из 3 строк для отображения: 'emoji text' (поддержка форматов emoji|text и запятая)."""
    slots = _parse_qualities_to_slots(user_qualities)
    return [f"{e} {t}".strip() if t else "" for e, t in slots]


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
    text = request_text
    lang = "ru"
    target_message_id = callback.message.message_id
    try:
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
            if user:
                lang = getattr(user, "language", None) or "ru"
                if user.qualities:
                    slots = _parse_qualities_to_slots(user.qualities)
                    if quality_index < len(slots):
                        emoji, text_part = slots[quality_index]
                        text_only = (text_part or "").strip()
                        if text_only:
                            current_line = f"{emoji} <code>{html.escape(text_only)}</code>"
                        else:
                            current_line = "—"
                    else:
                        current_line = "—"
                    text = f"{request_text}\n\n{t(lang, 'edit_current_copyable')}\n{current_line}"
            break
        await callback.message.edit_text(text, reply_markup=get_cancel_button(lang))
    except Exception:
        sent = await callback.message.answer(text, reply_markup=get_cancel_button(lang))
        target_message_id = sent.message_id
    await state.set_state(edit_state)
    await state.update_data(last_bot_message_id=target_message_id, editing_quality_index=quality_index)


@router.callback_query(F.data == "edit_quality_1")
async def start_edit_quality_1(callback: CallbackQuery, state: FSMContext) -> None:
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _start_edit_quality(callback, state, 0, t(lang, "quality_1_request"), ProfileEditStates.editing_quality_1)


@router.callback_query(F.data == "edit_quality_2")
async def start_edit_quality_2(callback: CallbackQuery, state: FSMContext) -> None:
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _start_edit_quality(callback, state, 1, t(lang, "quality_2_request"), ProfileEditStates.editing_quality_2)


@router.callback_query(F.data == "edit_quality_3")
async def start_edit_quality_3(callback: CallbackQuery, state: FSMContext) -> None:
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, callback.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _start_edit_quality(callback, state, 2, t(lang, "quality_3_request"), ProfileEditStates.editing_quality_3)


async def _process_edit_quality(
    message: Message, state: FSMContext, request_text: str
) -> None:
    """Сохранить одно качество: текст без эмодзи, затем выбор смайлика и возврат в профиль."""
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    idx = data.get("editing_quality_index", 0)
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break

    if not validate_single_quality(message.text):
        invalid_ids = list(data.get("invalid_user_message_ids") or [])
        invalid_ids.append(message.message_id)
        await state.update_data(invalid_user_message_ids=invalid_ids)
        length = len((message.text or "").strip())
        base_err = t(lang, "edit_quality_error")
        if lang == "ru":
            base_err = f"{base_err} Сейчас у тебя: {length}."
        else:
            base_err = f"{base_err} You now have: {length}."
        err_text = base_err
        from keyboards.common import get_cancel_button
        sent = await message.answer(err_text, reply_markup=get_cancel_button(lang))
        await state.update_data(last_quality_error_message_id=sent.message_id)
        return

    if text_contains_emoji(message.text):
        invalid_ids = list(data.get("invalid_user_message_ids") or [])
        invalid_ids.append(message.message_id)
        warn_msg = await message.answer(t(lang, "quality_no_emoji_in_text"))
        await state.update_data(
            invalid_user_message_ids=invalid_ids,
            last_warning_message_id=warn_msg.message_id,
        )
        return

    # Валидный ввод: удаляем все предупреждения и неудачные попытки (последнее сообщение пользователя не трогаем)
    chat_id = message.chat.id
    bot = message.bot
    for mid in (data.get("invalid_user_message_ids") or []):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
    if data.get("last_warning_message_id"):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=data["last_warning_message_id"])
        except Exception:
            pass
    if data.get("last_quality_error_message_id"):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=data["last_quality_error_message_id"])
        except Exception:
            pass
    await state.update_data(
        invalid_user_message_ids=[],
        last_warning_message_id=None,
        last_quality_error_message_id=None,
    )

    # Сохраняем новый текст и показываем выбор эмодзи (как при регистрации)
    new_value = message.text.strip()
    await state.update_data(
        editing_quality_new_text=new_value,
        edit_user_message_id=message.message_id,
    )
    from keyboards.quality_emoji import get_quality_emoji_keyboard
    step = idx + 1
    await message.answer(
        t(lang, "quality_emoji_prompt"),
        reply_markup=get_quality_emoji_keyboard(step, prefix="edit", lang=lang),
    )
    emoji_states = {
        0: ProfileEditStates.editing_quality_1_emoji,
        1: ProfileEditStates.editing_quality_2_emoji,
        2: ProfileEditStates.editing_quality_3_emoji,
    }
    await state.set_state(emoji_states.get(idx, ProfileEditStates.editing_quality_1_emoji))


@router.callback_query(F.data.regexp(r"^edit_q[123]_emoji:.+"))
async def profile_edit_quality_emoji_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор смайлика при редактировании качества: применяем, чистим служебные сообщения и показываем профиль."""
    from keyboards.quality_emoji import QUALITY_EMOJI_LIST
    await callback.answer()
    try:
        parts = callback.data.split("_emoji:", 1)
        if len(parts) != 2:
            return
        step_str = parts[0].replace("edit_q", "")
        if step_str not in ("1", "2", "3"):
            return
        idx = int(step_str) - 1
        emoji = parts[1].strip()
        if emoji not in QUALITY_EMOJI_LIST:
            return

        data = await state.get_data()
        new_text = (data.get("editing_quality_new_text") or "").strip()
        last_msg_id = data.get("last_bot_message_id")
        user_msg_id = data.get("edit_user_message_id")
        chat_id = callback.message.chat.id
        bot = callback.bot

        # Удаляем сообщение с эмодзи-клавиатурой
        try:
            await callback.message.delete()
        except Exception:
            pass
        # Удаляем сообщение-подсказку «введи качество», если есть
        if last_msg_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
            except Exception:
                pass
        # Удаляем сообщение пользователя с текстом качества (его попытку)
        if user_msg_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=user_msg_id)
            except Exception:
                pass

        # Обновляем качество в профиле
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
            if user:
                slots = _parse_qualities_to_slots(user.qualities)
                if 0 <= idx < len(slots):
                    slots[idx] = (emoji, new_text)
                    qualities_str = _build_qualities_from_slots(slots)
                    await UserRepository.update(session, user, qualities=qualities_str)
            break

        await state.clear()
        # Показываем обновлённый профиль новым сообщением
        await send_profile_view(callback.message, callback.from_user.id, state)
    except Exception as e:
        logger.error("Ошибка в profile_edit_quality_emoji_selected: %s", e, exc_info=True)
        _lang = "ru"
        async for s in get_session():
            u = await UserRepository.get_by_telegram_id(s, callback.from_user.id)
            if u:
                _lang = getattr(u, "language", None) or "ru"
            break
        await callback.answer(t(_lang, "edit_quality_emoji_error"), show_alert=True)


@router.message(ProfileEditStates.editing_quality_1)
async def process_edit_quality_1(message: Message, state: FSMContext) -> None:
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _process_edit_quality(message, state, t(lang, "quality_1_request"))


@router.message(ProfileEditStates.editing_quality_2)
async def process_edit_quality_2(message: Message, state: FSMContext) -> None:
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _process_edit_quality(message, state, t(lang, "quality_2_request"))


@router.message(ProfileEditStates.editing_quality_3)
async def process_edit_quality_3(message: Message, state: FSMContext) -> None:
    lang = "ru"
    async for s in get_session():
        u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break
    await _process_edit_quality(message, state, t(lang, "quality_3_request"))


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
