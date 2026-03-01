"""
Обработчики подписки: экран преимуществ, оплата по коду в группе, активация.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import Config
from repositories.database import get_session
from repositories.user_repository import UserRepository
from repositories.subscription_repository import SubscriptionRepository
from keyboards.subscription import (
    get_subscription_benefits_keyboard,
    get_subscription_how_to_keyboard,
    get_subscription_code_keyboard,
    get_subscription_congrats_keyboard,
)
from keyboards.menu import get_main_menu_keyboard
from texts.i18n import t

logger = logging.getLogger(__name__)
router = Router()
config = Config()


def _subscription_benefits_text(lang: str) -> str:
    return t(lang, "subscription_benefits_title").format(
        price=config.SUBSCRIPTION_STARS_PRICE,
        url=config.BUY_STARS_BOT_URL,
    )


@router.callback_query(F.data == "subscription_pay")
async def subscription_pay(callback: CallbackQuery, state: FSMContext) -> None:
    """Экран «Как оплатить»: схема и кнопка «Показать код»."""
    await callback.answer()
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break
    text = t(lang, "subscription_how_to_title")
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_subscription_how_to_keyboard(lang),
        )
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_subscription_how_to_keyboard(lang))


@router.callback_query(F.data == "subscription_show_code")
async def subscription_show_code(callback: CallbackQuery, state: FSMContext) -> None:
    """Генерация кода, сохранение в pending, показ ссылки на группу и кода."""
    await callback.answer()
    user_id = callback.from_user.id
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break

    code = f"{config.PAYMENT_CODE_BASE}_{user_id}"
    group_url = config.PAYMENT_GROUP_LINK or "https://t.me/cofounder_support"
    async for session in get_session():
        await SubscriptionRepository.add_pending_code(session, code, user_id)
        break

    text = t(lang, "subscription_code_screen").format(group_url=group_url, code=code)
    try:
        # Старое сообщение (например, экран преимуществ) заменяем экраном с кодом
        await callback.message.edit_text(
            text,
            reply_markup=get_subscription_code_keyboard(lang),
        )
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_subscription_code_keyboard(lang))


@router.callback_query(F.data == "subscription_i_paid")
async def subscription_i_paid(callback: CallbackQuery, state: FSMContext) -> None:
    """Проверка: если подписка уже активирована (бот активировал по коду в группе) — поздравление, иначе подсказка."""
    await callback.answer()
    user_id = callback.from_user.id
    lang = "ru"
    has_sub = False
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            lang = getattr(user, "language", None) or "ru"
            has_sub = getattr(user, "subscription_active", False)
        break

    if has_sub:
        text = t(lang, "subscription_congrats")
        kb = get_subscription_congrats_keyboard(lang)
    else:
        text = t(lang, "subscription_not_yet")
        kb = get_subscription_code_keyboard(lang)

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "subscription_back_profile")
async def subscription_back_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться в профиль (очистка состояния и переход в раздел профиля)."""
    await callback.answer()
    await state.clear()
    from handlers.profile import show_profile
    await show_profile(callback, state)


async def handle_payment_group_message(message: Message) -> bool:
    """
    Обработка сообщения в группе оплаты: если текст совпадает с ожидающим кодом
    (кто-то нажал «Показать код» и отправил код в группу) — удаляем сообщение,
    активируем подписку, отправляем пользователю поздравление.
    Возвращает True, если сообщение было обработано (код найден и использован).
    """
    if not config.payment_group_chat_id_matches(message.chat.id):
        return False
    text = (message.text or "").strip()
    if not text:
        return False

    logger.info("Группа оплаты: сообщение chat_id=%s text=%r", message.chat.id, text[:50])

    user_id = None
    async for session in get_session():
        user_id = await SubscriptionRepository.consume_code(session, text)
        break

    if user_id is None:
        logger.debug("Группа оплаты: код не найден в ожидающих, text=%r", text[:50])
        return False

    logger.info("Группа оплаты: код принят, user_id=%s, удаляю сообщение", user_id)
    try:
        await message.delete()
    except Exception as e:
        logger.warning("Не удалось удалить сообщение с кодом в группе: %s", e)

    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            await UserRepository.update(
                session, user,
                subscription_active=True,
                subscription_until=None,
                super_like_used=False,
            )
        break

    lang = "ru"
    async for session in get_session():
        u = await UserRepository.get_by_telegram_id(session, user_id)
        if u:
            lang = getattr(u, "language", None) or "ru"
        break

    try:
        from keyboards.subscription import get_subscription_congrats_keyboard
        # Удаляем предыдущее сообщение с кодом в личке (если есть)
        # Для простоты отправляем новое поздравление — пользователь увидит актуальный статус.
        await message.bot.send_message(
            chat_id=user_id,
            text=t(lang, "subscription_congrats"),
            reply_markup=get_subscription_congrats_keyboard(lang),
        )
    except Exception as e:
        logger.error("Не удалось отправить поздравление о подписке user_id=%s: %s", user_id, e)

    return True


@router.message(F.chat.type.in_(("group", "supergroup")))
async def maybe_payment_group_message(message: Message) -> None:
    """
    Любое сообщение в группе/супергруппе: если это группа оплаты — логируем и при наличии текста
    пытаемся обработать код. Личные чаты (private) вообще не затрагиваем.
    """
    if not config.payment_group_chat_id_matches(message.chat.id):
        return

    has_text = bool(message.text and message.text.strip())
    logger.info(
        "Группа оплаты: сообщение chat_id=%s, есть_текст=%s",
        message.chat.id,
        has_text,
    )
    if not has_text:
        return
    await handle_payment_group_message(message)


@router.edited_message(F.chat.type.in_(("group", "supergroup")))
async def maybe_payment_group_edited_message(message: Message) -> None:
    """
    Редактирование сообщения в группе/супергруппе: если сообщение из группы оплаты — обрабатываем так же
    (код могли вписать через «редактировать»). Личные чаты не затрагиваем.
    """
    if not config.payment_group_chat_id_matches(message.chat.id):
        return

    has_text = bool(message.text and message.text.strip())
    logger.info(
        "Группа оплаты (edited): chat_id=%s, есть_текст=%s",
        message.chat.id,
        has_text,
    )
    if not has_text:
        return
    await handle_payment_group_message(message)


def register_handlers(dp) -> None:
    dp.include_router(router)
