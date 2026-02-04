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


@router.callback_query(F.data == "main_menu")
async def cmd_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки Главное меню"""
    try:
        # Проверяем, не находимся ли мы уже в главном меню (до callback.answer())
        current_text = callback.message.text or (callback.message.caption or "")
        if "🏠 <b>Главное меню</b>" in current_text:
            await callback.answer("🏠 Вы уже в главном меню", show_alert=False)
            return
        
        await callback.answer()
        await state.clear()
        
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(
                session,
                callback.from_user.id
            )
            
            if user:
                try:
                    await callback.message.edit_text(
                        "🏠 <b>Главное меню</b>",
                        reply_markup=get_main_menu_keyboard(is_minor=user.is_minor)
                    )
                except Exception:
                    # Если не удалось отредактировать (например, фото), отправляем новое
                    await callback.message.answer(
                        "🏠 <b>Главное меню</b>",
                        reply_markup=get_main_menu_keyboard(is_minor=user.is_minor)
                    )
            else:
                try:
                    await callback.message.edit_text("❌ Ты ещё не зарегистрирован. Используй /start")
                except Exception:
                    await callback.message.answer("❌ Ты ещё не зарегистрирован. Используй /start")
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


@router.callback_query(F.data == "info")
async def cmd_info(callback: CallbackQuery) -> None:
    """Информация о боте"""
    # Проверяем, не находимся ли мы уже в этом разделе (до callback.answer())
    current_text = callback.message.text or (callback.message.caption or "")
    if "ℹ️ <b>Информация</b>" in current_text:
        await callback.answer("ℹ️ Вы уже в разделе Информация", show_alert=False)
        return
    
    await callback.answer()
    
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            is_minor = user.is_minor
        break
    try:
        await callback.message.edit_text(
            "ℹ️ <b>Информация</b>\n\n"
            "Co-founder Bot - это место для поиска партнёров и единомышленников.\n\n"
            "Здесь ты можешь:\n"
            "• Пройти тесты и узнать о себе больше\n"
            "• Получить доступ к обучающим материалам\n"
            "• Найти партнёров для проектов и стартапов\n"
            "• Собрать команду для реализации идей",
            reply_markup=get_main_menu_keyboard(is_minor=is_minor)
        )
    except Exception:
        # Проверяем, не стало ли сообщение уже таким же после ошибки
        current_text_after = callback.message.text or (callback.message.caption or "")
        if "ℹ️ <b>Информация</b>" not in current_text_after:
            await callback.message.answer(
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
    # Проверяем, не находимся ли мы уже в этом разделе (до callback.answer())
    current_text = callback.message.text or (callback.message.caption or "")
    if "📖 <b>Инструкция по боту</b>" in current_text:
        await callback.answer("📖 Вы уже в разделе Инструкция", show_alert=False)
        return
    
    await callback.answer()
    
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            is_minor = user.is_minor
        break
    try:
        await callback.message.edit_text(
            "📖 <b>Инструкция по боту</b>\n\n"
            "1. Заполни свой профиль\n"
            "2. Пройди тесты для лучшего понимания себя\n"
            "3. Изучи обучающие материалы\n"
            "4. Найди партнёров через раздел Знакомства\n"
            "5. Общайся и создавай проекты вместе!",
            reply_markup=get_main_menu_keyboard(is_minor=is_minor)
        )
    except Exception:
        current_text_after = callback.message.text or (callback.message.caption or "")
        if "📖 <b>Инструкция по боту</b>" not in current_text_after:
            await callback.message.answer(
                "📖 <b>Инструкция по боту</b>\n\n"
                "1. Заполни свой профиль\n"
                "2. Пройди тесты для лучшего понимания себя\n"
                "3. Изучи обучающие материалы\n"
                "4. Найди партнёров через раздел Знакомства\n"
                "5. Общайся и создавай проекты вместе!",
                reply_markup=get_main_menu_keyboard(is_minor=is_minor)
            )


@router.callback_query(F.data == "dating")
async def cmd_dating(callback: CallbackQuery) -> None:
    """Раздел Знакомства"""
    # Проверяем, не находимся ли мы уже в этом разделе (до callback.answer())
    current_text = callback.message.text or (callback.message.caption or "")
    if "💕 <b>Знакомства</b>" in current_text:
        await callback.answer("💕 Вы уже в разделе Знакомства", show_alert=False)
        return
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "💕 <b>Знакомства</b>\n\n"
            "Здесь ты сможешь находить партнёров по интересам и целям.\n\n"
            "Функция в разработке.",
            reply_markup=get_main_menu_keyboard(is_minor=False)
        )
    except Exception as e:
        # Если не удалось отредактировать, проверяем почему
        # Если это потому что сообщение уже такое же, просто игнорируем
        current_text_after = callback.message.text or (callback.message.caption or "")
        if "💕 <b>Знакомства</b>" not in current_text_after:
            # Только если сообщение действительно другое, отправляем новое
            await callback.message.answer(
                "💕 <b>Знакомства</b>\n\n"
                "Здесь ты сможешь находить партнёров по интересам и целям.\n\n"
                "Функция в разработке.",
                reply_markup=get_main_menu_keyboard(is_minor=False)
            )


@router.callback_query(F.data == "premium")
async def cmd_premium(callback: CallbackQuery) -> None:
    """Co-founder Premium"""
    # Проверяем, не находимся ли мы уже в этом разделе (до callback.answer())
    current_text = callback.message.text or (callback.message.caption or "")
    if "⭐ <b>Co-founder Premium</b>" in current_text:
        await callback.answer("⭐ Вы уже в разделе Premium", show_alert=False)
        return
    
    await callback.answer()
    
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            is_minor = user.is_minor
        break
    try:
        await callback.message.edit_text(
            "⭐ <b>Co-founder Premium</b>\n\n"
            "Расширенные возможности в разработке.",
            reply_markup=get_main_menu_keyboard(is_minor=is_minor)
        )
    except Exception:
        current_text_after = callback.message.text or (callback.message.caption or "")
        if "⭐ <b>Co-founder Premium</b>" not in current_text_after:
            await callback.message.answer(
                "⭐ <b>Co-founder Premium</b>\n\n"
                "Расширенные возможности в разработке.",
                reply_markup=get_main_menu_keyboard(is_minor=is_minor)
            )


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
