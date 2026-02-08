"""
Обработчики обучающего режима
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from keyboards.common import get_back_button
from keyboards.menu import get_main_menu_keyboard
from repositories.user_repository import UserRepository
from repositories.database import get_session
from utils.errors import handle_error
from texts.messages import (
    LESSON_1_TITLE,
    LESSON_1_CONTENT,
    LESSON_2_TITLE,
    LESSON_2_CONTENT,
)

logger = logging.getLogger(__name__)
router = Router()

# Уроки: id -> (заголовок, контент)
LESSONS: dict[int, tuple[str, str]] = {
    1: (LESSON_1_TITLE, LESSON_1_CONTENT),
    2: (LESSON_2_TITLE, LESSON_2_CONTENT),
}


def get_learning_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню обучения"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Модуль 1", callback_data="learning_module:1"))
    builder.add(InlineKeyboardButton(text="Модуль 2", callback_data="learning_module:2"))
    builder.add(get_back_button("main_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_module_lessons_keyboard(module_id: str) -> InlineKeyboardMarkup:
    """Клавиатура уроков модуля. В модуле 1 — 2 урока о бизнесе."""
    builder = InlineKeyboardBuilder()
    if module_id == "1":
        for lid, (title, _) in LESSONS.items():
            builder.add(
                InlineKeyboardButton(
                    text=f"📌 {title}",
                    callback_data=f"learning_lesson:1:{lid}",
                )
            )
    builder.add(InlineKeyboardButton(text="⬅ Назад", callback_data="learning"))
    builder.adjust(1)
    return builder.as_markup()


@router.message(F.text == "📚 Обучение")
@router.callback_query(F.data == "learning")
async def show_learning_menu(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Показать меню обучения (редактируем прошлое сообщение, не шлём новое)."""
    text = "📚 <b>Обучение</b>\n\nВыбери модуль:"
    reply_markup = get_learning_menu_keyboard()
    try:
        if isinstance(event, CallbackQuery):
            await event.answer()
            try:
                await event.message.edit_text(text=text, reply_markup=reply_markup)
                await state.update_data(last_bot_message_id=event.message.message_id)
            except Exception:
                try:
                    await event.message.delete()
                except Exception:
                    pass
                sent = await event.message.answer(text, reply_markup=reply_markup)
                await state.update_data(last_bot_message_id=sent.message_id)
        else:
            message = event
            data = await state.get_data()
            mid = data.get("last_bot_message_id")
            if mid:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=mid,
                        text=text,
                        reply_markup=reply_markup,
                    )
                    await state.update_data(last_bot_message_id=mid)
                    return
                except Exception:
                    try:
                        await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)
                    except Exception:
                        pass
            sent = await message.answer(text, reply_markup=reply_markup)
            await state.update_data(last_bot_message_id=sent.message_id)
    except Exception as e:
        logger.error(f"Ошибка в show_learning_menu: {e}", exc_info=True)
        await handle_error(None, e, "show_learning_menu")


@router.callback_query(F.data.startswith("learning_module:"))
async def show_learning_module(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать модуль обучения (редактируем сообщение)."""
    await callback.answer()
    module_id = callback.data.split(":")[1]
    if module_id == "1":
        text = (
            f"📚 <b>Модуль {module_id}</b>\n\n"
            "Выбери урок о бизнесе и стартапах:"
        )
        reply_markup = get_module_lessons_keyboard(module_id)
    else:
        text = (
            f"📚 <b>Модуль {module_id}</b>\n\n"
            "Уроки в разработке."
        )
        reply_markup = get_learning_menu_keyboard()
    try:
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(text=text, reply_markup=reply_markup)
        await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data.startswith("learning_lesson:"))
async def show_lesson(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать контент урока (редактируем сообщение)."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    module_id, lesson_id_str = parts[1], parts[2]
    try:
        lesson_id = int(lesson_id_str)
    except ValueError:
        return
    if lesson_id not in LESSONS:
        return
    title, content = LESSONS[lesson_id]
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="⬅ К модулю", callback_data=f"learning_module:{module_id}")
    )
    try:
        await callback.message.edit_text(
            content,
            reply_markup=builder.as_markup(),
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            content,
            reply_markup=builder.as_markup(),
        )
        await state.update_data(last_bot_message_id=sent.message_id)


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
