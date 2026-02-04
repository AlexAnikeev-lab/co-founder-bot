"""
Обработчики профиля пользователя
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.menu import get_profile_keyboard
from states.registration import ProfileEditStates
from repositories.user_repository import UserRepository
from repositories.database import get_session
from utils.errors import handle_error
from utils.validators import validate_name, validate_photo

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery) -> None:
    """Показать профиль пользователя"""
    try:
        await callback.answer()
        
        async for session in get_session():
            user = await UserRepository.get_by_telegram_id(
                session,
                callback.from_user.id
            )
            
            if not user or not user.is_registered:
                try:
                    await callback.message.edit_text("❌ Ты ещё не зарегистрирован. Используй /start")
                except Exception:
                    await callback.message.answer("❌ Ты ещё не зарегистрирован. Используй /start")
                return
            
            # Проверяем, не находимся ли мы уже в профиле
            # Проверяем по тексту или caption
            current_text = callback.message.text or (callback.message.caption or "")
            if "👤 <b>Профиль</b>" in current_text:
                await callback.answer("👤 Вы уже в профиле", show_alert=False)
                return
            
            # Формирование текста профиля
            profile_text = f"👤 <b>Профиль</b>\n\n"
            profile_text += f"Имя: {user.name or 'Не указано'}\n"
            profile_text += f"Возраст: {user.age or 'Не указан'}\n"
            
            if user.photo_id:
                # Если есть фото, пытаемся отредактировать caption или отправляем новое
                try:
                    # Пытаемся отредактировать caption если предыдущее сообщение было с фото
                    await callback.message.bot.edit_message_caption(
                        chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id,
                        caption=profile_text,
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
                except Exception:
                    # Если не получилось (не было фото или другое сообщение), удаляем и отправляем новое
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    await callback.message.answer_photo(
                        photo=user.photo_id,
                        caption=profile_text,
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
            else:
                try:
                    await callback.message.edit_text(
                        profile_text,
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
                except Exception:
                    await callback.message.answer(
                        profile_text,
                        reply_markup=get_profile_keyboard(user.is_minor)
                    )
            break
            
    except Exception as e:
        logger.error(f"Ошибка в show_profile: {e}", exc_info=True)
        await handle_error(None, e, "show_profile")


@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактирование профиля"""
    await callback.answer()
    is_minor = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            is_minor = user.is_minor
        break
    try:
        await callback.message.edit_text(
            "✏️ <b>Редактирование профиля</b>\n\n"
            "Что ты хочешь изменить?\n\n"
            "• Имя\n"
            "• Фото\n"
            "• Сильные стороны\n"
            "• Описание",
            reply_markup=get_profile_keyboard(is_minor=is_minor)
        )
    except Exception:
        # Если предыдущее было с фото, удаляем и отправляем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "✏️ <b>Редактирование профиля</b>\n\n"
            "Что ты хочешь изменить?\n\n"
            "• Имя\n"
            "• Фото\n"
            "• Сильные стороны\n"
            "• Описание",
            reply_markup=get_profile_keyboard(is_minor=is_minor)
        )


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
async def show_people(callback: CallbackQuery) -> None:
    """Раздел Люди"""
    await callback.answer()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            try:
                await callback.message.edit_text(
                    "👥 <b>Люди</b>\n\nФункция в разработке.",
                    reply_markup=get_profile_keyboard(is_minor=user.is_minor)
                )
            except Exception:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(
                    "👥 <b>Люди</b>\n\nФункция в разработке.",
                    reply_markup=get_profile_keyboard(is_minor=user.is_minor)
                )
        break


@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery) -> None:
    """Избранные"""
    await callback.answer()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            try:
                await callback.message.edit_text(
                    "⭐ <b>Избранные</b>\n\nФункция в разработке.",
                    reply_markup=get_profile_keyboard(is_minor=user.is_minor)
                )
            except Exception:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(
                    "⭐ <b>Избранные</b>\n\nФункция в разработке.",
                    reply_markup=get_profile_keyboard(is_minor=user.is_minor)
                )
        break


@router.callback_query(F.data == "matches")
async def show_matches(callback: CallbackQuery) -> None:
    """Мэтчи"""
    await callback.answer()
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            try:
                await callback.message.edit_text(
                    "💕 <b>Мэтчи</b>\n\nФункция в разработке.",
                    reply_markup=get_profile_keyboard(is_minor=user.is_minor)
                )
            except Exception:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(
                    "💕 <b>Мэтчи</b>\n\nФункция в разработке.",
                    reply_markup=get_profile_keyboard(is_minor=user.is_minor)
                )
        break


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
