"""
Обработчики команды /start и начального экрана
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from texts.messages import WELCOME_MESSAGE
from keyboards.common import get_start_button
from repositories.user_repository import UserRepository, User
from repositories.database import get_session
from utils.errors import handle_error

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
                # Пользователь уже зарегистрирован - показываем главное меню
                from handlers.common import show_main_menu
                await show_main_menu(message, user.is_minor)
            else:
                # Новый пользователь - показываем приветствие
                await message.answer(
                    WELCOME_MESSAGE,
                    reply_markup=get_start_button()
                )
            break
            
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}", exc_info=True)
        await handle_error(None, e, "cmd_start")
        await message.answer("❌ Произошла ошибка. Попробуй ещё раз.")


@router.callback_query(F.data == "start_registration")
async def start_registration(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса регистрации"""
    try:
        await callback.answer()
        
        # Переход к запросу возраста
        from handlers.registration import ask_age
        await ask_age(callback.message, state)
        
    except Exception as e:
        logger.error(f"Ошибка в start_registration: {e}", exc_info=True)
        await handle_error(None, e, "start_registration")
        await callback.message.answer("❌ Произошла ошибка. Попробуй ещё раз.")


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
