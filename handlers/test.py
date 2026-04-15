"""
Обработчики тестов
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from keyboards.test import (
    get_test_list_keyboard,
    get_test_info_keyboard,
    get_test_answer_keyboard,
    get_test_progress_keyboard,
    get_test_results_keyboard
)
from states.test import TestStates
from repositories.user_repository import UserRepository
from repositories.test_repository import TestResultRepository
from repositories.database import get_session
from texts.i18n import t, text_options
from utils.errors import handle_error
from texts.test_questions import TEST_TYPES
from services.compatibility_service import CompatibilityService

logger = logging.getLogger(__name__)
router = Router()

_TEST_I18N_KEYS = {
    "main": ("test_main_name", "test_main_desc"),
    "roles_extra": ("test_roles_name", "test_roles_desc"),
    "ethics_extra": ("test_ethics_name", "test_ethics_desc"),
    "goals_extra": ("test_goals_name", "test_goals_desc"),
    "risk_extra": ("test_risk_name", "test_risk_desc"),
    "decision_extra": ("test_decision_name", "test_decision_desc"),
    "comm_extra": ("test_comm_name", "test_comm_desc"),
}


def _get_test_name(test_type: str, lang: str) -> str:
    keys = _TEST_I18N_KEYS.get(test_type, ("test_main_name", "test_main_desc"))
    return t(lang, keys[0])


def _get_test_description(test_type: str, lang: str) -> str:
    keys = _TEST_I18N_KEYS.get(test_type, ("test_main_name", "test_main_desc"))
    return t(lang, keys[1])


async def _get_tests_list_text_and_keyboard(user_id: int):
    """Текст и клавиатура списка тестов (язык из пользователя). Возвращает (text, keyboard) или (None, None)."""
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if not user or not user.is_registered:
            return None, None
        lang = getattr(user, "language", None) or "ru"
        test_result = await TestResultRepository.get_by_user_id(session, user_id)
        main_test_completed = test_result.main_test_completed if test_result else False
        text = t(lang, "tests_title") + "\n\n" + t(lang, "tests_intro")
        if not main_test_completed:
            text += t(lang, "tests_main_label")
        text += t(lang, "tests_extra_label")
        return text, get_test_list_keyboard(main_test_completed=main_test_completed, lang=lang)
    return None, None


@router.message(F.text.in_(text_options("profile_tests")))
async def show_tests_list_from_message(message: Message, state: FSMContext) -> None:
    """Показать список тестов по кнопке из меню профиля (ru/en)."""
    try:
        await message.delete()
    except Exception:
        pass
    try:
        await state.update_data(in_profile=True, profile_screen="tests")
        user_id = message.from_user.id if message.from_user else 0
        text, kb = await _get_tests_list_text_and_keyboard(user_id)
        if text is None:
            data = await state.get_data()
            _lang = data.get("language", "ru")
            await message.answer(t(_lang, "not_registered_use_start"))
            return
        sent = await message.answer(text, reply_markup=kb)
        await state.update_data(last_bot_message_id=sent.message_id)
    except Exception as e:
        logger.error(f"Ошибка в show_tests_list_from_message: {e}", exc_info=True)
        await handle_error(None, e, "show_tests_list_from_message")


@router.callback_query(F.data == "tests")
async def show_tests_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список тестов. Удаляем сообщение «Выберите раздел» при переходе из профиля."""
    try:
        await callback.answer()
        data = await state.get_data()
        section_mid = data.get("profile_section_message_id")
        chat_id = callback.message.chat.id
        bot = callback.bot
        await state.clear()

        if section_mid:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=section_mid)
            except Exception:
                pass

        text, kb = await _get_tests_list_text_and_keyboard(callback.from_user.id)

        if text is None:
            _lang = await _get_user_lang(callback.from_user.id)
            err = t(_lang, "not_registered_use_start")
            try:
                await callback.message.edit_text(err)
            except Exception:
                await callback.message.answer(err)
            return

        try:
            await callback.message.edit_text(
                text,
                reply_markup=kb
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=kb)
    except Exception as e:
        logger.error(f"Ошибка в show_tests_list: {e}", exc_info=True)
        await handle_error(None, e, "show_tests_list")


async def _get_user_lang(user_id: int) -> str:
    lang = "ru"
    async for session in get_session():
        user = await UserRepository.get_by_telegram_id(session, user_id)
        if user:
            lang = getattr(user, "language", None) or "ru"
        break
    return lang


@router.callback_query(F.data == "about_tests")
async def about_tests(callback: CallbackQuery) -> None:
    """Информация о тестах (язык ru/en)."""
    await callback.answer()
    try:
        lang = await _get_user_lang(callback.from_user.id)
        main_test_completed = False
        async for session in get_session():
            test_result = await TestResultRepository.get_by_user_id(session, callback.from_user.id)
            main_test_completed = test_result.main_test_completed if test_result else False
            break
        text = t(lang, "tests_about_title") + "\n\n" + t(lang, "tests_about_text")
        # Всегда пытаемся редактировать сообщение
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_test_list_keyboard(main_test_completed=main_test_completed, lang=lang)
            )
        except Exception as e:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                reply_markup=get_test_list_keyboard(main_test_completed=main_test_completed, lang=lang)
            )
    except Exception as e:
        logger.error(f"Ошибка в about_tests: {e}", exc_info=True)
        await handle_error(None, e, "about_tests")


@router.callback_query(F.data.startswith("test:"))
async def show_test_info(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать информацию о тесте (язык ru/en)."""
    try:
        await callback.answer()
        lang = await _get_user_lang(callback.from_user.id)
        test_type = callback.data.split(":")[1]

        if test_type not in TEST_TYPES:
            await callback.answer(t(lang, "test_not_found"), show_alert=True)
            return

        test_info = TEST_TYPES[test_type]
        name = _get_test_name(test_type, lang)
        desc = _get_test_description(test_type, lang)
        text = (
            f"📋 <b>{name}</b>\n\n"
            f"{desc}\n\n"
            f"{t(lang, 'test_info_questions_count')} {test_info['total_questions']}\n\n"
            f"{t(lang, 'test_info_ready')}"
        )
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_test_info_keyboard(test_type, lang=lang)
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                reply_markup=get_test_info_keyboard(test_type, lang=lang)
            )
        
    except Exception as e:
        logger.error(f"Ошибка в show_test_info: {e}", exc_info=True)
        await handle_error(None, e, "show_test_info")


@router.callback_query(F.data.startswith("start_test:"))
async def start_test(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало прохождения теста"""
    try:
        test_type = callback.data.split(":")[1]
        
        if test_type not in TEST_TYPES:
            lang = await _get_user_lang(callback.from_user.id)
            await callback.answer(t(lang, "test_not_found"), show_alert=True)
            return

        lang = await _get_user_lang(callback.from_user.id)
        # Проверяем, не пройден ли уже тест (основной тест перепройти нельзя)
        async for session in get_session():
            test_result = await TestResultRepository.get_by_user_id(
                session,
                callback.from_user.id
            )
            completed_field = TestResultRepository._get_field_name(test_type, "completed")
            if test_result and getattr(test_result, completed_field, False):
                if test_type == "main":
                    await callback.answer(
                        t(lang, "test_main_already_completed"),
                        show_alert=True
                    )
                    return
                await callback.answer(
                    t(lang, "test_already_completed"),
                    show_alert=True
                )
                return
            break
        
        # Ответ на callback один раз — убираем «часики» у пользователя
        await callback.answer()
        await state.clear()
        # Инициализируем состояние
        await state.set_state(TestStates.answering_question)
        await state.update_data(
            test_type=test_type,
            current_question=1,
            answers={}
        )
        # Показываем первый вопрос
        await show_question(callback, state, test_type, 1)
        
    except Exception as e:
        logger.error(f"Ошибка в start_test: {e}", exc_info=True)
        await handle_error(None, e, "start_test")


async def show_question(
    callback: CallbackQuery,
    state: FSMContext,
    test_type: str,
    question_num: int
) -> None:
    """Показать вопрос теста"""
    try:
        test_info = TEST_TYPES[test_type]
        questions = test_info["questions"]
        
        if question_num not in questions:
            lang = await _get_user_lang(callback.from_user.id)
            await callback.answer(t(lang, "test_question_not_found"), show_alert=True)
            return
        
        question_data = questions[question_num]
        is_scale = question_data.get("scale", False)
        total_questions = test_info["total_questions"]
        lang = await _get_user_lang(callback.from_user.id)

        from texts.test_questions import get_question_and_answers_localized
        q_text, answers_loc = get_question_and_answers_localized(test_type, question_num, question_data, lang)
        if answers_loc is not None:
            answers = answers_loc
        elif is_scale:
            scale_labels = question_data.get("scale_labels", {})
            answers = {str(i): scale_labels.get(str(i), str(i)) for i in range(1, 6)}
        else:
            answers = question_data["answers"]

        if is_scale:
            await state.set_state(TestStates.answering_scale)
        else:
            await state.set_state(TestStates.answering_question)

        text = t(lang, "test_question_format").format(
            num=question_num, total=total_questions, text=q_text
        )

        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_test_answer_keyboard(
                    answers, question_num, test_type, is_scale=is_scale, lang=lang
                )
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                reply_markup=get_test_answer_keyboard(
                    answers, question_num, test_type, is_scale=is_scale, lang=lang
                )
            )
    except Exception as e:
        logger.error(f"Ошибка в show_question: {e}", exc_info=True)
        await handle_error(None, e, "show_question")


@router.callback_query(F.data.startswith("test_answer:"))
async def process_test_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка ответа на вопрос теста"""
    try:
        await callback.answer()
        parts = callback.data.split(":")
        test_type = parts[1]
        question_num = int(parts[2])
        answer = parts[3]
        
        # Сохраняем ответ
        data = await state.get_data()
        answers = data.get("answers", {})
        answers[f"Q{question_num}"] = answer
        
        await state.update_data(answers=answers)
        
        # Сохраняем в базу данных
        async for session in get_session():
            await TestResultRepository.save_answer(
                session,
                callback.from_user.id,
                test_type,
                question_num,
                answer
            )
            break
        
        # Проверяем, последний ли это вопрос
        test_info = TEST_TYPES[test_type]
        total_questions = test_info["total_questions"]
        is_last = question_num >= total_questions
        
        if is_last:
            await finish_test(callback, state, test_type)
        else:
            # Сразу показываем следующий вопрос без подтверждения
            next_num = question_num + 1
            await state.update_data(current_question=next_num)
            await show_question(callback, state, test_type, next_num)
        
    except Exception as e:
        logger.error(f"Ошибка в process_test_answer: {e}", exc_info=True)
        await handle_error(None, e, "process_test_answer")


@router.callback_query(F.data.startswith("next_question:"))
async def next_question(callback: CallbackQuery, state: FSMContext) -> None:
    """Переход к следующему вопросу"""
    try:
        await callback.answer()
        parts = callback.data.split(":")
        test_type = parts[1]
        next_question_num = int(parts[2])
        
        await state.update_data(current_question=next_question_num)
        
        await show_question(callback, state, test_type, next_question_num)
        
    except Exception as e:
        logger.error(f"Ошибка в next_question: {e}", exc_info=True)
        await handle_error(None, e, "next_question")


@router.callback_query(F.data.startswith("prev_question:"))
async def prev_question(callback: CallbackQuery, state: FSMContext) -> None:
    """Переход к предыдущему вопросу"""
    try:
        await callback.answer()
        parts = callback.data.split(":")
        test_type = parts[1]
        prev_question_num = int(parts[2])

        await state.update_data(current_question=prev_question_num)
        await show_question(callback, state, test_type, prev_question_num)

    except Exception as e:
        logger.error(f"Ошибка в prev_question: {e}", exc_info=True)
        await handle_error(None, e, "prev_question")


@router.callback_query(F.data.startswith("finish_test:"))
async def finish_test_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершение теста по кнопке"""
    try:
        await callback.answer()
        test_type = callback.data.split(":")[1]
        await finish_test(callback, state, test_type)
    except Exception as e:
        logger.error(f"Ошибка в finish_test_handler: {e}", exc_info=True)
        await handle_error(None, e, "finish_test_handler")


async def finish_test(
    callback: CallbackQuery,
    state: FSMContext,
    test_type: str
) -> None:
    """Завершение теста и расчет результатов"""
    try:
        data = await state.get_data()
        answers = data.get("answers", {})
        
        # Отмечаем тест как завершенный
        async for session in get_session():
            await TestResultRepository.mark_completed(
                session,
                callback.from_user.id,
                test_type
            )
            break
        
        # Рассчитываем профиль, если основной тест пройден
        async for session in get_session():
            test_result = await TestResultRepository.get_by_user_id(
                session,
                callback.from_user.id
            )
            if test_result and test_result.main_test_completed:
                await calculate_and_save_profile(callback.from_user.id)
            break
        
        lang = await _get_user_lang(callback.from_user.id)
        text = (
            f"{t(lang, 'test_completed_title')}\n\n"
            f"{t(lang, 'test_completed_thanks')}"
        )
        if test_type == "main":
            text += f"\n\n{t(lang, 'test_completed_profile_saved')}"
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_test_results_keyboard(lang=lang)
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                reply_markup=get_test_results_keyboard(lang=lang)
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в finish_test: {e}", exc_info=True)
        await handle_error(None, e, "finish_test")


async def calculate_and_save_profile(user_id: int) -> None:
    """Рассчитать и сохранить профиль пользователя"""
    try:
        async for session in get_session():
            test_result = await TestResultRepository.get_by_user_id(session, user_id)
            
            if not test_result:
                return
            
            # Получаем ответы основного теста
            main_answers_json = test_result.main_test_answers
            if not main_answers_json:
                return
            
            import json
            main_answers = json.loads(main_answers_json)
            
            # Рассчитываем профиль по основному тесту
            main_profile = CompatibilityService.calculate_main_test_profile(main_answers)
            
            # Получаем ответы дополнительных тестов (если есть)
            roles_extra = None
            if test_result.roles_extra_completed and test_result.roles_extra_answers:
                roles_answers = json.loads(test_result.roles_extra_answers)
                roles_extra = CompatibilityService.calculate_roles_extra(roles_answers)
            
            ethics_extra = None
            if test_result.ethics_extra_completed and test_result.ethics_extra_answers:
                ethics_answers = json.loads(test_result.ethics_extra_answers)
                ethics_extra = CompatibilityService.calculate_extra_test_score("ethics_extra", ethics_answers)
            
            goals_extra = None
            if test_result.goals_extra_completed and test_result.goals_extra_answers:
                goals_answers = json.loads(test_result.goals_extra_answers)
                goals_extra = CompatibilityService.calculate_extra_test_score("goals_extra", goals_answers)
            
            risk_extra = None
            if test_result.risk_extra_completed and test_result.risk_extra_answers:
                risk_answers = json.loads(test_result.risk_extra_answers)
                risk_extra = CompatibilityService.calculate_extra_test_score("risk_extra", risk_answers)
            
            decision_extra = None
            if test_result.decision_extra_completed and test_result.decision_extra_answers:
                decision_answers = json.loads(test_result.decision_extra_answers)
                decision_extra = CompatibilityService.calculate_extra_test_score("decision_extra", decision_answers)
            
            comm_extra = None
            if test_result.comm_extra_completed and test_result.comm_extra_answers:
                comm_answers = json.loads(test_result.comm_extra_answers)
                comm_extra = CompatibilityService.calculate_extra_test_score("comm_extra", comm_answers)
            
            # Рассчитываем финальный профиль
            final_profile = CompatibilityService.calculate_final_profile(
                main_profile,
                roles_extra=roles_extra,
                ethics_extra=ethics_extra,
                goals_extra=goals_extra,
                risk_extra=risk_extra,
                decision_extra=decision_extra,
                comm_extra=comm_extra
            )
            
            # Сохраняем профиль
            await TestResultRepository.create_or_update(
                session,
                user_id,
                hustler_percent=final_profile["hustler_percent"],
                hacker_percent=final_profile["hacker_percent"],
                hipster_percent=final_profile["hipster_percent"],
                ethics_score=final_profile["ethics_score"],
                goals_score=final_profile["goals_score"],
                risk_score=final_profile["risk_score"],
                decision_score=final_profile["decision_score"],
                comm_score=final_profile["comm_score"],
                profile_label=final_profile["profile_label"]
            )
            
            break
            
    except Exception as e:
        logger.error(f"Ошибка в calculate_and_save_profile: {e}", exc_info=True)
        raise


def register_handlers(dp) -> None:
    """Регистрация обработчиков"""
    dp.include_router(router)
