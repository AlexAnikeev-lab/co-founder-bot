"""
Обработчики профиля пользователя
"""

import html
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.menu import get_profile_keyboard, get_profile_reply_keyboard
from keyboards.menu import PROFILE_REPLY_PEOPLE
from states.registration import ProfileEditStates
from repositories.user_repository import UserRepository
from repositories.test_repository import TestResultRepository
from repositories.database import get_session
from utils.errors import handle_error
from utils.validators import (
    validate_name, 
    validate_photo,
    validate_short_description,
    validate_full_description,
    validate_qualities
)

logger = logging.getLogger(__name__)
router = Router()


async def send_profile_view(
    message: Message, user_id: int, state: FSMContext, edit_message_id: int | None = None
) -> None:
    """Отправить экран профиля. Если передан edit_message_id — редактируем сообщение вместо отправки нового (или удаляем и шлём, если нужна фотка)."""
    await state.update_data(in_profile=True, profile_screen="profile")
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if not user or not user.is_registered:
            if edit_message_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=edit_message_id,
                        text="❌ Профиль не найден.",
                    )
                except Exception:
                    await message.answer("❌ Профиль не найден.")
            else:
                await message.answer("❌ Профиль не найден.")
            return
        profile_text = (
            f"👤 <b>Профиль</b>\n\n"
            f"<b>Имя:</b> {user.name or 'Не указано'}\n"
            f"<b>Возраст:</b> {user.age or 'Не указан'}\n\n"
        )
        if user.short_description:
            profile_text += "<b>О себе:</b>\n"
            profile_text += f"<blockquote>{html.escape(user.short_description)}</blockquote>\n\n"
        if user.qualities:
            qualities_list = user.qualities.split(",")
            profile_text += "<b>Главные качества:</b>\n"
            for q in qualities_list:
                profile_text += f"• {q.strip()}\n"
            profile_text += "\n"
        if user.full_description:
            profile_text += "<b>Подробнее:</b>\n"
            profile_text += f"<blockquote>{html.escape(user.full_description)}</blockquote>"
        kb = get_profile_keyboard(user.is_minor)
        if edit_message_id:
            try:
                if user.photo_id:
                    await message.bot.delete_message(chat_id=message.chat.id, message_id=edit_message_id)
                    msg = await message.answer_photo(
                        photo=user.photo_id,
                        caption=profile_text,
                        reply_markup=kb,
                    )
                else:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=edit_message_id,
                        text=profile_text,
                        reply_markup=kb,
                    )
                    msg = None
            except Exception:
                if user.photo_id:
                    msg = await message.answer_photo(
                        photo=user.photo_id,
                        caption=profile_text,
                        reply_markup=kb,
                    )
                else:
                    msg = await message.answer(profile_text, reply_markup=kb)
            if msg:
                await state.update_data(last_bot_message_id=msg.message_id)
            else:
                await state.update_data(last_bot_message_id=edit_message_id)
        else:
            if user.photo_id:
                msg = await message.answer_photo(
                    photo=user.photo_id,
                    caption=profile_text,
                    reply_markup=kb,
                )
            else:
                msg = await message.answer(profile_text, reply_markup=kb)
            await state.update_data(last_bot_message_id=msg.message_id)
            await message.answer(
                "Выберите раздел:",
                reply_markup=get_profile_reply_keyboard(user.is_minor),
            )
        break


@router.message(F.text == "👤 Профиль")
@router.callback_query(F.data == "profile")
async def show_profile(event, state: FSMContext) -> None:
    """Показать профиль пользователя и меню: Тесты, Люди, Premium, Назад (reply-клавиатура)."""
    try:
        if isinstance(event, CallbackQuery):
            await event.answer()
            message = event.message
            user_id = event.from_user.id
        else:
            message = event
            user_id = event.from_user.id

        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, user_id)

            if not user or not user.is_registered:
                await message.answer("❌ Ты ещё не зарегистрирован. Используй /start")
                return

            await state.update_data(in_profile=True, profile_screen="profile")

            profile_text = f"👤 <b>Профиль</b>\n\n"
            profile_text += f"<b>Имя:</b> {user.name or 'Не указано'}\n"
            profile_text += f"<b>Возраст:</b> {user.age or 'Не указан'}\n\n"

            if user.short_description:
                profile_text += "<b>О себе:</b>\n"
                profile_text += f"<blockquote>{html.escape(user.short_description)}</blockquote>\n\n"

            if user.qualities:
                qualities_list = user.qualities.split(',')
                profile_text += f"<b>Главные качества:</b>\n"
                for quality in qualities_list:
                    profile_text += f"• {quality.strip()}\n"
                profile_text += "\n"

            if user.full_description:
                profile_text += "<b>Подробнее:</b>\n"
                profile_text += f"<blockquote>{html.escape(user.full_description)}</blockquote>"

            if user.photo_id:
                msg = await message.answer_photo(
                    photo=user.photo_id,
                    caption=profile_text,
                    reply_markup=get_profile_keyboard(user.is_minor)
                )
            else:
                msg = await message.answer(
                    profile_text,
                    reply_markup=get_profile_keyboard(user.is_minor)
                )
            await state.update_data(last_bot_message_id=msg.message_id)
            await message.answer("Выберите раздел:", reply_markup=get_profile_reply_keyboard(user.is_minor))
            break

    except Exception as e:
        logger.error(f"Ошибка в show_profile: {e}", exc_info=True)
        await handle_error(None, e, "show_profile")


@router.message(F.text == PROFILE_REPLY_PEOPLE)
async def profile_reply_people(message: Message, state: FSMContext) -> None:
    """Раздел Люди по кнопке из меню профиля."""
    await state.update_data(profile_screen="people")
    from keyboards.menu import get_people_keyboard
    text = (
        "👥 <b>Люди</b>\n\n"
        "Здесь ты можешь искать единомышленников, "
        "смотреть избранных и совпадения."
    )
    sent = await message.answer(text, reply_markup=get_people_keyboard())
    await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактирование профиля"""
    await callback.answer()
    await state.update_data(profile_screen="edit")
    from keyboards.profile import get_edit_profile_keyboard
    try:
        await callback.message.edit_text(
            "✏️ <b>Редактирование профиля</b>\n\n"
            "Что ты хочешь изменить?",
            reply_markup=get_edit_profile_keyboard()
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            "✏️ <b>Редактирование профиля</b>\n\n"
            "Что ты хочешь изменить?",
            reply_markup=get_edit_profile_keyboard()
        )
        await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "delete_profile")
async def delete_profile_confirm(callback: CallbackQuery) -> None:
    """Подтверждение удаления профиля"""
    await callback.answer()
    from keyboards.profile import get_delete_confirm_keyboard
    try:
        await callback.message.edit_text(
            "⚠️ <b>Удаление профиля</b>\n\n"
            "Ты уверен, что хочешь удалить свой профиль?\n"
            "Все твои данные будут удалены без возможности восстановления.",
            reply_markup=get_delete_confirm_keyboard()
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "⚠️ <b>Удаление профиля</b>\n\n"
            "Ты уверен, что хочешь удалить свой профиль?\n"
            "Все твои данные будут удалены без возможности восстановления.",
            reply_markup=get_delete_confirm_keyboard()
        )


@router.callback_query(F.data == "delete_profile_confirm")
async def delete_profile_yes(callback: CallbackQuery) -> None:
    """Удаление профиля подтверждено"""
    try:
        await callback.answer()
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
            if user:
                user_id = callback.from_user.id
                await TestResultRepository.delete_by_user_id(session, user_id)
                await UserRepository.delete(session, user)
                try:
                    await callback.message.edit_text("✅ Профиль удалён. Используй /start для новой регистрации.")
                except Exception:
                    await callback.message.answer("✅ Профиль удалён. Используй /start для новой регистрации.")
            else:
                try:
                    await callback.message.edit_text("❌ Профиль не найден.")
                except Exception:
                    await callback.message.answer("❌ Профиль не найден.")
            break
    except Exception as e:
        logger.error(f"Ошибка в delete_profile_yes: {e}", exc_info=True)
        try:
            await callback.message.edit_text("❌ Ошибка при удалении профиля.")
        except Exception:
            await callback.message.answer("❌ Ошибка при удалении профиля.")


@router.callback_query(F.data == "delete_profile_cancel")
async def delete_profile_no(callback: CallbackQuery) -> None:
    """Отмена удаления профиля"""
    await callback.answer()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            try:
                await callback.message.edit_text("Отмена. Профиль сохранён.", reply_markup=get_profile_keyboard(user.is_minor))
            except Exception:
                await callback.message.answer("Отмена. Профиль сохранён.", reply_markup=get_profile_keyboard(user.is_minor))
        else:
            try:
                await callback.message.edit_text("❌ Профиль не найден.")
            except Exception:
                await callback.message.answer("❌ Профиль не найден.")
        break


@router.callback_query(F.data == "people")
async def show_people(callback: CallbackQuery, state: FSMContext) -> None:
    """Раздел Люди - подменю с поиском, избранными и совпадениями"""
    await callback.answer()
    await state.update_data(profile_screen="people")
    from keyboards.menu import get_people_keyboard
    
    text = (
        "👥 <b>Люди</b>\n\n"
        "Здесь ты можешь искать единомышленников, "
        "смотреть избранных и совпадения."
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "search_people")
async def search_people(callback: CallbackQuery, state: FSMContext) -> None:
    """Поиск людей"""
    await callback.answer()
    await state.update_data(profile_screen="search")
    from keyboards.menu import get_people_keyboard
    
    text = (
        "🔍 <b>Поиск людей</b>\n\n"
        "Функция в разработке."
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery, state: FSMContext) -> None:
    """Избранные"""
    await callback.answer()
    await state.update_data(profile_screen="favorites")
    from keyboards.menu import get_people_keyboard
    
    text = (
        "⭐ <b>Избранные</b>\n\n"
        "Здесь будут люди, которых ты добавил в избранное.\n\n"
        "Функция в разработке."
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=get_people_keyboard()
        )
        await state.update_data(last_bot_message_id=sent.message_id)


@router.callback_query(F.data == "matches")
async def show_matches(callback: CallbackQuery, state: FSMContext) -> None:
    """Совпадения — список людей с взаимным лайком и кнопка «Перейти в ЛС»"""
    await callback.answer()
    await state.update_data(profile_screen="matches")
    from keyboards.menu import get_people_keyboard
    from repositories.database import get_session
    from repositories.swipe_repository import SwipeRepository
    from repositories.user_repository import UserRepository
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    user_id = callback.from_user.id
    builder = InlineKeyboardBuilder()

    try:
        async for session in get_session():
            match_ids = await SwipeRepository.get_mutual_matches(session, user_id)
            if not match_ids:
                text = (
                    "🤝 <b>Совпадения</b>\n\n"
                    "Здесь будут люди, с которыми у тебя взаимный интерес.\n\n"
                    "Пока ни с кем нет совпадений. Лайкайте анкеты в разделе «🤝 Партнёры» — когда кто-то ответит лайком, вы оба появятся здесь."
                )
                builder.adjust(1)
                break
            # Загружаем пользователей по id
            lines = ["🤝 <b>Совпадения</b>\n\nЛюди, с которыми у вас взаимный интерес:\n"]
            for mid in match_ids:
                u = await UserRepository.get_by_telegram_id(session, mid)
                if u:
                    name = u.name or "Пользователь"
                    lines.append(f"• {name}")
                    uname = (u.username or "").strip().lstrip("@")
                    url = f"https://t.me/{uname}" if uname else f"tg://user?id={u.telegram_id}"
                    builder.add(
                        InlineKeyboardButton(text=f"💬 {name} — в ЛС", url=url)
                    )
            builder.adjust(1)
            text = "\n".join(lines)
            break
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Ошибка загрузки совпадений: %s", e, exc_info=True)
        text = "Не удалось загрузить список. Попробуйте позже."
        builder.adjust(1)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
        )
        await state.update_data(last_bot_message_id=callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        sent = await callback.message.answer(
            text,
            reply_markup=builder.as_markup(),
        )
        await state.update_data(last_bot_message_id=sent.message_id)


# Обработчики редактирования полей профиля

@router.callback_query(F.data == "edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования имени"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    try:
        await callback.message.edit_text(
            "✏️ <b>Изменение имени</b>\n\n"
            "Введи новое имя:",
            reply_markup=get_cancel_button()
        )
    except Exception:
        await callback.message.answer(
            "✏️ <b>Изменение имени</b>\n\n"
            "Введи новое имя:",
            reply_markup=get_cancel_button()
        )
    await state.set_state(ProfileEditStates.editing_name)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_name)
async def process_edit_name(message: Message, state: FSMContext) -> None:
    """Обработка нового имени"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    if not validate_name(message.text):
        if last_msg_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Имя: от 2 до 50 символов, только буквы.\n\n✏️ <b>Изменение имени</b>\n\nВведи новое имя:",
                    reply_markup=None
                )
            except Exception:
                pass
        return
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, name=message.text)
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="✅ Имя обновлено!",
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
                except Exception:
                    await message.answer("✅ Имя обновлено!", reply_markup=get_profile_keyboard(user.is_minor))
            await state.clear()
        break


@router.callback_query(F.data == "edit_photo")
async def start_edit_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования фото"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    try:
        await callback.message.edit_text(
            "📸 <b>Изменение фото</b>\n\n"
            "Отправь новое фото:",
            reply_markup=get_cancel_button()
        )
    except Exception:
        await callback.message.answer(
            "📸 <b>Изменение фото</b>\n\n"
            "Отправь новое фото:",
            reply_markup=get_cancel_button()
        )
    await state.set_state(ProfileEditStates.editing_photo)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_photo, F.photo)
async def process_edit_photo(message: Message, state: FSMContext) -> None:
    """Обработка нового фото"""
    try:
        await message.delete()
    except Exception:
        pass
    
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, photo_id=photo_id)
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="✅ Фото обновлено!",
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
                except Exception:
                    await message.answer("✅ Фото обновлено!", reply_markup=get_profile_keyboard(user.is_minor))
            await state.clear()
        break


@router.callback_query(F.data == "edit_short_description")
async def start_edit_short_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования краткого описания"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    from texts.messages import SHORT_DESCRIPTION_REQUEST
    try:
        await callback.message.edit_text(
            SHORT_DESCRIPTION_REQUEST,
            reply_markup=get_cancel_button()
        )
    except Exception:
        await callback.message.answer(
            SHORT_DESCRIPTION_REQUEST,
            reply_markup=get_cancel_button()
        )
    await state.set_state(ProfileEditStates.editing_short_description)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_short_description)
async def process_edit_short_description(message: Message, state: FSMContext) -> None:
    """Обработка нового краткого описания"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    if not validate_short_description(message.text):
        if last_msg_id:
            try:
                from texts.messages import SHORT_DESCRIPTION_REQUEST
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Краткое описание: от 10 до 200 символов.\n\n" + SHORT_DESCRIPTION_REQUEST,
                    reply_markup=None
                )
            except Exception:
                pass
        return
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, short_description=message.text)
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="✅ Краткое описание обновлено!",
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
                except Exception:
                    await message.answer("✅ Краткое описание обновлено!", reply_markup=get_profile_keyboard(user.is_minor))
            await state.clear()
        break


@router.callback_query(F.data == "edit_full_description")
async def start_edit_full_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования полного описания"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    from texts.messages import FULL_DESCRIPTION_REQUEST
    try:
        await callback.message.edit_text(
            FULL_DESCRIPTION_REQUEST,
            reply_markup=get_cancel_button()
        )
    except Exception:
        await callback.message.answer(
            FULL_DESCRIPTION_REQUEST,
            reply_markup=get_cancel_button()
        )
    await state.set_state(ProfileEditStates.editing_full_description)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_full_description)
async def process_edit_full_description(message: Message, state: FSMContext) -> None:
    """Обработка нового полного описания"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    if not validate_full_description(message.text):
        if last_msg_id:
            try:
                from texts.messages import FULL_DESCRIPTION_REQUEST
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Полное описание: от 20 до 1000 символов.\n\n" + FULL_DESCRIPTION_REQUEST,
                    reply_markup=None
                )
            except Exception:
                pass
        return
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, full_description=message.text)
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="✅ Полное описание обновлено!",
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
                except Exception:
                    await message.answer("✅ Полное описание обновлено!", reply_markup=get_profile_keyboard(user.is_minor))
            await state.clear()
        break


@router.callback_query(F.data == "edit_qualities")
async def start_edit_qualities(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования качеств"""
    await callback.answer()
    from keyboards.common import get_cancel_button
    from texts.messages import QUALITIES_REQUEST
    try:
        await callback.message.edit_text(
            QUALITIES_REQUEST,
            reply_markup=get_cancel_button()
        )
    except Exception:
        await callback.message.answer(
            QUALITIES_REQUEST,
            reply_markup=get_cancel_button()
        )
    await state.set_state(ProfileEditStates.editing_qualities)
    await state.update_data(last_bot_message_id=callback.message.message_id)


@router.message(ProfileEditStates.editing_qualities)
async def process_edit_qualities(message: Message, state: FSMContext) -> None:
    """Обработка новых качеств"""
    try:
        await message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_bot_message_id")
    
    if not validate_qualities(message.text):
        if last_msg_id:
            try:
                from texts.messages import QUALITIES_REQUEST
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=last_msg_id,
                    text="❌ Укажи ровно 3 качества через запятую.\n\n" + QUALITIES_REQUEST,
                    reply_markup=None
                )
            except Exception:
                pass
        return
    
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        if user:
            await UserRepository.update(session, user, qualities=message.text)
            if last_msg_id:
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=last_msg_id,
                        text="✅ Качества обновлены!",
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
                except Exception:
                    await message.answer("✅ Качества обновлены!", reply_markup=get_profile_keyboard(user.is_minor))
            await state.clear()
        break


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
