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
from texts.i18n import t, text_options
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(message: Message, is_minor: bool = False, lang: str = "ru") -> None:
    """Показать главное меню (язык: ru/en)."""
    await message.answer(
        t(lang, "main_menu_title"),
        reply_markup=get_main_menu_keyboard(is_minor=is_minor, lang=lang),
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


@router.message(F.text.in_(text_options("profile_back")))
async def cmd_back_from_section(message: Message, state: FSMContext) -> None:
    """Назад: из Партнёров — в меню; из Профиля — в подменю или меню."""
    try:
        await message.delete()
    except Exception:
        pass
    data = await state.get_data()
    user_id = message.from_user.id if message.from_user else 0
    lang = "ru"
    async for session in get_session():
        u = await UserRepository.get_by_telegram_id(session, user_id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break

    if data.get("in_partners"):
        await state.update_data(in_partners=False, current_partner_id=None)
        is_minor = False
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)
            if user:
                is_minor = user.is_minor
            break
        await message.answer(
            t(lang, "back_from_partners"),
            reply_markup=get_main_menu_keyboard(is_minor, lang),
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

        if current_state and "ProfileEditStates" in (current_state or ""):
            await state.clear()
            await state.update_data(in_profile=True, profile_screen="edit")
            await _edit_or_send(
                message, state, t(lang, "edit_profile_title"), get_edit_profile_keyboard(lang), send_fallback=True
            )
            return

        if profile_screen in ("edit", "people", "tests"):
            from handlers.profile import send_profile_view
            await send_profile_view(message, user_id, state, edit_message_id=last_mid)
            return

        if profile_screen in ("matches", "favorites", "search"):
            await state.update_data(profile_screen="people")
            text = t(lang, "people_title") + "\n\n" + t(lang, "people_intro")
            await _edit_or_send(message, state, text, get_people_keyboard(lang), send_fallback=True)
            return

        chat_id = message.chat.id
        bot = message.bot
        for mid in (data.get("last_bot_message_id"), data.get("profile_section_message_id")):
            if mid:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
        await state.update_data(in_profile=False, profile_screen=None, last_bot_message_id=None, profile_section_message_id=None)
        is_minor = False
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)
            if user:
                is_minor = user.is_minor
            break
        sent = await message.answer(t(lang, "choose_menu_item"), reply_markup=get_main_menu_keyboard(is_minor, lang))
        await state.update_data(last_bot_message_id=sent.message_id)
        return

    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            is_minor = user.is_minor
        break
    await message.answer(t(lang, "choose_menu_item"), reply_markup=get_main_menu_keyboard(is_minor, lang))


@router.message(F.text.in_(text_options("menu_main")))
@router.callback_query(F.data == "main_menu")
async def cmd_main_menu(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки Главное меню (ru/en). Удаляем предыдущий экран (профиль, «Выберите раздел» и т.д.)."""
    try:
        if isinstance(event, CallbackQuery):
            await event.answer()
            message = event.message
            user_id = event.from_user.id
            try:
                await message.delete()
            except Exception:
                pass
        else:
            message = event
            user_id = event.from_user.id
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
        await state.clear()

        lang = "ru"
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)
            if user:
                lang = getattr(user, "language", None) or "ru"
                sent = await message.answer(
                    t(lang, "main_menu_title"),
                    reply_markup=get_main_menu_keyboard(is_minor=user.is_minor, lang=lang),
                )
                await state.update_data(last_bot_message_id=sent.message_id)
            else:
                await message.answer(t(lang, "not_registered_use_start"))
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


@router.message(F.text.in_(text_options("menu_info")))
@router.callback_query(F.data == "info")
async def cmd_info(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Информация о боте (ru/en). При переходе удаляем предыдущее меню."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
        try:
            await message.delete()
        except Exception:
            pass
    else:
        message = event
        user_id = event.from_user.id
        try:
            await message.delete()
        except Exception:
            pass
        data = await state.get_data()
        for mid in (data.get("last_bot_message_id"), data.get("profile_section_message_id")):
            if mid:
                try:
                    await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)
                except Exception:
                    pass

    lang, is_minor = "ru", False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            is_minor = user.is_minor
        break

    text = t(lang, "info_title") + "\n\n" + t(lang, "info_text")
    sent = await message.answer(text, reply_markup=get_main_menu_keyboard(is_minor=is_minor, lang=lang))
    await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "bot_instruction")
async def cmd_bot_instruction(callback: CallbackQuery) -> None:
    """Инструкция по использованию бота (ru/en)."""
    await callback.answer()
    lang, is_minor = "ru", False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            is_minor = user.is_minor
        break
    text = t(lang, "instruction_title") + "\n\n" + t(lang, "instruction_text")
    await callback.message.answer(text, reply_markup=get_main_menu_keyboard(is_minor=is_minor, lang=lang))


@router.message(F.text.in_(text_options("menu_premium")))
@router.callback_query(F.data == "premium")
async def cmd_premium(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Co-founder Subscription: экран преимуществ, кнопки Оплатить / Вернуться в профиль."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
        try:
            await message.delete()
        except Exception:
            pass
    else:
        message = event
        user_id = event.from_user.id
        try:
            await message.delete()
        except Exception:
            pass
        data = await state.get_data()
        for mid in (data.get("last_bot_message_id"), data.get("profile_section_message_id")):
            if mid:
                try:
                    await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)
                except Exception:
                    pass

    from keyboards.subscription import get_subscription_benefits_keyboard
    from config import Config
    config = Config()

    lang, is_minor, has_sub = "ru", False, False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            is_minor = user.is_minor
            has_sub = getattr(user, "subscription_active", False)
        break

    if has_sub:
        text = t(lang, "subscription_already")
        from keyboards.subscription import get_subscription_congrats_keyboard
        kb = get_subscription_congrats_keyboard(lang)
    else:
        text = t(lang, "subscription_benefits_title").format(
            price=config.SUBSCRIPTION_STARS_PRICE,
            url=config.BUY_STARS_BOT_URL,
        )
        kb = get_subscription_benefits_keyboard(lang)

    sent = await message.answer(text, reply_markup=kb)
    await state.update_data(last_bot_message_id=sent.message_id)


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
