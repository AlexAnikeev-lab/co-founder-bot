"""
Обработчики тестов
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.test import (
    get_test_list_keyboard,
    get_test_info_keyboard,
    get_test_answer_keyboard,
    get_test_explanation_keyboard
)
from states.test import TestStates
from repositories.user_repository import UserRepository
from repositories.database import get_session
from utils.errors import handle_error

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "tests")
async def show_tests_list(callback: CallbackQuery) -> None:
    """Показать список тестов"""
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
            
            # Проверяем, не находимся ли мы уже в списке тестов
            current_text = callback.message.text or (callback.message.caption or "")
            if "📝 <b>Тесты</b>" in current_text and "Выбери тест" in current_text:
                await callback.answer("📝 Вы уже в списке тестов", show_alert=False)
                return
            
            try:
                await callback.message.edit_text(
                    "📝 <b>Тесты</b>\n\n"
                    "Выбери тест, который хочешь пройти:",
                    reply_markup=get_test_list_keyboard()
                )
            except Exception:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.message.answer(
                    "📝 <b>Тесты</b>\n\n"
                    "Выбери тест, который хочешь пройти:",
                    reply_markup=get_test_list_keyboard()
                )
            break
            
    except Exception as e:
        logger.error(f"Ошибка в show_tests_list: {e}", exc_info=True)
        await handle_error(None, e, "show_tests_list")


@router.callback_query(F.data == "about_tests")
async def about_tests(callback: CallbackQuery) -> None:
    """Информация о тестах"""
    await callback.answer()
    try:
        await callback.message.edit_text(
            "ℹ️ <b>О тестах</b>\n\n"
            "Тесты помогут тебе лучше понять себя, свои сильные стороны и предпочтения.\n\n"
            "Результаты тестов используются для подбора совместимых партнёров.",
            reply_markup=get_test_list_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "ℹ️ <b>О тестах</b>\n\n"
            "Тесты помогут тебе лучше понять себя, свои сильные стороны и предпочтения.\n\n"
            "Результаты тестов используются для подбора совместимых партнёров.",
            reply_markup=get_test_list_keyboard()
        )


@router.callback_query(F.data.startswith("test:"))
async def show_test_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать информацию о тесте"""
    try:
        await callback.answer()
        test_id = int(callback.data.split(":")[1])
        
        # TODO: Загрузить информацию о тесте из базы данных
        try:
            await callback.message.edit_text(
                f"📋 <b>Тест {test_id}</b>\n\n"
                "Описание теста...\n\n"
                "Готов начать?",
                reply_markup=get_test_info_keyboard(test_id)
            )
        except Exception:
            await callback.message.answer(
                f"📋 <b>Тест {test_id}</b>\n\n"
                "Описание теста...\n\n"
                "Готов начать?",
                reply_markup=get_test_info_keyboard(test_id)
            )
        
    except Exception as e:
        logger.error(f"Ошибка в show_test_info: {e}", exc_info=True)
        await handle_error(None, e, "show_test_info")


@router.callback_query(F.data.startswith("start_test:"))
async def start_test(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало прохождения теста"""
    try:
        await callback.answer()
        test_id = int(callback.data.split(":")[1])
        
        # TODO: Загрузить первый вопрос из базы данных
        question_id = 1
        answers = ["Ответ 1", "Ответ 2", "Ответ 3", "Ответ 4"]
        
        await state.set_state(TestStates.answering_question)
        await state.update_data(test_id=test_id, question_id=question_id)
        
        try:
            await callback.message.edit_text(
                f"❓ <b>Вопрос {question_id}</b>\n\n"
                "Текст вопроса...",
                reply_markup=get_test_answer_keyboard(answers, question_id)
            )
        except Exception:
            await callback.message.answer(
                f"❓ <b>Вопрос {question_id}</b>\n\n"
                "Текст вопроса...",
                reply_markup=get_test_answer_keyboard(answers, question_id)
            )
        
    except Exception as e:
        logger.error(f"Ошибка в start_test: {e}", exc_info=True)
        await handle_error(None, e, "start_test")


@router.callback_query(F.data.startswith("test_answer:"))
async def process_test_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка ответа на вопрос теста"""
    try:
        await callback.answer()
        _, question_id, answer_idx = callback.data.split(":")
        question_id = int(question_id)
        answer_idx = int(answer_idx)
        
        # TODO: Сохранить ответ и проверить правильность
        is_correct = True  # Заглушка
        
        await state.update_data(
            last_answer=answer_idx,
            is_correct=is_correct
        )
        
        # TODO: Проверить, последний ли это вопрос
        is_last = False  # Заглушка
        
        try:
            await callback.message.edit_text(
                f"{'✅ Правильно!' if is_correct else '❌ Неправильно'}\n\n"
                "Пояснение ответа...",
                reply_markup=get_test_explanation_keyboard(question_id, is_last)
            )
        except Exception:
            await callback.message.answer(
                f"{'✅ Правильно!' if is_correct else '❌ Неправильно'}\n\n"
                "Пояснение ответа...",
                reply_markup=get_test_explanation_keyboard(question_id, is_last)
            )
        
    except Exception as e:
        logger.error(f"Ошибка в process_test_answer: {e}", exc_info=True)
        await handle_error(None, e, "process_test_answer")


@router.callback_query(F.data.startswith("next_question:"))
async def next_question(callback: CallbackQuery, state: FSMContext) -> None:
    """Переход к следующему вопросу"""
    try:
        await callback.answer()
        data = await state.get_data()
        test_id = data.get("test_id")
        current_question = data.get("question_id", 1)
        next_question_id = current_question + 1
        
        # TODO: Загрузить следующий вопрос из базы данных
        answers = ["Ответ 1", "Ответ 2", "Ответ 3", "Ответ 4"]
        
        await state.update_data(question_id=next_question_id)
        
        try:
            await callback.message.edit_text(
                f"❓ <b>Вопрос {next_question_id}</b>\n\n"
                "Текст вопроса...",
                reply_markup=get_test_answer_keyboard(answers, next_question_id)
            )
        except Exception:
            await callback.message.answer(
                f"❓ <b>Вопрос {next_question_id}</b>\n\n"
                "Текст вопроса...",
                reply_markup=get_test_answer_keyboard(answers, next_question_id)
            )
        
    except Exception as e:
        logger.error(f"Ошибка в next_question: {e}", exc_info=True)
        await handle_error(None, e, "next_question")


@router.callback_query(F.data == "back_to_test_info")
async def back_to_test_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Назад к информации о тесте"""
    await callback.answer()
    data = await state.get_data()
    test_id = data.get("test_id", 1)
    try:
        await callback.message.edit_text(
            f"📋 <b>Тест {test_id}</b>\n\nОписание теста...\n\nГотов начать?",
            reply_markup=get_test_info_keyboard(test_id)
        )
    except Exception:
        await callback.message.answer(
            f"📋 <b>Тест {test_id}</b>\n\nОписание теста...\n\nГотов начать?",
            reply_markup=get_test_info_keyboard(test_id)
        )


@router.callback_query(F.data == "back_to_test")
async def back_to_test(callback: CallbackQuery, state: FSMContext) -> None:
    """Назад к списку тестов"""
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(
            "📝 <b>Тесты</b>\n\nВыбери тест:",
            reply_markup=get_test_list_keyboard()
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "📝 <b>Тесты</b>\n\nВыбери тест:",
            reply_markup=get_test_list_keyboard()
        )


@router.callback_query(F.data == "tests_list")
async def back_to_tests_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Назад к списку тестов (из информации о тесте)"""
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(
            "📝 <b>Тесты</b>\n\nВыбери тест:",
            reply_markup=get_test_list_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "📝 <b>Тесты</b>\n\nВыбери тест:",
            reply_markup=get_test_list_keyboard()
        )


@router.callback_query(F.data.startswith("explanation:"))
async def show_explanation(callback: CallbackQuery) -> None:
    """Показать пояснение к ответу"""
    await callback.answer()
    try:
        await callback.message.edit_text(
            "📖 <b>Пояснение</b>\n\nПодробное объяснение ответа будет здесь."
        )
    except Exception:
        await callback.message.answer(
            "📖 <b>Пояснение</b>\n\nПодробное объяснение ответа будет здесь."
        )


@router.callback_query(F.data.startswith("finish_test:"))
async def finish_test(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершение теста и показ результатов"""
    try:
        await callback.answer()
        data = await state.get_data()
        test_id = data.get("test_id")
        
        # TODO: Рассчитать результаты теста
        try:
            await callback.message.edit_text(
                "📊 <b>Результаты теста</b>\n\n"
                "Твои результаты...",
                reply_markup=get_test_list_keyboard()
            )
        except Exception:
            await callback.message.answer(
                "📊 <b>Результаты теста</b>\n\n"
                "Твои результаты...",
                reply_markup=get_test_list_keyboard()
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в finish_test: {e}", exc_info=True)
        await handle_error(None, e, "finish_test")


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
