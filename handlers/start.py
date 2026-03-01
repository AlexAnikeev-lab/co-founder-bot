"""
Обработчики команды /start и начального экрана
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from aiogram.types import FSInputFile

from keyboards.common import get_welcome_step2_button
from texts.i18n import t
from repositories.user_repository import UserRepository, User
from repositories.database import get_session
from config import get_registration_photo_path, get_registration_photo_file_id
from utils.errors import handle_error
from utils.registration_photos import show_registration_step

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработка команды /start"""
    try:
        # Очистка состояния
        await state.clear()
        
        # Проверка существования пользователя
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(
                session, 
                message.from_user.id
            )
            
            if user and user.is_registered:
                from handlers.common import show_main_menu
                lang = getattr(user, "language", None) or "ru"
                await show_main_menu(message, user.is_minor, lang)
            else:
                # Новый пользователь — сначала выбор языка, потом приветствие
                await state.update_data(from_start=True)
                from handlers.registration import ask_language
                await ask_language(message, state)
            break
            
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}", exc_info=True)
        await handle_error(None, e, "cmd_start")
        lang = "ru"
        async for s in get_session():
            u = await UserRepository.get_by_telegram_id(s, message.from_user.id)
            if u:
                lang = getattr(u, "language", None) or "ru"
            break
        await message.answer("❌ " + t(lang, "error_try_later"))


@router.callback_query(F.data == "welcome_gas")
async def welcome_gas(callback: CallbackQuery, state: FSMContext) -> None:
    """Второй экран приветствия после нажатия «Газ» — текст на выбранном языке."""
    try:
        await callback.answer()
        if not callback.message:
            return
        data = await state.get_data()
        lang = data.get("language", "ru")
        welcome2_text = t(lang, "welcome_2")
        photo = get_registration_photo_file_id("welcome_2", lang=lang) or (
            FSInputFile(p) if (p := get_registration_photo_path("welcome_2", lang=lang)) else None
        )
        if photo:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo,
                caption=welcome2_text,
                reply_markup=get_welcome_step2_button(lang),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                welcome2_text,
                reply_markup=get_welcome_step2_button(lang),
            )
    except Exception as e:
        logger.error(f"Ошибка в welcome_gas: {e}", exc_info=True)
        await handle_error(None, e, "welcome_gas")
        if callback.message:
            data = await state.get_data()
            lang = data.get("language", "ru")
            await callback.message.answer("❌ " + t(lang, "error_try_later"))


@router.callback_query(F.data == "start_registration")
async def start_registration(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало регистрации (после «Круто!») — язык уже выбран, переходим к дате рождения."""
    try:
        await callback.answer()
        from handlers.registration import ask_age
        await ask_age(callback.message, state)
    except Exception as e:
        logger.error(f"Ошибка в start_registration: {e}", exc_info=True)
        await handle_error(None, e, "start_registration")
        if callback.message:
            data = await state.get_data()
            lang = data.get("language", "ru")
            await callback.message.answer("❌ " + t(lang, "error_try_later"))


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
