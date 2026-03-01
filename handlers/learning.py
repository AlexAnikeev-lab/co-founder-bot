"""
Обработчики обучающего режима (язык: ru/en).
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
from texts.i18n import t, text_options
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()

LESSON_IDS = (1, 2)


async def _get_user_lang(user_id: int) -> str:
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break
    return lang


def get_learning_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура меню обучения (язык: ru/en)."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=t(lang, "learning_module_1"), callback_data="learning_module:1"))
    builder.add(InlineKeyboardButton(text=t(lang, "learning_module_2"), callback_data="learning_module:2"))
    builder.add(get_back_button("main_menu", lang))
    builder.adjust(1)
    return builder.as_markup()


def get_module_lessons_keyboard(module_id: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура уроков модуля (язык: ru/en)."""
    builder = InlineKeyboardBuilder()
    if module_id == "1":
        for lid in LESSON_IDS:
            builder.add(
                InlineKeyboardButton(
                    text=f"📌 {t(lang, f'lesson_{lid}_title')}",
                    callback_data=f"learning_lesson:1:{lid}",
                )
            )
    builder.add(get_back_button("learning", lang))
    builder.adjust(1)
    return builder.as_markup()


@router.message(F.text.in_(text_options("menu_learning")))
@router.callback_query(F.data == "learning")
async def show_learning_menu(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Показать меню обучения (язык ru/en)."""
    user_id = event.from_user.id if event.from_user else 0
    lang = await _get_user_lang(user_id)
    text = t(lang, "learning_title") + "\n\n" + t(lang, "learning_choose_module")
    reply_markup = get_learning_menu_keyboard(lang)
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
            try:
                await message.delete()
            except Exception:
                pass
            data = await state.get_data()
            chat_id = message.chat.id
            bot = message.bot
            for mid in (data.get("last_bot_message_id"), data.get("profile_section_message_id")):
                if mid:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=mid)
                    except Exception:
                        pass
            await state.update_data(profile_section_message_id=None)
            sent = await message.answer(text, reply_markup=reply_markup)
            await state.update_data(last_bot_message_id=sent.message_id)
    except Exception as e:
        logger.error(f"Ошибка в show_learning_menu: {e}", exc_info=True)
        await handle_error(None, e, "show_learning_menu")


@router.callback_query(F.data.startswith("learning_module:"))
async def show_learning_module(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать модуль обучения (язык ru/en)."""
    await callback.answer()
    lang = await _get_user_lang(callback.from_user.id)
    module_id = callback.data.split(":")[1]
    if module_id == "1":
        text = f"📚 <b>{t(lang, 'learning_module')} {module_id}</b>\n\n" + t(lang, "learning_choose_lesson")
        reply_markup = get_module_lessons_keyboard(module_id, lang)
    else:
        text = f"📚 <b>{t(lang, 'learning_module')} {module_id}</b>\n\n" + t(lang, "lessons_coming")
        reply_markup = get_learning_menu_keyboard(lang)
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
    """Показать контент урока (язык ru/en)."""
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    module_id, lesson_id_str = parts[1], parts[2]
    try:
        lesson_id = int(lesson_id_str)
    except ValueError:
        return
    if lesson_id not in LESSON_IDS:
        return
    lang = await _get_user_lang(callback.from_user.id)
    content = t(lang, f"lesson_{lesson_id}_content")
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=t(lang, "lesson_back_to_module"),
            callback_data=f"learning_module:{module_id}",
        )
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
