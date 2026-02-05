"""
Общие обработчики (главное меню, навигация)
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.menu import get_main_menu_keyboard
from repositories.user_repository import UserRepository
from repositories.database import get_session
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(message: Message, is_minor: bool = False) -> None:
    """Показать главное меню"""
    await message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_menu_keyboard(is_minor=is_minor)
    )


@router.message(F.text == "🏠 Главное меню")
@router.callback_query(F.data == "main_menu")
async def cmd_main_menu(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки Главное меню"""
    try:
        # Определяем тип события
        if isinstance(event, CallbackQuery):
            await event.answer()
            message = event.message
            user_id = event.from_user.id
        else:
            message = event
            user_id = event.from_user.id
        
        await state.clear()
        
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)
            
            if user:
                await message.answer(
                    "🏠 <b>Главное меню</b>",
                    reply_markup=get_main_menu_keyboard(is_minor=user.is_minor)
                )
            else:
                await message.answer("❌ Ты ещё не зарегистрирован. Используй /start")
            break
            
    except Exception as e:
        logger.error(f"Ошибка в cmd_main_menu: {e}", exc_info=True)
        await handle_error(None, e, "cmd_main_menu")


@router.callback_query(F.data == "back")
async def cmd_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки Назад"""
    await callback.answer()
    await state.clear()
    await cmd_main_menu(callback, state)


@router.callback_query(F.data == "back_to_start")
async def cmd_back_to_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Назад из обучающего режима — в главное меню"""
    await callback.answer()
    await state.clear()
    await cmd_main_menu(callback, state)


@router.message(F.text == "ℹ️ Информация")
@router.callback_query(F.data == "info")
async def cmd_info(event: Message | CallbackQuery) -> None:
    """Информация о боте"""
    # Определяем тип события
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id
    
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            is_minor = user.is_minor
        break
    
    await message.answer(
        "ℹ️ <b>Информация</b>\n\n"
        "Co-founder Bot - это место для поиска партнёров и единомышленников.\n\n"
        "Здесь ты можешь:\n"
        "• Пройти тесты и узнать о себе больше\n"
        "• Получить доступ к обучающим материалам\n"
        "• Найти партнёров для проектов и стартапов\n"
        "• Собрать команду для реализации идей",
        reply_markup=get_main_menu_keyboard(is_minor=is_minor)
    )


@router.callback_query(F.data == "bot_instruction")
async def cmd_bot_instruction(callback: CallbackQuery) -> None:
    """Инструкция по использованию бота"""
    await callback.answer()
    
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            is_minor = user.is_minor
        break
    
    await callback.message.answer(
        "📖 <b>Инструкция по боту</b>\n\n"
        "1. Заполни свой профиль\n"
        "2. Пройди тесты для лучшего понимания себя\n"
        "3. Изучи обучающие материалы\n"
        "4. Найди партнёров через раздел Знакомства\n"
        "5. Общайся и создавай проекты вместе!",
        reply_markup=get_main_menu_keyboard(is_minor=is_minor)
    )


@router.message(F.text == "🤝 Партнеры")
@router.callback_query(F.data == "dating")
async def cmd_dating(event: Message | CallbackQuery) -> None:
    """Раздел Партнеры"""
    # Определяем тип события
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id
    
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            is_minor = user.is_minor
        break
    
    await message.answer(
        "🤝 <b>Поиск партнеров</b>\n\n"
        "Здесь ты сможешь находить партнёров по интересам и целям.\n\n"
        "Функция в разработке.",
        reply_markup=get_main_menu_keyboard(is_minor=is_minor)
    )


@router.message(F.text == "⭐ Co-founder Premium")
@router.callback_query(F.data == "premium")
async def cmd_premium(event: Message | CallbackQuery) -> None:
    """Co-founder Premium"""
    # Определяем тип события
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id
    
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            is_minor = user.is_minor
        break
    
    await message.answer(
        "⭐ <b>Co-founder Premium</b>\n\n"
        "Расширенные возможности в разработке.",
        reply_markup=get_main_menu_keyboard(is_minor=is_minor)
    )


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
