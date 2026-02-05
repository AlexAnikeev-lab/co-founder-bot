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
    QUALITIES_REQUEST,
    LEARNING_MODE_MESSAGE,
    SUCCESS_REGISTRATION
)
from keyboards.common import (
    get_accept_button, 
    get_learning_mode_button, 
    get_cancel_button,
    get_contact_request_keyboard
)
from keyboards.menu import get_main_menu_keyboard
from repositories.user_repository import UserRepository
from repositories.database import get_session
from config import Config
from utils.validators import (
    validate_age, 
    validate_name, 
    validate_photo,
    validate_short_description,
    validate_full_description,
    validate_qualities
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
        
        # Переходим к запросу краткого описания
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=SHORT_DESCRIPTION_REQUEST,
                    reply_markup=get_cancel_button()
                )
            except Exception:
                sent = await message.answer(SHORT_DESCRIPTION_REQUEST, reply_markup=get_cancel_button())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(SHORT_DESCRIPTION_REQUEST, reply_markup=get_cancel_button())
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
                        text="❌ Краткое описание: от 10 до 200 символов.\n\n" + SHORT_DESCRIPTION_REQUEST,
                        reply_markup=get_cancel_button()
                    )
                except Exception:
                    pass
            return

        await state.update_data(short_description=message.text)
        
        # Переходим к запросу полного описания
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=FULL_DESCRIPTION_REQUEST,
                    reply_markup=get_cancel_button()
                )
            except Exception:
                sent = await message.answer(FULL_DESCRIPTION_REQUEST, reply_markup=get_cancel_button())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(FULL_DESCRIPTION_REQUEST, reply_markup=get_cancel_button())
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
                        text="❌ Полное описание: от 20 до 1000 символов.\n\n" + FULL_DESCRIPTION_REQUEST,
                        reply_markup=get_cancel_button()
                    )
                except Exception:
                    pass
            return

        await state.update_data(full_description=message.text)
        
        # Переходим к запросу качеств
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text=QUALITIES_REQUEST,
                    reply_markup=get_cancel_button()
                )
            except Exception:
                sent = await message.answer(QUALITIES_REQUEST, reply_markup=get_cancel_button())
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            sent = await message.answer(QUALITIES_REQUEST, reply_markup=get_cancel_button())
            await state.update_data(last_bot_message_id=sent.message_id)
        
        await state.set_state(RegistrationStates.waiting_for_qualities)

    except Exception as e:
        logger.error(f"Ошибка в process_full_description: {e}", exc_info=True)
        await handle_error(None, e, "process_full_description")


@router.message(RegistrationStates.waiting_for_qualities)
async def process_qualities(message: Message, state: FSMContext) -> None:
    """Обработка качеств"""
    try:
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        last_msg_id = data.get("last_bot_message_id")
        
        if not validate_qualities(message.text):
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="❌ Укажи ровно 3 качества через запятую.\n\n" + QUALITIES_REQUEST,
                        reply_markup=get_cancel_button()
                    )
                except Exception:
                    pass
            return

        # Сохраняем все данные в БД
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
            if user:
                await UserRepository.update(
                    session,
                    user,
                    name=data.get("name"),
                    photo_id=data.get("photo_id"),
                    short_description=data.get("short_description"),
                    full_description=data.get("full_description"),
                    qualities=message.text,
                    is_registered=True
                )
                if last_msg_id:
                    try:
                        await message.bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=last_msg_id,
                            text=SUCCESS_REGISTRATION,
                            reply_markup=get_main_menu_keyboard(is_minor=False)
                        )
                    except Exception:
                        await message.answer(SUCCESS_REGISTRATION, reply_markup=get_main_menu_keyboard(is_minor=False))
                await state.clear()
            break

    except Exception as e:
        logger.error(f"Ошибка в process_qualities: {e}", exc_info=True)
        await handle_error(None, e, "process_qualities")
        if last_msg_id := (await state.get_data()).get("last_bot_message_id"):
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Произошла ошибка. Попробуй ещё раз.\n\n" + QUALITIES_REQUEST,
                    reply_markup=get_cancel_button()
                )
            except Exception:
                pass


@router.callback_query(F.data == "cancel")
async def cancel_registration(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена регистрации — редактируем сообщение бота"""
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text("❌ Регистрация отменена.")
    except Exception:
        await callback.message.answer("❌ Регистрация отменена.")


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
