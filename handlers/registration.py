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
from keyboards.common import (
    get_accept_button, 
    get_learning_mode_button, 
    get_cancel_button,
    get_skip_and_cancel_keyboard,
    get_contact_request_keyboard
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

logger = logging.getLogger(__name__)
router = Router()
config = Config()


async def ask_age(message: Message, state: FSMContext) -> None:
    """Запрос возраста — редактируем сообщение бота"""
    await message.edit_text(
        "✏️ <b>Сколько тебе лет?</b>\n\n<i>Укажи свой возраст цифрами.</i>",
        reply_markup=get_cancel_button()
    )
    await state.update_data(last_bot_message_id=message.message_id)
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
        
        if not age:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text="❌ Пожалуйста, укажи корректный возраст (от 1 до 120 лет).\n\n✏️ <b>Сколько тебе лет?</b>",
                reply_markup=get_cancel_button()
            )
            return
        
        await state.update_data(age=age)
        
        # Редактируем сообщение бота
        if age < config.MIN_AGE_FULL:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=LEARNING_MODE_MESSAGE,
                reply_markup=get_learning_mode_button()
            )
            await state.update_data(is_minor=True)
        else:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=LEGAL_AGREEMENT,
                reply_markup=get_accept_button()
            )
            await state.set_state(RegistrationStates.waiting_for_legal_agreement)
            await state.update_data(is_minor=False)
            
    except Exception as e:
        logger.error(f"Ошибка в process_age: {e}", exc_info=True)
        await handle_error(None, e, "process_age")
        if last_msg_id := (await state.get_data()).get("last_bot_message_id"):
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Произошла ошибка. Попробуй ещё раз.\n\n✏️ <b>Сколько тебе лет?</b>",
                    reply_markup=get_cancel_button()
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
            # Редактируем сообщение бота
            await callback.message.edit_text(
                TELEGRAM_ACCESS_REQUEST,
                reply_markup=get_cancel_button()
            )
            await state.update_data(last_bot_message_id=callback.message.message_id)
            await state.set_state(RegistrationStates.waiting_for_telegram_access)
            
    except Exception as e:
        logger.error(f"Ошибка в start_learning_mode: {e}", exc_info=True)
        await handle_error(None, e, "start_learning_mode")


@router.callback_query(F.data == "accept_legal")
async def accept_legal(callback: CallbackQuery, state: FSMContext) -> None:
    """Принятие юридического соглашения"""
    try:
        await callback.answer()
        
        # Редактируем сообщение с правилами на запрос контакта
        await callback.message.edit_text(
            TELEGRAM_PHONE_ACCESS_REQUEST,
            reply_markup=None  # Inline-клавиатуру убираем
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
        
        # Отправляем отдельное сообщение только с Reply-клавиатурой для контакта
        keyboard_msg = await callback.message.answer(
            "📱",
            reply_markup=get_contact_request_keyboard()
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

        if not is_minor and not phone and not message.contact:
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Пожалуйста, отправь контакт кнопкой ниже.\n\n" + TELEGRAM_PHONE_ACCESS_REQUEST,
                        reply_markup=None
                    )
                    # Отправляем клавиатуру заново
                    keyboard_msg = await message.answer(
                        "📱",
                        reply_markup=get_contact_request_keyboard()
                    )
                    await state.update_data(keyboard_message_id=keyboard_msg.message_id)
                except Exception:
                    await message.answer(
                        "❌ Пожалуйста, отправь свой контакт, нажав на кнопку ниже.",
                        reply_markup=get_contact_request_keyboard()
                    )
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
            await UserRepository.update(session, user, age=data.get("age"), is_minor=is_minor, phone=phone_number)

            # Редактируем основное сообщение на запрос имени
            name_text = NAME_REQUEST if is_minor else NAME_REQUEST_PROFILE
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=name_text,
                        reply_markup=get_cancel_button()
                    )
                except Exception:
                    sent = await message.answer(name_text, reply_markup=get_cancel_button())
                    await state.update_data(last_bot_message_id=sent.message_id)
            else:
                sent = await message.answer(name_text, reply_markup=get_cancel_button())
                await state.update_data(last_bot_message_id=sent.message_id)
            
            await state.update_data(keyboard_message_id=None)  # Очищаем ID клавиатуры
            await state.set_state(RegistrationStates.waiting_for_name)
            break

    except Exception as e:
        logger.error(f"Ошибка в process_telegram_access: {e}", exc_info=True)
        await handle_error(None, e, "process_telegram_access")
        last_msg_id = (await state.get_data()).get("last_bot_message_id")
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Произошла ошибка. Попробуй ещё раз.",
                    reply_markup=get_cancel_button()
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

        if not validate_name(message.text):
            try:
                name_text = NAME_REQUEST if data.get("is_minor") else NAME_REQUEST_PROFILE
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Имя: от 2 до 50 символов, только буквы.\n\n" + name_text,
                    reply_markup=get_cancel_button()
                )
            except Exception:
                pass
            return

        await state.update_data(name=message.text)
        is_minor = data.get("is_minor", False)

        if is_minor:
            async for session in get_session():
                user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
                if user:
                    await UserRepository.update(session, user, name=message.text, is_registered=True)
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=SUCCESS_REGISTRATION,
                        reply_markup=get_main_menu_keyboard(is_minor=True)
                    )
                    await state.clear()
                break
        else:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text=PHOTO_REQUEST,
                reply_markup=get_cancel_button()
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

        if not validate_photo(photo_id):
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Не удалось обработать фото. Попробуй ещё раз.\n\n" + PHOTO_REQUEST,
                        reply_markup=get_cancel_button()
                    )
                except Exception:
                    pass
            return

        await state.update_data(photo_id=photo_id)
        
        # Переходим к запросу краткого описания (можно пропустить)
        short_text = SHORT_DESCRIPTION_REQUEST + REG_SKIP_HINT
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=short_text,
                    reply_markup=get_skip_and_cancel_keyboard()
                )
            except Exception:
                sent = await message.answer(short_text, reply_markup=get_skip_and_cancel_keyboard())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(short_text, reply_markup=get_skip_and_cancel_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)
        
        await state.set_state(RegistrationStates.waiting_for_short_description)

    except Exception as e:
        logger.error(f"Ошибка в process_photo: {e}", exc_info=True)
        await handle_error(None, e, "process_photo")
        if last_msg_id := (await state.get_data()).get("last_bot_message_id"):
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Произошла ошибка. Попробуй ещё раз.\n\n" + PHOTO_REQUEST,
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
    if last_msg_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_msg_id,
                text="❌ Пожалуйста, отправь фото.\n\n" + PHOTO_REQUEST,
                reply_markup=get_cancel_button()
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
        
        if not validate_short_description(message.text):
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Краткое описание: от 10 до 200 символов.\n\n" + SHORT_DESCRIPTION_REQUEST + REG_SKIP_HINT,
                        reply_markup=get_skip_and_cancel_keyboard()
                    )
                except Exception:
                    pass
            return

        await state.update_data(short_description=message.text)
        full_text = FULL_DESCRIPTION_REQUEST + REG_SKIP_HINT
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=full_text,
                    reply_markup=get_skip_and_cancel_keyboard()
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
        
        if not validate_full_description(message.text):
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Полное описание: от 20 до 1000 символов.\n\n" + FULL_DESCRIPTION_REQUEST + REG_SKIP_HINT,
                        reply_markup=get_skip_and_cancel_keyboard()
                    )
                except Exception:
                    pass
            return

        await state.update_data(full_description=message.text)
        # Переходим к первому качеству
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=QUALITY_1_REQUEST + REG_SKIP_HINT,
                    reply_markup=get_skip_and_cancel_keyboard()
                )
            except Exception:
                sent = await message.answer(QUALITY_1_REQUEST + REG_SKIP_HINT, reply_markup=get_skip_and_cancel_keyboard())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(QUALITY_1_REQUEST + REG_SKIP_HINT, reply_markup=get_skip_and_cancel_keyboard())
            await state.update_data(last_bot_message_id=sent.message_id)
        
        await state.set_state(RegistrationStates.waiting_for_quality_1)

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
                is_registered=True
            )
            await session.refresh(user)
            try:
                await AdminArchiveRepository.create_from_user(session, user)
            except Exception as e:
                logger.exception("Ошибка сохранения в архив админа: %s", e)
            last_msg_id = data.get("last_bot_message_id")
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text=SUCCESS_REGISTRATION_OFFER_TEST,
                        reply_markup=get_post_registration_offer_keyboard()
                    )
                except Exception:
                    await message.answer(
                        SUCCESS_REGISTRATION_OFFER_TEST,
                        reply_markup=get_post_registration_offer_keyboard()
                    )
            else:
                await message.answer(
                    SUCCESS_REGISTRATION_OFFER_TEST,
                    reply_markup=get_post_registration_offer_keyboard()
                )
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

        if current == RegistrationStates.waiting_for_short_description.state:
            await state.update_data(short_description=None)
            text = FULL_DESCRIPTION_REQUEST + REG_SKIP_HINT
            try:
                await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
            except Exception:
                await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_full_description)
            return
        if current == RegistrationStates.waiting_for_full_description.state:
            await state.update_data(full_description=None)
            text = QUALITY_1_REQUEST + REG_SKIP_HINT
            try:
                await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
            except Exception:
                await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_quality_1)
            return
        if current == RegistrationStates.waiting_for_quality_1.state:
            await state.update_data(quality_1=None)
            text = QUALITY_2_REQUEST + REG_SKIP_HINT
            try:
                await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
            except Exception:
                await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_quality_2)
            return
        if current == RegistrationStates.waiting_for_quality_2.state:
            await state.update_data(quality_2=None)
            text = QUALITY_3_REQUEST + REG_SKIP_HINT
            try:
                await msg.edit_text(text, reply_markup=get_skip_and_cancel_keyboard())
            except Exception:
                await msg.answer(text, reply_markup=get_skip_and_cancel_keyboard())
            await state.set_state(RegistrationStates.waiting_for_quality_3)
            return
        if current == RegistrationStates.waiting_for_quality_3.state:
            await state.update_data(quality_3=None)
            data = await state.get_data()
            await _complete_registration(msg, state, data, user_id=callback.from_user.id)
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
        if not validate_single_quality(message.text):
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Укажи качество от 2 до 50 символов.\n\n" + QUALITY_1_REQUEST + REG_SKIP_HINT,
                        reply_markup=get_skip_and_cancel_keyboard()
                    )
                except Exception:
                    pass
            return
        await state.update_data(quality_1=message.text.strip())
        text = QUALITY_2_REQUEST + REG_SKIP_HINT
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=text,
                    reply_markup=get_skip_and_cancel_keyboard()
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
        if not validate_single_quality(message.text):
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Укажи качество от 2 до 50 символов.\n\n" + QUALITY_2_REQUEST + REG_SKIP_HINT,
                        reply_markup=get_skip_and_cancel_keyboard()
                    )
                except Exception:
                    pass
            return
        await state.update_data(quality_2=message.text.strip())
        text = QUALITY_3_REQUEST + REG_SKIP_HINT
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=text,
                    reply_markup=get_skip_and_cancel_keyboard()
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
    """Обработка третьего качества и завершение регистрации"""
    try:
        try:
            await message.delete()
        except Exception:
            pass
        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        if not validate_single_quality(message.text):
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Укажи качество от 2 до 50 символов.\n\n" + QUALITY_3_REQUEST + REG_SKIP_HINT,
                        reply_markup=get_skip_and_cancel_keyboard()
                    )
                except Exception:
                    pass
            return
        await state.update_data(quality_3=message.text.strip())
        data = await state.get_data()
        await _complete_registration(message, state, data)
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
    await state.clear()
    try:
        await callback.message.edit_text("❌ Регистрация отменена.")
    except Exception:
        await callback.message.answer("❌ Регистрация отменена.")


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
