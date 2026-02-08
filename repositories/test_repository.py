"""
Репозиторий для работы с тестами и результатами
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from repositories.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import json


class TestResult(Base):
    """Модель результатов теста пользователя"""
    __tablename__ = "test_results"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)  # telegram_id пользователя
    
    # Основной тест (10 вопросов)
    main_test_answers: Mapped[Optional[str]] = mapped_column(default=None)  # JSON: {"Q1": "a", "Q2": "b", ...}
    main_test_completed: Mapped[bool] = mapped_column(default=False)
    
    # Дополнительные тесты (каждый по 10 вопросов)
    roles_extra_answers: Mapped[Optional[str]] = mapped_column(default=None)  # JSON
    roles_extra_completed: Mapped[bool] = mapped_column(default=False)
    
    ethics_extra_answers: Mapped[Optional[str]] = mapped_column(default=None)  # JSON
    ethics_extra_completed: Mapped[bool] = mapped_column(default=False)
    
    goals_extra_answers: Mapped[Optional[str]] = mapped_column(default=None)  # JSON
    goals_extra_completed: Mapped[bool] = mapped_column(default=False)
    
    risk_extra_answers: Mapped[Optional[str]] = mapped_column(default=None)  # JSON
    risk_extra_completed: Mapped[bool] = mapped_column(default=False)
    
    decision_extra_answers: Mapped[Optional[str]] = mapped_column(default=None)  # JSON
    decision_extra_completed: Mapped[bool] = mapped_column(default=False)
    
    comm_extra_answers: Mapped[Optional[str]] = mapped_column(default=None)  # JSON
    comm_extra_completed: Mapped[bool] = mapped_column(default=False)
    
    # Рассчитанные профили (0-100)
    hustler_percent: Mapped[Optional[int]] = mapped_column(default=None)
    hacker_percent: Mapped[Optional[int]] = mapped_column(default=None)
    hipster_percent: Mapped[Optional[int]] = mapped_column(default=None)
    
    ethics_score: Mapped[Optional[int]] = mapped_column(default=None)  # 0-100
    goals_score: Mapped[Optional[int]] = mapped_column(default=None)  # 0-100
    risk_score: Mapped[Optional[int]] = mapped_column(default=None)  # 0-100
    decision_score: Mapped[Optional[int]] = mapped_column(default=None)  # 0-100
    comm_score: Mapped[Optional[int]] = mapped_column(default=None)  # 0-100
    
    # Лейбл профиля
    profile_label: Mapped[Optional[str]] = mapped_column(default=None)  # "Hustler", "Hacker", "Hipster", "Hybrid"
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class TestResultRepository:
    """Репозиторий для работы с результатами тестов"""
    
    @staticmethod
    def _get_field_name(test_type: str, field_suffix: str = "answers") -> str:
        """
        Преобразование типа теста в имя поля в базе данных
        
        Args:
            test_type: Тип теста (main, roles_extra, ethics_extra, etc.)
            field_suffix: Суффикс поля (answers или completed)
        
        Returns:
            Имя поля в базе данных
        """
        # Маппинг типов тестов на имена полей
        field_mapping = {
            "main": "main_test",
            "roles_extra": "roles_extra",
            "ethics_extra": "ethics_extra",
            "goals_extra": "goals_extra",
            "risk_extra": "risk_extra",
            "decision_extra": "decision_extra",
            "comm_extra": "comm_extra"
        }
        
        base_name = field_mapping.get(test_type, test_type)
        return f"{base_name}_{field_suffix}"
    
    @staticmethod
    async def get_by_user_id(session: AsyncSession, user_id: int) -> Optional[TestResult]:
        """Получение результатов теста по user_id (telegram_id)"""
        result = await session.execute(
            select(TestResult).where(TestResult.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_or_update(session: AsyncSession, user_id: int, **kwargs) -> TestResult:
        """Создание или обновление результатов теста"""
        test_result = await TestResultRepository.get_by_user_id(session, user_id)
        
        if test_result is None:
            test_result = TestResult(user_id=user_id)
            session.add(test_result)
        
        # Обновление полей
        for key, value in kwargs.items():
            if hasattr(test_result, key):
                # Если значение - словарь или список, преобразуем в JSON
                if isinstance(value, (dict, list)):
                    setattr(test_result, key, json.dumps(value, ensure_ascii=False))
                else:
                    setattr(test_result, key, value)
        
        test_result.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(test_result)
        return test_result
    
    @staticmethod
    async def get_answers_dict(session: AsyncSession, user_id: int, test_type: str) -> Optional[dict]:
        """Получение ответов теста в виде словаря"""
        test_result = await TestResultRepository.get_by_user_id(session, user_id)
        if not test_result:
            return None
        
        field_name = TestResultRepository._get_field_name(test_type, "answers")
        answers_json = getattr(test_result, field_name, None)
        
        if answers_json:
            return json.loads(answers_json)
        return None
    
    @staticmethod
    async def save_answer(session: AsyncSession, user_id: int, test_type: str, question_num: int, answer: str) -> TestResult:
        """Сохранение ответа на вопрос"""
        test_result = await TestResultRepository.get_by_user_id(session, user_id)
        
        if test_result is None:
            test_result = TestResult(user_id=user_id)
            session.add(test_result)
        
        # Определяем поле для сохранения
        field_name = TestResultRepository._get_field_name(test_type, "answers")
        answers_json = getattr(test_result, field_name, None)
        
        if answers_json:
            answers = json.loads(answers_json)
        else:
            answers = {}
        
        # Сохраняем ответ
        answers[f"Q{question_num}"] = answer
        
        setattr(test_result, field_name, json.dumps(answers, ensure_ascii=False))
        test_result.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(test_result)
        return test_result
    
    @staticmethod
    async def mark_completed(session: AsyncSession, user_id: int, test_type: str) -> TestResult:
        """Отметить тест как завершенный"""
        test_result = await TestResultRepository.get_by_user_id(session, user_id)
        
        if test_result is None:
            test_result = TestResult(user_id=user_id)
            session.add(test_result)
        
        field_name = TestResultRepository._get_field_name(test_type, "completed")
        setattr(test_result, field_name, True)
        test_result.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(test_result)
        return test_result

    @staticmethod
    async def delete_by_user_id(session: AsyncSession, user_id: int) -> None:
        """Удалить все результаты тестов пользователя (при удалении профиля)."""
        await session.execute(delete(TestResult).where(TestResult.user_id == user_id))
        await session.commit()
