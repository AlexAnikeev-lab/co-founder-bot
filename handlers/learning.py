"""
Обработчики обучающего режима
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.common import get_back_button
from keyboards.menu import get_main_menu_keyboard
from repositories.user_repository import UserRepository
from repositories.database import get_session
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()


def get_learning_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню обучения"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Модуль 1", callback_data="learning_module:1"))
    builder.add(InlineKeyboardButton(text="Модуль 2", callback_data="learning_module:2"))
    builder.add(get_back_button("main_menu"))
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "learning")
async def show_learning_menu(callback: CallbackQuery) -> None:
    """Показать меню обучения"""
    try:
        await callback.answer()
        
        # Проверяем, не находимся ли мы уже в разделе обучения
        current_text = callback.message.text or (callback.message.caption or "")
        if "📚 <b>Обучение</b>" in current_text:
            await callback.answer("📚 Вы уже в разделе Обучение", show_alert=False)
            return
        
        try:
            await callback.message.edit_text(
                "📚 <b>Обучение</b>\n\n"
                "Выбери модуль:",
                reply_markup=get_learning_menu_keyboard()
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                "📚 <b>Обучение</b>\n\n"
                "Выбери модуль:",
                reply_markup=get_learning_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в show_learning_menu: {e}", exc_info=True)
        await handle_error(None, e, "show_learning_menu")


@router.callback_query(F.data.startswith("learning_module:"))
async def show_learning_module(callback: CallbackQuery) -> None:
    """Показать модуль обучения"""
    await callback.answer()
    module_id = callback.data.split(":")[1]
    try:
        await callback.message.edit_text(
            f"📚 <b>Модуль {module_id}</b>\n\n"
            "Уроки в разработке.",
            reply_markup=get_learning_menu_keyboard()
        )
    except Exception:
        await callback.message.answer(
            f"📚 <b>Модуль {module_id}</b>\n\n"
            "Уроки в разработке.",
            reply_markup=get_learning_menu_keyboard()
        )


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
