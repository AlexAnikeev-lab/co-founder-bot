"""
Обработчики процесса регистрации
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.registration import RegistrationStates
from texts.messages import (
    LEGAL_AGREEMENT,
    TELEGRAM_ACCESS_REQUEST,
    TELEGRAM_PHONE_ACCESS_REQUEST,
    NAME_REQUEST,
    NAME_REQUEST_PROFILE,
    PHOTO_REQUEST,
    SHORT_DESCRIPTION_REQUEST,
    FULL_DESCRIPTION_REQUEST,
    QUALITY_1_REQUEST,
    QUALITY_2_REQUEST,
    QUALITY_3_REQUEST,
    REG_SKIP_HINT,
    LEARNING_MODE_MESSAGE,
    SUCCESS_REGISTRATION,
    SUCCESS_REGISTRATION_OFFER_TEST,
)
from texts.i18n import t
from keyboards.common import (
    get_accept_button,
    get_learning_mode_button,
    get_cancel_button,
    get_skip_and_cancel_keyboard,
    get_contact_request_keyboard,
    get_language_keyboard,
)
from keyboards.menu import get_main_menu_keyboard
from keyboards.test import get_post_registration_offer_keyboard
from repositories.user_repository import UserRepository
from repositories.admin_archive_repository import AdminArchiveRepository
from repositories.database import get_session
from config import Config
from utils.validators import (
    validate_age, 
    validate_name, 
    validate_photo,
    validate_short_description,
    validate_full_description,
    validate_single_quality,
)
from utils.errors import handle_error
from utils.registration_photos import show_registration_step

logger = logging.getLogger(__name__)
router = Router()
config = Config()


async def ask_language(message: Message, state: FSMContext) -> None:
    """Первый шаг регистрации: выбор языка (Русский / English)."""
    text = t("ru", "language_question")
    last_msg_id = getattr(message, "message_id", None)
    if last_msg_id:
        try:
            await message.edit_text(text, reply_markup=get_language_keyboard())
        except Exception:
            sent = await message.answer(text, reply_markup=get_language_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)
    else:
        sent = await message.answer(text, reply_markup=get_language_keyboard())
        await state.update_data(last_bot_message_id=sent.message_id)
    await state.set_state(RegistrationStates.waiting_for_language)


@router.callback_query(F.data.in_({"set_lang_ru", "set_lang_en"}))
async def set_language(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохранение языка: если с самого начала — показать приветствие; иначе — запрос даты рождения."""
    await callback.answer()
    lang = "ru" if callback.data == "set_lang_ru" else "en"
    await state.update_data(language=lang)
    data = await state.get_data()
    if data.get("from_start"):
        await state.update_data(from_start=False)
        from keyboards.common import get_start_button
        from utils.registration_photos import show_registration_step
        mid = await show_registration_step(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            "welcome_1",
            t(lang, "welcome_1"),
            get_start_button(lang),
        )
        if mid is not None:
            await state.update_data(last_bot_message_id=mid)
        else:
            try:
                await callback.message.delete()
            except Exception:
                pass
            sent = await callback.message.answer(
                t(lang, "welcome_1"),
                reply_markup=get_start_button(lang),
            )
            await state.update_data(last_bot_message_id=sent.message_id)
        return
    await ask_age(callback.message, state)


async def ask_age(message: Message, state: FSMContext) -> None:
    """Запрос даты рождения — текст по выбранному языку."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    birth_text = t(lang, "birth_date_question")
    last_msg_id = getattr(message, "message_id", None) or data.get("last_bot_message_id")
    mid = await show_registration_step(
        message.bot,
        message.chat.id,
        last_msg_id,
        "age",
        birth_text,
        get_cancel_button(),
    )
    if mid is not None:
        await state.update_data(last_bot_message_id=mid)
    else:
        if last_msg_id:
            try:
                await message.edit_text(birth_text, reply_markup=get_cancel_button())
            except Exception:
                sent = await message.answer(birth_text, reply_markup=get_cancel_button())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(birth_text, reply_markup=get_cancel_button())
            await state.update_data(last_bot_message_id=sent.message_id)
    await state.set_state(RegistrationStates.waiting_for_age)


@router.message(RegistrationStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext) -> None:
    """Обработка возраста"""
    try:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        if not last_msg_id:
            await message.answer("❌ Ошибка. Начни с /start")
            return

        age = validate_age(message.text)

        lang = data.get("language", "ru")
        birth_text = t(lang, "birth_date_question")
        if not age:
            err_caption = t(lang, "birth_date_error") + "\n\n" + birth_text
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "age", err_caption, get_cancel_button()
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=err_caption,
                    reply_markup=get_cancel_button(),
                )
            return

        await state.update_data(age=age)

        if age < config.MIN_AGE_FULL:
            learning_text = t(lang, "learning_mode_message")
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "learning_mode",
                learning_text, get_learning_mode_button(),
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=learning_text,
                    reply_markup=get_learning_mode_button(),
                )
            await state.update_data(is_minor=True)
        else:
            legal_text = t(lang, "legal_agreement")
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "legal",
                legal_text, get_accept_button(lang),
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=legal_text,
                    reply_markup=get_accept_button(lang),
                )
            await state.set_state(RegistrationStates.waiting_for_legal_agreement)
            await state.update_data(is_minor=False)
            
    except Exception as e:
        logger.error(f"Ошибка в process_age: {e}", exc_info=True)
        await handle_error(None, e, "process_age")
        if last_msg_id := (await state.get_data()).get("last_bot_message_id"):
            try:
                err_lang = (await state.get_data()).get("language", "ru")
                err_caption = "❌ " + ("Произошла ошибка. Попробуй ещё раз." if err_lang == "ru" else "Something went wrong. Try again.") + "\n\n" + t(err_lang, "birth_date_question")
                mid2 = await show_registration_step(
                    message.bot, message.chat.id, last_msg_id, "age", err_caption, get_cancel_button()
                )
                if mid2 is None:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err_caption,
                        reply_markup=get_cancel_button(),
                    )
            except Exception:
                pass


@router.callback_query(F.data == "learning_mode")
async def start_learning_mode(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало обучающего режима для несовершеннолетних"""
    try:
        await callback.answer()
        
        data = await state.get_data()
        age = data.get("age")
        
        if age and age < config.MIN_AGE_FULL:
            lang = data.get("language", "ru")
            telegram_text = t(lang, "telegram_access_request")
            mid = await show_registration_step(
                callback.bot,
                callback.message.chat.id,
                callback.message.message_id,
                "telegram",
                telegram_text,
                get_cancel_button(),
            )
            if mid is None:
                await callback.message.edit_text(
                    telegram_text,
                    reply_markup=get_cancel_button(),
                )
            await state.update_data(last_bot_message_id=callback.message.message_id)
            await state.set_state(RegistrationStates.waiting_for_telegram_access)
            
    except Exception as e:
        logger.error(f"Ошибка в start_learning_mode: {e}", exc_info=True)
        await handle_error(None, e, "start_learning_mode")


@router.callback_query(F.data == "accept_legal")
async def accept_legal(callback: CallbackQuery, state: FSMContext) -> None:
    """Принятие юридического соглашения — переход к запросу контакта: картинка с подписью «Allow access», одно сообщение с подсказкой и кнопкой."""
    try:
        await callback.answer()
        data = await state.get_data()
        lang = data.get("language", "ru")
        caption_text = t(lang, "telegram_phone_access_request")

        mid = await show_registration_step(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            "telegram",
            caption_text,
            None,
        )
        if mid is not None:
            await state.update_data(last_bot_message_id=mid)
        else:
            try:
                await callback.message.edit_text(caption_text, reply_markup=None)
            except Exception:
                pass
            await state.update_data(last_bot_message_id=callback.message.message_id)

        keyboard_msg = await callback.message.answer(
            t(lang, "contact_request_hint"),
            reply_markup=get_contact_request_keyboard(),
        )
        await state.update_data(keyboard_message_id=keyboard_msg.message_id)
        await state.set_state(RegistrationStates.waiting_for_telegram_access)

    except Exception as e:
        logger.error(f"Ошибка в accept_legal: {e}", exc_info=True)
        await handle_error(None, e, "accept_legal")


@router.message(RegistrationStates.waiting_for_telegram_access, F.contact)
async def process_telegram_access_contact(message: Message, state: FSMContext) -> None:
    """Обработка контакта с телефоном"""
    await process_telegram_access(message, state, phone=message.contact.phone_number)


@router.message(RegistrationStates.waiting_for_telegram_access)
async def process_telegram_access(message: Message, state: FSMContext, phone: str = None) -> None:
    """Обработка доступа к Telegram данным"""
    try:
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        is_minor = data.get("is_minor", False)
        last_msg_id = data.get("last_bot_message_id")
        keyboard_msg_id = data.get("keyboard_message_id")

        # Удаляем сообщение с Reply-клавиатурой (если есть)
        if keyboard_msg_id:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=keyboard_msg_id)
            except Exception:
                pass

        lang = data.get("language", "ru")
        if not is_minor and not phone and not message.contact:
            if last_msg_id:
                err_text = "❌ " + t(lang, "contact_please_send") + "\n\n" + t(lang, "telegram_phone_access_request")
                if await show_registration_step(message.bot, message.chat.id, last_msg_id, "telegram", err_text, None) is None:
                    try:
                        await message.bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=last_msg_id,
                            text=err_text,
                            reply_markup=None,
                        )
                    except Exception:
                        pass
                keyboard_msg = await message.answer(
                    "📱",
                    reply_markup=get_contact_request_keyboard(),
                )
                await state.update_data(keyboard_message_id=keyboard_msg.message_id)
            return

        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(
                session,
                message.from_user.id
            )
            if not user:
                user = await UserRepository.create(
                    session,
                    telegram_id=message.from_user.id,
                    username=message.from_user.username
                )
            phone_number = phone or (message.contact.phone_number if message.contact else None)
            await UserRepository.update(
                session, user,
                age=data.get("age"), is_minor=is_minor, phone=phone_number,
                language=data.get("language", "ru"),
            )

            name_text = t(lang, "name_request") if is_minor else t(lang, "name_request_profile")
            # Редактируем предыдущее сообщение (с «Allow access») в запрос имени, чтобы не слать второе сообщение
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "name", name_text, get_cancel_button(),
            )
            if mid2 is not None:
                await state.update_data(last_bot_message_id=mid2, keyboard_message_id=None)
            else:
                if last_msg_id:
                    try:
                        await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
                    except Exception:
                        pass
                sent = await message.answer(name_text, reply_markup=get_cancel_button())
                await state.update_data(last_bot_message_id=sent.message_id, keyboard_message_id=None)
            await state.set_state(RegistrationStates.waiting_for_name)
            break

    except Exception as e:
        logger.error(f"Ошибка в process_telegram_access: {e}", exc_info=True)
        await handle_error(None, e, "process_telegram_access")
        last_msg_id = (await state.get_data()).get("last_bot_message_id")
        if last_msg_id:
            err_text = "❌ Произошла ошибка. Попробуй ещё раз."
            if await show_registration_step(message.bot, message.chat.id, last_msg_id, "telegram", err_text, get_cancel_button()) is None:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err_text,
                        reply_markup=get_cancel_button(),
                    )
                except Exception:
                    pass


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    """Обработка имени"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        if not last_msg_id:
            await message.answer("❌ Ошибка. Начни с /start")
            return

        lang = data.get("language", "ru")
        if not validate_name(message.text):
            name_text = t(lang, "name_request") if data.get("is_minor") else t(lang, "name_request_profile")
            err_text = "❌ " + ("Имя: от 2 до 50 символов, только буквы." if lang == "ru" else "Name: 2–50 characters, letters only.") + "\n\n" + name_text
            if await show_registration_step(message.bot, message.chat.id, last_msg_id, "name", err_text, get_cancel_button()) is None:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err_text,
                        reply_markup=get_cancel_button(),
                    )
                except Exception:
                    pass
            return

        await state.update_data(name=message.text)
        is_minor = data.get("is_minor", False)

        lang = data.get("language", "ru")
        if is_minor:
            async for session in get_session():
                user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
                if user:
                    await UserRepository.update(session, user, name=message.text, is_registered=True, language=lang)
                    success_text = t(lang, "success_registration")
                    mid2 = await show_registration_step(
                        message.bot, message.chat.id, last_msg_id, "success",
                        success_text, None,
                    )
                    if mid2 is None:
                        await message.bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=last_msg_id,
                            text=success_text,
                            reply_markup=get_main_menu_keyboard(is_minor=True, lang=lang),
                        )
                    else:
                        await message.answer("🏠", reply_markup=get_main_menu_keyboard(is_minor=True, lang=lang))
                    await state.clear()
                break
        else:
            photo_text = t(lang, "photo_request")
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "photo",
                photo_text, get_cancel_button(),
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=photo_text,
                    reply_markup=get_cancel_button(),
                )
            await state.set_state(RegistrationStates.waiting_for_photo)

    except Exception as e:
        logger.error(f"Ошибка в process_name: {e}", exc_info=True)
        await handle_error(None, e, "process_name")
        if last_msg_id := (await state.get_data()).get("last_bot_message_id"):
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Произошла ошибка. Попробуй ещё раз.",
                    reply_markup=get_cancel_button()
                )
            except Exception:
                pass


@router.message(RegistrationStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext) -> None:
    """Обработка фото"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")
        if not validate_photo(photo_id):
            if last_msg_id:
                err_text = "❌ " + ("Не удалось обработать фото. Попробуй ещё раз." if lang == "ru" else "Could not process photo. Try again.") + "\n\n" + t(lang, "photo_request")
                if await show_registration_step(message.bot, message.chat.id, last_msg_id, "photo", err_text, get_cancel_button()) is None:
                    try:
                        await message.bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=last_msg_id,
                            text=err_text,
                            reply_markup=get_cancel_button(),
                        )
                    except Exception:
                        pass
            return

        await state.update_data(photo_id=photo_id)

        q1_text = t(lang, "quality_1_request") + t(lang, "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, last_msg_id, "quality_1",
            q1_text, get_skip_and_cancel_keyboard(),
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2)
        elif last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=q1_text,
                    reply_markup=get_skip_and_cancel_keyboard(),
                )
            except Exception:
                sent = await message.answer(q1_text, reply_markup=get_skip_and_cancel_keyboard())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(q1_text, reply_markup=get_skip_and_cancel_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)

        await state.set_state(RegistrationStates.waiting_for_quality_1)

    except Exception as e:
        logger.error(f"Ошибка в process_photo: {e}", exc_info=True)
        await handle_error(None, e, "process_photo")
        err_lang = (await state.get_data()).get("language", "ru")
        if last_msg_id := (await state.get_data()).get("last_bot_message_id"):
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=("❌ Произошла ошибка. Попробуй ещё раз.\n\n" if err_lang == "ru" else "❌ Something went wrong. Try again.\n\n") + t(err_lang, "photo_request"),
                    reply_markup=get_cancel_button()
                )
            except Exception:
                pass


@router.message(RegistrationStates.waiting_for_photo)
async def process_photo_invalid(message: Message, state: FSMContext) -> None:
    """Обработка некорректного фото"""
    try:
        await message.delete()
    except Exception:
        pass
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    lang = data.get("language", "ru")
    if last_msg_id:
        err_text = "❌ " + ("Пожалуйста, отправь фото." if lang == "ru" else "Please send a photo.") + "\n\n" + t(lang, "photo_request")
        if await show_registration_step(message.bot, message.chat.id, last_msg_id, "photo", err_text, get_cancel_button()) is None:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=err_text,
                    reply_markup=get_cancel_button(),
                )
            except Exception:
                pass


@router.message(RegistrationStates.waiting_for_short_description)
async def process_short_description(message: Message, state: FSMContext) -> None:
    """Обработка краткого описания"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        
        lang = data.get("language", "ru")
        if not validate_short_description(message.text):
            if last_msg_id:
                try:
                    err = "❌ " + ("Краткое описание: от 10 до 200 символов." if lang == "ru" else "Short description: 10–200 characters.") + "\n\n" + t(lang, "short_description_request") + t(lang, "reg_skip_hint")
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(),
                    )
                except Exception:
                    pass
            return

        await state.update_data(short_description=message.text)
        full_text = t(lang, "full_description_request") + t(lang, "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, last_msg_id, "full_desc",
            full_text, get_skip_and_cancel_keyboard(),
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2)
        elif last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=full_text,
                    reply_markup=get_skip_and_cancel_keyboard(),
                )
            except Exception:
                sent = await message.answer(full_text, reply_markup=get_skip_and_cancel_keyboard())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(full_text, reply_markup=get_skip_and_cancel_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)

        await state.set_state(RegistrationStates.waiting_for_full_description)

    except Exception as e:
        logger.error(f"Ошибка в process_short_description: {e}", exc_info=True)
        await handle_error(None, e, "process_short_description")


@router.message(RegistrationStates.waiting_for_full_description)
async def process_full_description(message: Message, state: FSMContext) -> None:
    """Обработка полного описания"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        
        lang = data.get("language", "ru")
        if not validate_full_description(message.text):
            if last_msg_id:
                try:
                    err = "❌ " + ("Полное описание: от 20 до 1000 символов." if lang == "ru" else "Full description: 20–1000 characters.") + "\n\n" + t(lang, "full_description_request") + t(lang, "reg_skip_hint")
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(),
                    )
                except Exception:
                    pass
            return

        await state.update_data(full_description=message.text)
        data = await state.get_data()
        await _complete_registration(message, state, data)

    except Exception as e:
        logger.error(f"Ошибка в process_full_description: {e}", exc_info=True)
        await handle_error(None, e, "process_full_description")


def _build_qualities_string(data: dict) -> str | None:
    """Собрать строку качеств из quality_1, quality_2, quality_3 или None."""
    q1 = (data.get("quality_1") or "").strip()
    q2 = (data.get("quality_2") or "").strip()
    q3 = (data.get("quality_3") or "").strip()
    parts = [q for q in (q1, q2, q3) if q]
    return ", ".join(parts) if parts else None


async def _complete_registration(
    message: Message, state: FSMContext, data: dict, *, user_id: int | None = None
) -> None:
    """Сохранить профиль в БД и показать экран завершения регистрации. user_id задаётся при вызове из callback."""
    uid = user_id if user_id is not None else message.from_user.id
    qualities = _build_qualities_string(data)
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, uid)
        if user:
            await UserRepository.update(
                session,
                user,
                name=data.get("name"),
                photo_id=data.get("photo_id"),
                short_description=data.get("short_description"),
                full_description=data.get("full_description"),
                qualities=qualities,
                is_registered=True,
                language=data.get("language", "ru"),
            )
            await session.refresh(user)
            try:
                await AdminArchiveRepository.create_from_user(session, user)
            except Exception as e:
                logger.exception("Ошибка сохранения в архив админа: %s", e)
            last_msg_id = data.get("last_bot_message_id")
            lang = data.get("language", "ru")
            success_text = t(lang, "success_registration_offer_test")
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "success",
                success_text,
                get_post_registration_offer_keyboard(lang=lang),
            )
            if mid2 is not None:
                pass
            elif last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=success_text,
                        reply_markup=get_post_registration_offer_keyboard(lang=lang),
                    )
                except Exception:
                    await message.answer(success_text, reply_markup=get_post_registration_offer_keyboard(lang=lang))
            else:
                await message.answer(success_text, reply_markup=get_post_registration_offer_keyboard(lang=lang))
            await state.clear()
        break


@router.callback_query(F.data == "reg_skip")
async def reg_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки «Пропустить» на шагах: краткое/полное описание, качества 1–3."""
    await callback.answer()
    try:
        current = await state.get_state()
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        msg = callback.message
        bot = callback.bot

        lang = (await state.get_data()).get("language", "ru")
        if current == RegistrationStates.waiting_for_short_description.state:
            await state.update_data(short_description=None)
            text = t(lang, "full_description_request") + t(lang, "reg_skip_hint")
            if await show_registration_step(bot, msg.chat.id, last_msg_id, "full_desc", text, get_skip_and_cancel_keyboard()) is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
                except Exception:
                    await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_full_description)
            return
        if current == RegistrationStates.waiting_for_full_description.state:
            await state.update_data(full_description=None)
            data = await state.get_data()
            await _complete_registration(msg, state, data, user_id=callback.from_user.id)
            return
        if current == RegistrationStates.waiting_for_quality_1.state:
            await state.update_data(quality_1=None)
            text = t(lang, "quality_2_request") + t(lang, "reg_skip_hint")
            if await show_registration_step(bot, msg.chat.id, last_msg_id, "quality_2", text, get_skip_and_cancel_keyboard()) is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
                except Exception:
                    await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_quality_2)
            return
        if current == RegistrationStates.waiting_for_quality_2.state:
            await state.update_data(quality_2=None)
            text = t(lang, "quality_3_request") + t(lang, "reg_skip_hint")
            if await show_registration_step(bot, msg.chat.id, last_msg_id, "quality_3", text, get_skip_and_cancel_keyboard()) is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
                except Exception:
                    await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_quality_3)
            return
        if current == RegistrationStates.waiting_for_quality_3.state:
            await state.update_data(quality_3=None)
            text = t(lang, "short_description_request") + t(lang, "reg_skip_hint")
            if await show_registration_step(bot, msg.chat.id, last_msg_id, "short_desc", text, get_skip_and_cancel_keyboard()) is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
                except Exception:
                    await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_short_description)
    except Exception as e:
        logger.error(f"Ошибка в reg_skip: {e}", exc_info=True)
        await handle_error(None, e, "reg_skip")


@router.message(RegistrationStates.waiting_for_quality_1)
async def process_quality_1(message: Message, state: FSMContext) -> None:
    """Обработка первого качества"""
    try:
        try:
            await message.delete()
        except Exception:
            pass
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")
        if not validate_single_quality(message.text):
            if last_msg_id:
                try:
                    err = "❌ " + ("Укажи качество от 2 до 50 символов." if lang == "ru" else "Enter 2–50 characters.") + "\n\n" + t(lang, "quality_1_request") + t(lang, "reg_skip_hint")
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(),
                    )
                except Exception:
                    pass
            return
        await state.update_data(quality_1=message.text.strip())
        text = t(lang, "quality_2_request") + t(lang, "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, last_msg_id, "quality_2",
            text, get_skip_and_cancel_keyboard(),
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2)
        elif last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=text,
                    reply_markup=get_skip_and_cancel_keyboard(),
                )
            except Exception:
                sent = await message.answer(text, reply_markup=get_skip_and_cancel_keyboard())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)
        await state.set_state(RegistrationStates.waiting_for_quality_2)
    except Exception as e:
        logger.error(f"Ошибка в process_quality_1: {e}", exc_info=True)
        await handle_error(None, e, "process_quality_1")


@router.message(RegistrationStates.waiting_for_quality_2)
async def process_quality_2(message: Message, state: FSMContext) -> None:
    """Обработка второго качества"""
    try:
        try:
            await message.delete()
        except Exception:
            pass
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")
        if not validate_single_quality(message.text):
            if last_msg_id:
                try:
                    err = "❌ " + ("Укажи качество от 2 до 50 символов." if lang == "ru" else "Enter 2–50 characters.") + "\n\n" + t(lang, "quality_2_request") + t(lang, "reg_skip_hint")
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(),
                    )
                except Exception:
                    pass
            return
        await state.update_data(quality_2=message.text.strip())
        text = t(lang, "quality_3_request") + t(lang, "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, last_msg_id, "quality_3",
            text, get_skip_and_cancel_keyboard(),
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2)
        elif last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=text,
                    reply_markup=get_skip_and_cancel_keyboard(),
                )
            except Exception:
                sent = await message.answer(text, reply_markup=get_skip_and_cancel_keyboard())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)
        await state.set_state(RegistrationStates.waiting_for_quality_3)
    except Exception as e:
        logger.error(f"Ошибка в process_quality_2: {e}", exc_info=True)
        await handle_error(None, e, "process_quality_2")


@router.message(RegistrationStates.waiting_for_quality_3)
async def process_quality_3(message: Message, state: FSMContext) -> None:
    """Обработка третьего качества, далее — краткое описание"""
    try:
        try:
            await message.delete()
        except Exception:
            pass
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")
        if not validate_single_quality(message.text):
            if last_msg_id:
                try:
                    err = "❌ " + ("Укажи качество от 2 до 50 символов." if lang == "ru" else "Enter 2–50 characters.") + "\n\n" + t(lang, "quality_3_request") + t(lang, "reg_skip_hint")
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(),
                    )
                except Exception:
                    pass
            return
        await state.update_data(quality_3=message.text.strip())
        data = await state.get_data()
        short_text = t(data.get("language", "ru"), "short_description_request") + t(data.get("language", "ru"), "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, data.get("last_bot_message_id"), "short_desc",
            short_text, get_skip_and_cancel_keyboard(),
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2)
        elif data.get("last_bot_message_id"):
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=data["last_bot_message_id"],
                    text=short_text,
                    reply_markup=get_skip_and_cancel_keyboard(),
                )
            except Exception:
                sent = await message.answer(short_text, reply_markup=get_skip_and_cancel_keyboard())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(short_text, reply_markup=get_skip_and_cancel_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)
        await state.set_state(RegistrationStates.waiting_for_short_description)
    except Exception as e:
        logger.error(f"Ошибка в process_quality_3: {e}", exc_info=True)
        await handle_error(None, e, "process_quality_3")


@router.callback_query(F.data == "cancel")
async def cancel_registration(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена: в редактировании профиля — вернуть экран профиля (редактируем сообщение); в регистрации — отмена регистрации."""
    await callback.answer()
    current = await state.get_state()
    if current and "ProfileEditStates" in (current or ""):
        await state.clear()
        await state.update_data(in_profile=True, profile_screen="profile")
        from handlers.profile import send_profile_view
        await send_profile_view(
            callback.message,
            callback.from_user.id,
            state,
            edit_message_id=callback.message.message_id,
        )
        return
    data = await state.get_data()
    lang = data.get("language", "ru")
    await state.clear()
    cancelled_text = t(lang, "registration_cancelled")
    try:
        await callback.message.edit_text(cancelled_text)
    except Exception:
        await callback.message.answer(cancelled_text)


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
