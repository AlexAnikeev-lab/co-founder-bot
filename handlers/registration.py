"""
Обработчики процесса регистрации
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

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
    get_accept_and_cancel_keyboard,
    get_learning_mode_button,
    get_cancel_button,
    get_skip_and_cancel_keyboard,
    get_contact_request_keyboard,
    get_language_keyboard,
)
from keyboards.test import get_post_registration_offer_keyboard, get_post_registration_minor_keyboard
from repositories.user_repository import UserRepository
from repositories.admin_archive_repository import AdminArchiveRepository
from config import Config
from utils.validators import (
    validate_age,
    parse_age_input,
    validate_name,
    validate_photo,
    validate_city,
    validate_short_description,
    validate_full_description,
    validate_single_quality,
    text_contains_emoji,
)
from utils.errors import handle_error, notify_admin_new_user
from utils.registration_photos import show_registration_step
from middlewares.delete_previous import protect_message

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
            lang=lang,
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
        get_cancel_button(lang),
        lang=lang,
    )
    if mid is not None:
        await state.update_data(last_bot_message_id=mid)
    else:
        if last_msg_id:
            try:
                await message.edit_text(birth_text, reply_markup=get_cancel_button(lang))
            except Exception:
                sent = await message.answer(birth_text, reply_markup=get_cancel_button(lang))
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(birth_text, reply_markup=get_cancel_button(lang))
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
            lang = data.get("language", "ru")
            await message.answer(t(lang, "error_start_required"))
            return

        parsed = parse_age_input(message.text)
        age = parsed[0] if parsed else None
        birth_date_iso = parsed[1].isoformat() if parsed and parsed[1] else None

        lang = data.get("language", "ru")
        birth_text = t(lang, "birth_date_question")
        if not age:
            err_caption = t(lang, "birth_date_error") + "\n\n" + birth_text
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "age", err_caption, get_cancel_button(lang), lang=lang,
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=err_caption,
                    reply_markup=get_cancel_button(lang),
                )
            return

        await state.update_data(age=age, birth_date=birth_date_iso)

        if age < config.MIN_AGE_FULL:
            learning_text = t(lang, "learning_mode_message")
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "learning_mode",
                learning_text, get_learning_mode_button(lang), lang=lang,
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=learning_text,
                    reply_markup=get_learning_mode_button(lang),
                )
            await state.update_data(is_minor=True)
        else:
            legal_text = t(lang, "legal_agreement")
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "legal",
                legal_text, get_accept_and_cancel_keyboard(lang), lang=lang,
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=legal_text,
                    reply_markup=get_accept_and_cancel_keyboard(lang),
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
                    message.bot, message.chat.id, last_msg_id, "age", err_caption, get_cancel_button(err_lang), lang=err_lang,
                )
                if mid2 is None:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err_caption,
                        reply_markup=get_cancel_button(err_lang),
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
                get_cancel_button(lang),
                lang=lang,
            )
            if mid is None:
                await callback.message.edit_text(
                    telegram_text,
                    reply_markup=get_cancel_button(lang),
                )
            await state.update_data(last_bot_message_id=callback.message.message_id)

            keyboard_msg = await callback.message.answer(
                t(lang, "contact_request_hint"),
                reply_markup=get_contact_request_keyboard(lang),
            )
            await state.update_data(keyboard_message_id=keyboard_msg.message_id)
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
            lang=lang,
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
            reply_markup=get_contact_request_keyboard(lang),
        )
        await state.update_data(keyboard_message_id=keyboard_msg.message_id)
        await state.set_state(RegistrationStates.waiting_for_telegram_access)

    except Exception as e:
        logger.error(f"Ошибка в accept_legal: {e}", exc_info=True)
        await handle_error(None, e, "accept_legal")


@router.message(RegistrationStates.waiting_for_telegram_access, F.contact)
async def process_telegram_access_contact(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка контакта с телефоном"""
    await process_telegram_access(message, state, phone=message.contact.phone_number, session=session)


@router.message(RegistrationStates.waiting_for_telegram_access)
async def process_telegram_access(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    phone: str = None,
) -> None:
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
                if await show_registration_step(message.bot, message.chat.id, last_msg_id, "telegram", err_text, None, lang=lang) is None:
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
                    reply_markup=get_contact_request_keyboard(lang),
                )
                await state.update_data(keyboard_message_id=keyboard_msg.message_id)
            return

        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if not user:
            user = await UserRepository.create(
                session,
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
        phone_number = phone or (message.contact.phone_number if message.contact else None)
        await UserRepository.update(
            session, user,
            age=data.get("age"),
            birth_date=data.get("birth_date"),
            is_minor=is_minor,
            phone=phone_number,
            language=data.get("language", "ru"),
        )

        name_text = t(lang, "name_request") if is_minor else t(lang, "name_request_profile")
        # Редактируем предыдущее сообщение (с «Allow access») в запрос имени, чтобы не слать второе сообщение
        mid2 = await show_registration_step(
            message.bot, message.chat.id, last_msg_id, "name", name_text, get_cancel_button(lang), lang=lang,
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2, keyboard_message_id=None)
        else:
            if last_msg_id:
                try:
                    await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
                except Exception:
                    pass
            sent = await message.answer(name_text, reply_markup=get_cancel_button(lang))
            await state.update_data(last_bot_message_id=sent.message_id, keyboard_message_id=None)
        await state.set_state(RegistrationStates.waiting_for_name)

    except Exception as e:
        logger.error(f"Ошибка в process_telegram_access: {e}", exc_info=True)
        await handle_error(None, e, "process_telegram_access")
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        err_lang = data.get("language", "ru")
        if last_msg_id:
            err_text = "❌ " + t(err_lang, "error_try_later")
            if await show_registration_step(message.bot, message.chat.id, last_msg_id, "telegram", err_text, get_cancel_button(err_lang), lang=err_lang) is None:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err_text,
                        reply_markup=get_cancel_button(err_lang),
                    )
                except Exception:
                    pass


@router.message(RegistrationStates.waiting_for_name)
async def process_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка имени"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        if not last_msg_id:
            lang = data.get("language", "ru")
            await message.answer(t(lang, "error_start_required"))
            return

        lang = data.get("language", "ru")
        if not validate_name(message.text):
            name_text = t(lang, "name_request") if data.get("is_minor") else t(lang, "name_request_profile")
            err_text = "❌ " + ("Имя: от 2 до 40 символов, только буквы." if lang == "ru" else "Name: 2–40 characters, letters only.") + "\n\n" + name_text
            if await show_registration_step(message.bot, message.chat.id, last_msg_id, "name", err_text, get_cancel_button(lang), lang=lang) is None:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err_text,
                        reply_markup=get_cancel_button(lang),
                    )
                except Exception:
                    pass
            return

        await state.update_data(name=message.text)
        is_minor = data.get("is_minor", False)

        lang = data.get("language", "ru")
        if is_minor:
            user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
            if user:
                await UserRepository.update(
                    session,
                    user,
                    name=message.text,
                    is_registered=True,
                    language=lang,
                )
                success_text = t(lang, "success_registration")
                mid2 = await show_registration_step(
                    message.bot,
                    message.chat.id,
                    last_msg_id,
                    "success",
                    success_text,
                    None,
                    lang=lang,
                )
                if mid2 is None:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=success_text,
                        reply_markup=get_post_registration_minor_keyboard(lang=lang),
                    )
                else:
                    await message.answer(
                        success_text,
                        reply_markup=get_post_registration_minor_keyboard(lang=lang),
                    )
                await state.clear()
        else:
            photo_text = t(lang, "photo_request")
            mid2 = await show_registration_step(
                message.bot, message.chat.id, last_msg_id, "photo",
                photo_text, get_cancel_button(lang), lang=lang,
            )
            if mid2 is None:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=photo_text,
                    reply_markup=get_cancel_button(lang),
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
                    reply_markup=get_cancel_button(lang)
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
                if await show_registration_step(message.bot, message.chat.id, last_msg_id, "photo", err_text, get_cancel_button(lang), lang=lang) is None:
                    try:
                        await message.bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=last_msg_id,
                            text=err_text,
                            reply_markup=get_cancel_button(lang),
                        )
                    except Exception:
                        pass
            return

        await state.update_data(photo_id=photo_id)

        city_text = t(lang, "city_request") + t(lang, "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, last_msg_id, "city",
            city_text, get_skip_and_cancel_keyboard(lang), lang=lang,
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2)
            protect_message(message.chat.id, mid2)
        elif last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=city_text,
                    reply_markup=get_skip_and_cancel_keyboard(lang),
                )
            except Exception:
                sent = await message.answer(city_text, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(last_bot_message_id=sent.message_id)
                protect_message(message.chat.id, sent.message_id)
        else:
            sent = await message.answer(city_text, reply_markup=get_skip_and_cancel_keyboard(lang))
            await state.update_data(last_bot_message_id=sent.message_id)
            protect_message(message.chat.id, sent.message_id)

        await state.set_state(RegistrationStates.waiting_for_city)

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
                    reply_markup=get_cancel_button(err_lang)
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
        if await show_registration_step(message.bot, message.chat.id, last_msg_id, "photo", err_text, get_cancel_button(lang), lang=lang) is None:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=err_text,
                    reply_markup=get_cancel_button(lang),
                )
            except Exception:
                pass


@router.message(RegistrationStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext) -> None:
    """Обработка города перед блоком сильных качеств."""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")

        if not validate_city(message.text):
            err = (
                ("❌ Укажи город от 2 до 40 символов." if lang == "ru" else "❌ Enter your city (2–40 characters).")
                + "\n\n"
                + t(lang, "city_request")
            )
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(lang),
                    )
                except Exception:
                    sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                    await state.update_data(last_bot_message_id=sent.message_id)
            else:
                sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(last_bot_message_id=sent.message_id)
            return

        if text_contains_emoji(message.text):
            await message.answer(t(lang, "city_no_emoji_in_text"))
            return

        await state.update_data(city=(message.text or "").strip())
        q1_text = t(lang, "quality_1_request") + t(lang, "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, last_msg_id, "quality_1",
            q1_text, get_skip_and_cancel_keyboard(lang), lang=lang,
        )
        if mid2 is not None:
            await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=[mid2])
            protect_message(message.chat.id, mid2)
        elif last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=q1_text,
                    reply_markup=get_skip_and_cancel_keyboard(lang),
                )
            except Exception:
                sent = await message.answer(q1_text, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=[sent.message_id])
                protect_message(message.chat.id, sent.message_id)
        else:
            sent = await message.answer(q1_text, reply_markup=get_skip_and_cancel_keyboard(lang))
            await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=[sent.message_id])
            protect_message(message.chat.id, sent.message_id)
        await state.set_state(RegistrationStates.waiting_for_quality_1)
    except Exception as e:
        logger.error(f"Ошибка в process_city: {e}", exc_info=True)
        await handle_error(None, e, "process_city")


@router.message(RegistrationStates.waiting_for_short_description)
async def process_short_description(message: Message, state: FSMContext) -> None:
    """Обработка краткого описания"""
    try:
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        # Защищаем шаговые сообщения описаний от автоудаления middleware
        step_ids = list(data.get("description_step_message_ids") or [])
        protect_targets = []
        if last_msg_id:
            protect_targets.append(last_msg_id)
        protect_targets.extend(step_ids)
        for mid in dict.fromkeys(protect_targets):
            try:
                protect_message(message.chat.id, int(mid))
            except Exception:
                pass
        
        lang = data.get("language", "ru")
        if not validate_short_description(message.text):
            invalid_ids = list(data.get("invalid_user_message_ids") or [])
            invalid_ids.append(message.message_id)
            await state.update_data(invalid_user_message_ids=invalid_ids)
            length = len((message.text or "").strip())
            err = (
                ("❌ Краткое описание: от 10 до 180 символов, сейчас у тебя: " if lang == "ru" else "❌ Short description: 10–180 characters, you now have: ")
                + str(length)
                + "."
            )
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(lang),
                    )
                except Exception:
                    sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                    await state.update_data(
                        last_bot_message_id=sent.message_id,
                        last_short_description_error_message_id=sent.message_id,
                    )
            else:
                sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(
                    last_bot_message_id=sent.message_id,
                    last_short_description_error_message_id=sent.message_id,
                )
            return

        # Удаляем неудачные попытки ввода описания
        for mid in (data.get("invalid_user_message_ids") or []):
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)
            except Exception:
                pass
        # Удаляем отдельное сообщение-ошибку, если отправляли ранее
        err_mid = data.get("last_short_description_error_message_id")
        if err_mid:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=err_mid)
            except Exception:
                pass
        # Как в шагах сильных сторон: оставляем сообщения, но снимаем с них кнопки
        step_ids = list(data.get("description_step_message_ids") or [])
        targets = []
        if last_msg_id:
            targets.append(last_msg_id)
        targets.extend(step_ids)
        for mid in dict.fromkeys(targets):
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=mid,
                    reply_markup=None,
                )
            except Exception:
                pass

        await state.update_data(short_description=message.text)
        full_text = t(lang, "full_description_request") + t(lang, "reg_skip_hint")
        mid2 = await show_registration_step(
            message.bot, message.chat.id, None, "full_desc",
            full_text, get_skip_and_cancel_keyboard(lang), lang=lang,
        )
        if mid2 is not None:
            mids = list(data.get("description_step_message_ids") or [])
            mids.append(mid2)
            await state.update_data(
                last_bot_message_id=mid2,
                last_short_description_error_message_id=None,
                description_step_message_ids=mids,
                invalid_user_message_ids=[],
            )
            protect_message(message.chat.id, mid2)
        else:
            sent = await message.answer(full_text, reply_markup=get_skip_and_cancel_keyboard(lang))
            mids = list(data.get("description_step_message_ids") or [])
            mids.append(sent.message_id)
            await state.update_data(
                last_bot_message_id=sent.message_id,
                last_short_description_error_message_id=None,
                description_step_message_ids=mids,
                invalid_user_message_ids=[],
            )
            protect_message(message.chat.id, sent.message_id)

        await state.set_state(RegistrationStates.waiting_for_full_description)

    except Exception as e:
        logger.error(f"Ошибка в process_short_description: {e}", exc_info=True)
        await handle_error(None, e, "process_short_description")


@router.message(RegistrationStates.waiting_for_full_description)
async def process_full_description(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка полного описания"""
    try:
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        # Защищаем шаговые сообщения описаний от автоудаления middleware
        step_ids = list(data.get("description_step_message_ids") or [])
        protect_targets = []
        if last_msg_id:
            protect_targets.append(last_msg_id)
        protect_targets.extend(step_ids)
        for mid in dict.fromkeys(protect_targets):
            try:
                protect_message(message.chat.id, int(mid))
            except Exception:
                pass
        
        lang = data.get("language", "ru")
        if not validate_full_description(message.text):
            invalid_ids = list(data.get("invalid_user_message_ids") or [])
            invalid_ids.append(message.message_id)
            await state.update_data(invalid_user_message_ids=invalid_ids)
            length = len((message.text or "").strip())
            err = (
                ("❌ Полное описание: от 20 до 500 символов, сейчас у тебя: " if lang == "ru" else "❌ Full description: 20–500 characters, you now have: ")
                + str(length)
                + "."
            )
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(lang),
                    )
                except Exception:
                    sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                    await state.update_data(
                        last_bot_message_id=sent.message_id,
                        last_full_description_error_message_id=sent.message_id,
                    )
            else:
                sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(
                    last_bot_message_id=sent.message_id,
                    last_full_description_error_message_id=sent.message_id,
                )
            return

        # Удаляем неудачные попытки ввода полного описания
        for mid in (data.get("invalid_user_message_ids") or []):
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)
            except Exception:
                pass
        # Удаляем отдельное сообщение-ошибку, если было
        err_mid = data.get("last_full_description_error_message_id")
        if err_mid:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=err_mid)
            except Exception:
                pass
        # Оставляем сообщения шага, но убираем с них кнопки
        step_ids = list(data.get("description_step_message_ids") or [])
        targets = []
        if last_msg_id:
            targets.append(last_msg_id)
        targets.extend(step_ids)
        for mid in dict.fromkeys(targets):
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=mid,
                    reply_markup=None,
                )
            except Exception:
                pass

        await state.update_data(full_description=message.text, invalid_user_message_ids=[])
        data = await state.get_data()
        await _complete_registration(message, state, data, session=session)

    except Exception as e:
        logger.error(f"Ошибка в process_full_description: {e}", exc_info=True)
        await handle_error(None, e, "process_full_description")


def _build_qualities_string(data: dict) -> str | None:
    """Собрать строку качеств в формате emoji|text (по одной строке на качество). Если смайлик не выбран — используется •."""
    lines = []
    for i in (1, 2, 3):
        text = (data.get(f"quality_{i}") or "").strip()
        emoji = (data.get(f"quality_{i}_emoji") or "").strip() or "•"
        if text:
            lines.append(f"{emoji}|{text}")
    return "\n".join(lines) if lines else None


async def _complete_registration(
    message: Message,
    state: FSMContext,
    data: dict,
    *,
    session: AsyncSession,
    user_id: int | None = None,
) -> None:
    """Сохранить профиль в БД и показать экран завершения регистрации. user_id задаётся при вызове из callback."""
    uid = user_id if user_id is not None else message.from_user.id
    qualities = _build_qualities_string(data)
    user = await UserRepository.get_by_telegram_id(session, uid)
    if user:
        await UserRepository.update(
            session,
            user,
            name=data.get("name"),
            photo_id=data.get("photo_id"),
            short_description=data.get("short_description"),
            full_description=data.get("full_description"),
            city=data.get("city"),
            qualities=qualities,
            is_registered=True,
            language=data.get("language", "ru"),
        )
        await session.refresh(user)
        try:
            await AdminArchiveRepository.create_from_user(session, user)
        except Exception as e:
            logger.exception("Ошибка сохранения в архив админа: %s", e)
        try:
            await notify_admin_new_user(
                message.bot,
                user.name or "",
                user.telegram_id,
                user.username,
            )
        except Exception as e:
            logger.exception("Ошибка уведомления о новом пользователе: %s", e)
        lang = data.get("language", "ru")
        success_text = t(lang, "success_registration_offer_test")
        # По требованию UX: после полной регистрации отправляем отдельное новое сообщение,
        # не редактируя предыдущие шаги регистрации.
        await message.answer(
            success_text,
            reply_markup=get_post_registration_offer_keyboard(lang=lang),
        )
        await state.clear()


@router.callback_query(F.data == "reg_skip")
async def reg_skip(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
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
            mid2 = await show_registration_step(
                bot, msg.chat.id, last_msg_id, "full_desc", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    mids = list((await state.get_data()).get("description_step_message_ids") or [])
                    mids.append(sent.message_id)
                    await state.update_data(last_bot_message_id=sent.message_id, description_step_message_ids=mids)
                    protect_message(msg.chat.id, sent.message_id)
            else:
                mids = list((await state.get_data()).get("description_step_message_ids") or [])
                mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, description_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_full_description)
            return
        if current == RegistrationStates.waiting_for_full_description.state:
            await state.update_data(full_description=None)
            data = await state.get_data()
            await _complete_registration(
                msg,
                state,
                data,
                session=session,
                user_id=callback.from_user.id,
            )
            return
        if current == RegistrationStates.waiting_for_quality_1.state:
            await state.update_data(quality_1=None)
            text = t(lang, "quality_2_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, last_msg_id, "quality_2", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                    mids.append(sent.message_id)
                    await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=mids)
                    protect_message(msg.chat.id, sent.message_id)
            else:
                mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                if not mids or mids[-1] != mid2:
                    mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_quality_2)
            return
        if current == RegistrationStates.waiting_for_city.state:
            await state.update_data(city=None)
            text = t(lang, "quality_1_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, last_msg_id, "quality_1", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=[sent.message_id])
                    protect_message(msg.chat.id, sent.message_id)
            else:
                await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=[mid2])
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_quality_1)
            return
        if current == RegistrationStates.waiting_for_quality_1_emoji.state:
            await state.update_data(quality_1_emoji="•")
            target_mid = _get_last_quality_step_message_id(data) or last_msg_id
            text = t(lang, "quality_2_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, target_mid, "quality_2", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                    mids.append(sent.message_id)
                    await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=mids)
                    protect_message(msg.chat.id, sent.message_id)
            else:
                mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                if not mids or mids[-1] != mid2:
                    mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_quality_2)
            return
        if current == RegistrationStates.waiting_for_quality_2.state:
            await state.update_data(quality_2=None)
            text = t(lang, "quality_3_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, last_msg_id, "quality_3", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                    mids.append(sent.message_id)
                    await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=mids)
                    protect_message(msg.chat.id, sent.message_id)
            else:
                mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                if not mids or mids[-1] != mid2:
                    mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_quality_3)
            return
        if current == RegistrationStates.waiting_for_quality_2_emoji.state:
            await state.update_data(quality_2_emoji="•")
            target_mid = _get_last_quality_step_message_id(data) or last_msg_id
            text = t(lang, "quality_3_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, target_mid, "quality_3", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                    mids.append(sent.message_id)
                    await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=mids)
                    protect_message(msg.chat.id, sent.message_id)
            else:
                mids = list((await state.get_data()).get("quality_step_message_ids") or [])
                if not mids or mids[-1] != mid2:
                    mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_quality_3)
            return
        if current == RegistrationStates.waiting_for_quality_3.state:
            await state.update_data(quality_3=None)
            text = t(lang, "short_description_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, last_msg_id, "short_desc", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    mids = list((await state.get_data()).get("description_step_message_ids") or [])
                    mids.append(sent.message_id)
                    await state.update_data(last_bot_message_id=sent.message_id, description_step_message_ids=mids)
                    protect_message(msg.chat.id, sent.message_id)
            else:
                mids = list((await state.get_data()).get("description_step_message_ids") or [])
                mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, description_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_short_description)
            return
        if current == RegistrationStates.waiting_for_quality_3_emoji.state:
            await state.update_data(quality_3_emoji="•")
            target_mid = _get_last_quality_step_message_id(data) or last_msg_id
            text = t(lang, "short_description_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, target_mid, "short_desc", text, get_skip_and_cancel_keyboard(lang), lang=lang
            )
            if mid2 is None:
                try:
                    await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                except Exception:
                    sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                    mids = list((await state.get_data()).get("description_step_message_ids") or [])
                    mids.append(sent.message_id)
                    await state.update_data(last_bot_message_id=sent.message_id, description_step_message_ids=mids)
                    protect_message(msg.chat.id, sent.message_id)
            else:
                mids = list((await state.get_data()).get("description_step_message_ids") or [])
                mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, description_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            await state.set_state(RegistrationStates.waiting_for_short_description)
    except Exception as e:
        logger.error(f"Ошибка в reg_skip: {e}", exc_info=True)
        await handle_error(None, e, "reg_skip")
    

async def _cleanup_quality_warnings_and_attempts(bot, chat_id: int, data: dict) -> None:
    """Удалить все предупреждения и неудачные попытки ввода (по id из state)."""
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


def _get_last_quality_step_message_id(data: dict) -> int | None:
    """Вернуть последний id карточки шага сильной стороны (обычно сообщение с фото)."""
    mids = list(data.get("quality_step_message_ids") or [])
    if not mids:
        return None
    try:
        return int(mids[-1])
    except Exception:
        return None


@router.message(RegistrationStates.waiting_for_quality_1)
async def process_quality_1(message: Message, state: FSMContext) -> None:
    """Обработка первого качества. Эмодзи в тексте запрещены; при валидном вводе удаляем предупреждения и неудачные попытки."""
    try:
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")
        if not validate_single_quality(message.text):
            invalid_ids = list(data.get("invalid_user_message_ids") or [])
            invalid_ids.append(message.message_id)
            await state.update_data(invalid_user_message_ids=invalid_ids)
            length = len((message.text or "").strip())
            err = (
                ("❌ Укажи качество от 2 до 40 символов, сейчас у тебя: " if lang == "ru" else "❌ Enter 2–40 characters, you now have: ")
                + str(length)
                + "."
            )
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(lang),
                    )
                except Exception:
                    sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                    await state.update_data(
                        last_quality_error_message_id=sent.message_id,
                    )
            else:
                sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(
                    last_quality_error_message_id=sent.message_id,
                )
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
        await _cleanup_quality_warnings_and_attempts(message.bot, message.chat.id, data)
        step_ids = list(data.get("quality_step_message_ids") or [])
        targets = []
        if last_msg_id:
            targets.append(last_msg_id)
        targets.extend(step_ids)
        for mid in dict.fromkeys(targets):
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=mid,
                    reply_markup=None,
                )
            except Exception:
                pass
        await state.update_data(
            quality_1=message.text.strip(),
            invalid_user_message_ids=[],
            last_warning_message_id=None,
            last_quality_error_message_id=None,
        )
        text = t(lang, "quality_emoji_prompt")
        from keyboards.quality_emoji import get_quality_emoji_keyboard
        kb = get_quality_emoji_keyboard(1, prefix="reg", lang=lang)
        # Показываем выбор смайлика отдельным сообщением, не трогая карточку с «Сильная сторона №1»
        await message.answer(text, reply_markup=kb)
        await state.set_state(RegistrationStates.waiting_for_quality_1_emoji)
    except Exception as e:
        logger.error(f"Ошибка в process_quality_1: {e}", exc_info=True)
        await handle_error(None, e, "process_quality_1")


@router.message(RegistrationStates.waiting_for_quality_2)
async def process_quality_2(message: Message, state: FSMContext) -> None:
    """Обработка второго качества. Эмодзи в тексте запрещены; при валидном вводе удаляем предупреждения и неудачные попытки."""
    try:
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")
        if not validate_single_quality(message.text):
            invalid_ids = list(data.get("invalid_user_message_ids") or [])
            invalid_ids.append(message.message_id)
            await state.update_data(invalid_user_message_ids=invalid_ids)
            length = len((message.text or "").strip())
            err = (
                ("❌ Укажи качество от 2 до 40 символов, сейчас у тебя: " if lang == "ru" else "❌ Enter 2–40 characters, you now have: ")
                + str(length)
                + "."
            )
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(lang),
                    )
                except Exception:
                    sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                    await state.update_data(
                        last_quality_error_message_id=sent.message_id,
                    )
            else:
                sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(
                    last_quality_error_message_id=sent.message_id,
                )
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
        await _cleanup_quality_warnings_and_attempts(message.bot, message.chat.id, data)
        step_ids = list(data.get("quality_step_message_ids") or [])
        targets = []
        if last_msg_id:
            targets.append(last_msg_id)
        targets.extend(step_ids)
        for mid in dict.fromkeys(targets):
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=mid,
                    reply_markup=None,
                )
            except Exception:
                pass
        await state.update_data(
            quality_2=message.text.strip(),
            invalid_user_message_ids=[],
            last_warning_message_id=None,
            last_quality_error_message_id=None,
        )
        text = t(lang, "quality_emoji_prompt")
        from keyboards.quality_emoji import get_quality_emoji_keyboard
        kb = get_quality_emoji_keyboard(2, prefix="reg", lang=lang)
        # Тоже отдельное сообщение, карточка «Сильная сторона №2» остаётся
        await message.answer(text, reply_markup=kb)
        await state.set_state(RegistrationStates.waiting_for_quality_2_emoji)
    except Exception as e:
        logger.error(f"Ошибка в process_quality_2: {e}", exc_info=True)
        await handle_error(None, e, "process_quality_2")


@router.message(RegistrationStates.waiting_for_quality_3)
async def process_quality_3(message: Message, state: FSMContext) -> None:
    """Обработка третьего качества. Эмодзи в тексте запрещены; при валидном вводе удаляем предупреждения и неудачные попытки."""
    try:
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        lang = data.get("language", "ru")
        if not validate_single_quality(message.text):
            invalid_ids = list(data.get("invalid_user_message_ids") or [])
            invalid_ids.append(message.message_id)
            await state.update_data(invalid_user_message_ids=invalid_ids)
            length = len((message.text or "").strip())
            err = (
                ("❌ Укажи качество от 2 до 40 символов, сейчас у тебя: " if lang == "ru" else "❌ Enter 2–40 characters, you now have: ")
                + str(length)
                + "."
            )
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=err,
                        reply_markup=get_skip_and_cancel_keyboard(lang),
                    )
                except Exception:
                    sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                    await state.update_data(
                        last_quality_error_message_id=sent.message_id,
                    )
            else:
                sent = await message.answer(err, reply_markup=get_skip_and_cancel_keyboard(lang))
                await state.update_data(
                    last_quality_error_message_id=sent.message_id,
                )
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
        await _cleanup_quality_warnings_and_attempts(message.bot, message.chat.id, data)
        step_ids = list(data.get("quality_step_message_ids") or [])
        targets = []
        if last_msg_id:
            targets.append(last_msg_id)
        targets.extend(step_ids)
        for mid in dict.fromkeys(targets):
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=message.chat.id,
                    message_id=mid,
                    reply_markup=None,
                )
            except Exception:
                pass
        await state.update_data(
            quality_3=message.text.strip(),
            invalid_user_message_ids=[],
            last_warning_message_id=None,
            last_quality_error_message_id=None,
        )
        text = t(lang, "quality_emoji_prompt")
        from keyboards.quality_emoji import get_quality_emoji_keyboard
        kb = get_quality_emoji_keyboard(3, prefix="reg", lang=lang)
        await message.answer(text, reply_markup=kb)
        await state.set_state(RegistrationStates.waiting_for_quality_3_emoji)
    except Exception as e:
        logger.error(f"Ошибка в process_quality_3: {e}", exc_info=True)
        await handle_error(None, e, "process_quality_3")


@router.callback_query(F.data.regexp(r"^reg_q[123]_emoji:.+"))
async def reg_quality_emoji_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор смайлика для качества в регистрации: сохранить и перейти к следующему шагу."""
    await callback.answer()
    from keyboards.quality_emoji import QUALITY_EMOJI_LIST
    try:
        # callback.data = "reg_q1_emoji:🔥"
        parts = callback.data.split("_emoji:", 1)
        if len(parts) != 2:
            return
        step_str = parts[0].replace("reg_q", "")
        if step_str not in ("1", "2", "3"):
            return
        step = int(step_str)
        emoji = parts[1].strip()
        if emoji not in QUALITY_EMOJI_LIST:
            return
        await state.update_data(**{f"quality_{step}_emoji": emoji})
        data = await state.get_data()
        lang = data.get("language", "ru")
        msg = callback.message
        bot = callback.bot

        # Защищаем все карточки «Сильная сторона ...» от автоудаления middleware
        quality_step_ids = list(data.get("quality_step_message_ids") or [])
        for mid in quality_step_ids:
            try:
                protect_message(msg.chat.id, int(mid))
            except Exception:
                pass

        # Удаляем только сообщение с выбором смайлика
        try:
            await msg.delete()
        except Exception:
            pass

        if step == 1:
            text = t(lang, "quality_2_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, None, "quality_2",
                text, get_skip_and_cancel_keyboard(lang), lang=lang,
            )
            if mid2 is not None:
                quality_step_ids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=quality_step_ids)
                protect_message(msg.chat.id, mid2)
            else:
                sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                quality_step_ids.append(sent.message_id)
                await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=quality_step_ids)
                protect_message(msg.chat.id, sent.message_id)
            await state.set_state(RegistrationStates.waiting_for_quality_2)
        elif step == 2:
            text = t(lang, "quality_3_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, None, "quality_3",
                text, get_skip_and_cancel_keyboard(lang), lang=lang,
            )
            if mid2 is not None:
                quality_step_ids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, quality_step_message_ids=quality_step_ids)
                protect_message(msg.chat.id, mid2)
            else:
                sent = await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard(lang))
                quality_step_ids.append(sent.message_id)
                await state.update_data(last_bot_message_id=sent.message_id, quality_step_message_ids=quality_step_ids)
                protect_message(msg.chat.id, sent.message_id)
            await state.set_state(RegistrationStates.waiting_for_quality_3)
        else:
            short_text = t(lang, "short_description_request") + t(lang, "reg_skip_hint")
            mid2 = await show_registration_step(
                bot, msg.chat.id, None, "short_desc",
                short_text, get_skip_and_cancel_keyboard(lang), lang=lang,
            )
            if mid2 is not None:
                mids = list(data.get("description_step_message_ids") or [])
                mids.append(mid2)
                await state.update_data(last_bot_message_id=mid2, description_step_message_ids=mids)
                protect_message(msg.chat.id, mid2)
            else:
                sent = await msg.answer(short_text, reply_markup=get_skip_and_cancel_keyboard(lang))
                mids = list(data.get("description_step_message_ids") or [])
                mids.append(sent.message_id)
                await state.update_data(last_bot_message_id=sent.message_id, description_step_message_ids=mids)
                protect_message(msg.chat.id, sent.message_id)
            await state.set_state(RegistrationStates.waiting_for_short_description)
    except Exception as e:
        logger.error(f"Ошибка в reg_quality_emoji_selected: {e}", exc_info=True)
        await handle_error(None, e, "reg_quality_emoji_selected")


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
