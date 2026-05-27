"""
Проверка обязательных данных перед разделом «Партнёры» и смежными действиями.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.common import get_back_button
from repositories.database import get_session
from repositories.test_repository import TestResultRepository
from repositories.user_repository import UserRepository
from texts.i18n import t
from utils.qualities import is_quality_slot_filled

if TYPE_CHECKING:
    from repositories.user_repository import User
    from repositories.test_repository import TestResult

PREREQ_MSG_ID_KEY = "partners_prerequisites_message_id"
PREREQ_CHAT_ID_KEY = "partners_prerequisites_chat_id"
PREREQ_SECTION_KEY = "partners_prerequisites_section_title_key"
FROM_PREREQ_KEY = "from_partners_prerequisites"


@dataclass(frozen=True)
class MissingPrerequisite:
    """Один недостающий пункт: подпись кнопки и callback."""

    button_key: str
    callback_data: str


def collect_missing_prerequisites(
    user: User,
    test_result: Optional[TestResult],
) -> list[MissingPrerequisite]:
    """Список того, что нужно заполнить перед партнёрами (порядок фиксированный)."""
    missing: list[MissingPrerequisite] = []

    if not test_result or not test_result.main_test_completed:
        missing.append(
            MissingPrerequisite(
                button_key="partners_btn_take_test",
                callback_data="start_test:main",
            )
        )
    if not user.short_description:
        missing.append(
            MissingPrerequisite(
                button_key="edit_short_description",
                callback_data="edit_short_description",
            )
        )
    if not user.full_description:
        missing.append(
            MissingPrerequisite(
                button_key="edit_full_description",
                callback_data="edit_full_description",
            )
        )
    for index, button_key in enumerate(
        ("edit_quality_1", "edit_quality_2", "edit_quality_3"),
        start=0,
    ):
        if not is_quality_slot_filled(user.qualities, index):
            missing.append(
                MissingPrerequisite(
                    button_key=button_key,
                    callback_data=button_key,
                )
            )

    return missing


def prerequisites_state_slice(data: dict[str, Any]) -> dict[str, Any]:
    """Поля FSM, привязанные к экрану требований (сохраняем при тесте и редактировании)."""
    return {
        k: data[k]
        for k in (PREREQ_MSG_ID_KEY, PREREQ_CHAT_ID_KEY, PREREQ_SECTION_KEY)
        if k in data and data[k] is not None
    }


def is_prerequisites_gate_message(data: dict[str, Any], message_id: int) -> bool:
    """Сообщение с кнопками требований перед партнёрами."""
    prereq_id = data.get(PREREQ_MSG_ID_KEY)
    return bool(prereq_id and int(prereq_id) == int(message_id))


def build_prerequisites_message(
    lang: str,
    *,
    section_title_key: str = "partners_title",
    all_done: bool = False,
) -> str:
    """Текст экрана требований (без маркированного списка)."""
    if all_done:
        return (
            f"{t(lang, section_title_key)}\n\n"
            f"{t(lang, 'partners_prerequisites_all_done')}"
        )
    return (
        f"{t(lang, section_title_key)}\n\n"
        f"{t(lang, 'partners_prerequisites_intro')}"
    )


def build_prerequisites_keyboard(
    lang: str,
    missing: list[MissingPrerequisite],
    *,
    back_callback: str = "main_menu",
    section_title_key: str = "partners_title",
) -> InlineKeyboardMarkup:
    """Кнопки на каждый недостающий пункт + «Назад»."""
    builder = InlineKeyboardBuilder()
    for item in missing:
        builder.add(
            InlineKeyboardButton(
                text=t(lang, item.button_key),
                callback_data=item.callback_data,
            )
        )
    builder.add(get_back_button(back_callback, lang))
    builder.adjust(1)
    return builder.as_markup()


def build_prerequisites_all_done_keyboard(
    lang: str,
    *,
    section_title_key: str = "partners_title",
    back_callback: str = "main_menu",
) -> InlineKeyboardMarkup:
    """Когда всё заполнено — кнопка продолжения (для партнёров) или только «Назад»."""
    builder = InlineKeyboardBuilder()
    if section_title_key == "partners_title":
        builder.add(
            InlineKeyboardButton(
                text=t(lang, "partners_prerequisites_btn_continue"),
                callback_data="dating",
            )
        )
    builder.add(get_back_button(back_callback, lang))
    builder.adjust(1)
    return builder.as_markup()


async def send_partners_prerequisites(
    target: Message,
    state: FSMContext,
    user: User,
    test_result: Optional[TestResult],
    *,
    section_title_key: str = "partners_title",
) -> None:
    """Отправить экран требований и запомнить message_id для последующего обновления кнопок."""
    lang = getattr(user, "language", None) or "ru"
    missing = collect_missing_prerequisites(user, test_result)
    sent = await target.answer(
        build_prerequisites_message(lang, section_title_key=section_title_key),
        reply_markup=build_prerequisites_keyboard(
            lang, missing, section_title_key=section_title_key
        ),
    )
    await state.update_data(
        **{
            PREREQ_MSG_ID_KEY: sent.message_id,
            PREREQ_CHAT_ID_KEY: sent.chat.id,
            PREREQ_SECTION_KEY: section_title_key,
        }
    )


async def refresh_partners_prerequisites_message(
    bot: Bot,
    user_id: int,
    state: FSMContext,
    session: AsyncSession,
) -> bool:
    """
    Обновить клавиатуру экрана требований (убрать выполненные пункты).
    Возвращает True, если всё заполнено.
    """
    data = await state.get_data()
    msg_id = data.get(PREREQ_MSG_ID_KEY)
    chat_id = data.get(PREREQ_CHAT_ID_KEY)
    section_key = data.get(PREREQ_SECTION_KEY, "partners_title")
    if not msg_id or not chat_id:
        return False

    user = await UserRepository.get_by_telegram_id(session, user_id)
    if not user:
        return False

    lang = getattr(user, "language", None) or "ru"
    test_result = await TestResultRepository.get_by_user_id(session, user_id)
    missing = collect_missing_prerequisites(user, test_result)

    if not missing:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=build_prerequisites_message(
                    lang, section_title_key=section_key, all_done=True
                ),
                reply_markup=build_prerequisites_all_done_keyboard(
                    lang, section_title_key=section_key
                ),
            )
        except Exception:
            pass
        return True

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=build_prerequisites_message(lang, section_title_key=section_key),
            reply_markup=build_prerequisites_keyboard(
                lang, missing, section_title_key=section_key
            ),
        )
    except Exception:
        pass
    return False


async def finish_prerequisites_field_edit(
    bot: Bot,
    user_id: int,
    state: FSMContext,
    *,
    chat_id: int | None = None,
) -> None:
    """После заполнения поля из экрана требований — убрать форму ввода и обновить кнопки."""
    data = await state.get_data()
    cleanup_chat_id = chat_id or data.get(PREREQ_CHAT_ID_KEY)
    last_msg_id = data.get("last_bot_message_id")
    if cleanup_chat_id and last_msg_id:
        try:
            await bot.delete_message(chat_id=cleanup_chat_id, message_id=last_msg_id)
        except Exception:
            pass
    prereq_slice = prerequisites_state_slice(data)
    await state.clear()
    if prereq_slice:
        await state.update_data(**prereq_slice)
    async for session in get_session():
        await refresh_partners_prerequisites_message(bot, user_id, state, session)
        break


async def begin_field_edit_from_prerequisites(
    callback,
    state: FSMContext,
    *,
    text: str,
    lang: str,
    edit_state,
) -> bool:
    """
    Открыть редактирование поля новым сообщением, не трогая экран требований.
    Возвращает True, если запрос пришёл с экрана требований.
    """
    from keyboards.common import get_cancel_button

    data = await state.get_data()
    if not is_prerequisites_gate_message(data, callback.message.message_id):
        return False

    await callback.answer()
    sent = await callback.message.answer(text, reply_markup=get_cancel_button(lang))
    prereq_slice = prerequisites_state_slice(data)
    await state.set_state(edit_state)
    await state.update_data(
        **prereq_slice,
        last_bot_message_id=sent.message_id,
        **{FROM_PREREQ_KEY: True},
    )
    return True
