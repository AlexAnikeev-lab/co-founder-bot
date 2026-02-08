"""
Общие обработчики (главное меню, навигация)
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.menu import get_main_menu_keyboard, get_profile_reply_keyboard
from keyboards.menu import get_people_keyboard
from keyboards.profile import get_edit_profile_keyboard
from repositories.user_repository import UserRepository
from repositories.database import get_session
from states.registration import ProfileEditStates
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(message: Message, is_minor: bool = False) -> None:
    """Показать главное меню"""
    await message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_menu_keyboard(is_minor=is_minor)
    )


async def _edit_or_send(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup,
    *,
    send_fallback: bool = True,
) -> None:
    """Редактировать последнее сообщение бота или отправить новое, если редактирование невозможно."""
    data = await state.get_data()
    mid = data.get("last_bot_message_id")
    if not mid:
        if send_fallback:
            sent = await message.answer(text, reply_markup=reply_markup)
            await state.update_data(last_bot_message_id=sent.message_id)
        return
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=mid,
            text=text,
            reply_markup=reply_markup,
        )
    except Exception:
        if send_fallback:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)
            except Exception:
                pass
            sent = await message.answer(text, reply_markup=reply_markup)
            await state.update_data(last_bot_message_id=sent.message_id)


@router.message(F.text == "◀️ Назад")
async def cmd_back_from_section(message: Message, state: FSMContext) -> None:
    """Назад: из Партнёров — в меню; из Профиля — редактируем прошлое сообщение, не шлём новое."""
    data = await state.get_data()
    user_id = message.from_user.id if message.from_user else 0

    if data.get("in_partners"):
        await state.update_data(in_partners=False, current_partner_id=None)
        is_minor = False
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)
            if user:
                is_minor = user.is_minor
            break
        await message.answer(
            "Вы вышли из раздела Партнеры. Выберите пункт меню:",
            reply_markup=get_main_menu_keyboard(is_minor),
        )
        return

    if data.get("in_profile"):
        is_minor = False
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)
            if user:
                is_minor = user.is_minor
            break

        current_state = await state.get_state()
        profile_screen = data.get("profile_screen", "profile")
        last_mid = data.get("last_bot_message_id")

        # Из FSM редактирования (фото, описание, качества) — в меню «Изменить»
        if current_state and "ProfileEditStates" in (current_state or ""):
            await state.clear()
            await state.update_data(in_profile=True, profile_screen="edit")
            edit_text = "✏️ <b>Редактирование профиля</b>\n\nЧто ты хочешь изменить?"
            await _edit_or_send(
                message, state, edit_text, get_edit_profile_keyboard(), send_fallback=True
            )
            return

        # Из меню «Изменить», «Люди» или «Тесты» — в экран профиля (редактируем/удаляем и шлём)
        if profile_screen in ("edit", "people", "tests"):
            from handlers.profile import send_profile_view
            await send_profile_view(message, user_id, state, edit_message_id=last_mid)
            return

        # Из «Совпадения» / «Избранные» / «Поиск людей» — в меню «Люди» (редактируем)
        if profile_screen in ("matches", "favorites", "search"):
            await state.update_data(profile_screen="people")
            text = (
                "👥 <b>Люди</b>\n\n"
                "Здесь ты можешь искать единомышленников, "
                "смотреть избранных и совпадения."
            )
            await _edit_or_send(message, state, text, get_people_keyboard(), send_fallback=True)
            return

        # Из экрана профиля — в главное меню (reply-клавиатура, только отправка)
        await state.update_data(in_profile=False, profile_screen=None, last_bot_message_id=None)
        is_minor = False
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)
            if user:
                is_minor = user.is_minor
            break
        await message.answer(
            "Выберите пункт меню:",
            reply_markup=get_main_menu_keyboard(is_minor),
        )
        return

    # Назад из любого другого раздела (обучение, инфо и т.д.) — в главное меню
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            is_minor = user.is_minor
        break
    await message.answer(
        "Выберите пункт меню:",
        reply_markup=get_main_menu_keyboard(is_minor),
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
                sent = await message.answer(
                    "🏠 <b>Главное меню</b>",
                    reply_markup=get_main_menu_keyboard(is_minor=user.is_minor)
                )
                await state.update_data(last_bot_message_id=sent.message_id)
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
