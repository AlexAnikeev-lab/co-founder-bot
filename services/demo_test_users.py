"""
Демо-пользователи для тестирования: массовая генерация, удаление, диапазон telegram_id.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.admin_archive_repository import AdminUserArchive
from repositories.swipe_repository import Swipe
from repositories.test_repository import TestResult, TestResultRepository
from repositories.user_repository import User, UserRepository
from services.demo_profile_templates import ALL_TEMPLATES, DemoProfileTemplate

logger = logging.getLogger(__name__)

# Диапазон зарезервированных telegram_id для демо (не пересекается с реальными)
DEMO_TELEGRAM_ID_MIN = 9_000_000_001
DEMO_TELEGRAM_ID_MAX = 9_000_010_000
DEMO_SEED_DEFAULT_COUNT = 10
DEMO_SEED_MAX_BATCH = 50

_EXTRA_TEST_TYPES = (
    "roles_extra",
    "ethics_extra",
    "goals_extra",
    "risk_extra",
    "decision_extra",
    "comm_extra",
)


def is_demo_telegram_id(telegram_id: int) -> bool:
    """True — synthetic demo user (без уведомлений админу и т.п.)."""
    return DEMO_TELEGRAM_ID_MIN <= telegram_id <= DEMO_TELEGRAM_ID_MAX


@dataclass(frozen=True)
class DemoUserSpec:
    telegram_id: int
    language: str
    username: str
    name: str
    city: str
    phone: str
    birth_date: str
    age: int
    short_description: str
    full_description: str
    qualities: str
    hustler_percent: int
    hacker_percent: int
    hipster_percent: int
    ethics_score: int
    goals_score: int
    risk_score: int
    decision_score: int
    comm_score: int
    profile_label: str = "Hybrid"


def _demo_answer_json() -> str:
    return json.dumps({f"Q{i}": "b" for i in range(1, 11)}, ensure_ascii=False)


def _birth_date_for_index(index: int) -> tuple[str, int]:
    year = 1990 + (index % 12)
    month = (index % 12) + 1
    day = (index % 25) + 1
    birth_date = f"{year}-{month:02d}-{day:02d}"
    from datetime import date

    today = date.today()
    age = today.year - year
    if (today.month, today.day) < (month, day):
        age -= 1
    return birth_date, max(18, min(age, 45))


def build_demo_spec(telegram_id: int, template: DemoProfileTemplate, slot: int) -> DemoUserSpec:
    birth_date, age = _birth_date_for_index(slot)
    lang = template.language
    suffix = telegram_id - DEMO_TELEGRAM_ID_MIN + 1
    return DemoUserSpec(
        telegram_id=telegram_id,
        language=lang,
        username=f"demo_{lang}_{suffix}",
        name=template.name,
        city=template.city,
        phone=f"+7900{telegram_id % 10_000_000:07d}" if lang == "ru" else f"+447900{telegram_id % 10_000_000:07d}",
        birth_date=birth_date,
        age=age,
        short_description=template.short_description,
        full_description=template.full_description,
        qualities=template.qualities_block(),
        hustler_percent=template.hustler_percent,
        hacker_percent=template.hacker_percent,
        hipster_percent=template.hipster_percent,
        ethics_score=template.ethics_score,
        goals_score=template.goals_score,
        risk_score=template.risk_score,
        decision_score=template.decision_score,
        comm_score=template.comm_score,
        profile_label=template.profile_label,
    )


def _build_test_result_kwargs(spec: DemoUserSpec) -> dict[str, Any]:
    answers = _demo_answer_json()
    kwargs: dict[str, Any] = {
        "main_test_completed": True,
        "main_test_answers": answers,
        "hustler_percent": spec.hustler_percent,
        "hacker_percent": spec.hacker_percent,
        "hipster_percent": spec.hipster_percent,
        "ethics_score": spec.ethics_score,
        "goals_score": spec.goals_score,
        "risk_score": spec.risk_score,
        "decision_score": spec.decision_score,
        "comm_score": spec.comm_score,
        "profile_label": spec.profile_label,
    }
    for test_type in _EXTRA_TEST_TYPES:
        kwargs[f"{test_type}_completed"] = True
        kwargs[f"{test_type}_answers"] = answers
    return kwargs


async def count_demo_users(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(
            User.telegram_id >= DEMO_TELEGRAM_ID_MIN,
            User.telegram_id <= DEMO_TELEGRAM_ID_MAX,
        )
    )
    return int(result.scalar() or 0)


async def _existing_demo_ids(session: AsyncSession) -> set[int]:
    result = await session.execute(
        select(User.telegram_id).where(
            User.telegram_id >= DEMO_TELEGRAM_ID_MIN,
            User.telegram_id <= DEMO_TELEGRAM_ID_MAX,
        )
    )
    return {int(row[0]) for row in result.all()}


async def allocate_demo_telegram_ids(session: AsyncSession, count: int) -> list[int]:
    if count < 1:
        return []
    existing = await _existing_demo_ids(session)
    ids: list[int] = []
    tid = DEMO_TELEGRAM_ID_MIN
    while len(ids) < count and tid <= DEMO_TELEGRAM_ID_MAX:
        if tid not in existing:
            ids.append(tid)
        tid += 1
    if len(ids) < count:
        raise ValueError(
            f"Достигнут лимит демо-пользователей ({DEMO_TELEGRAM_ID_MAX - DEMO_TELEGRAM_ID_MIN + 1}). "
            f"Сейчас в базе: {len(existing)}. Удалите лишних: /delete_test_users"
        )
    return ids


async def upsert_demo_test_user(session: AsyncSession, spec: DemoUserSpec) -> tuple[User, bool]:
    user = await UserRepository.get_by_telegram_id(session, spec.telegram_id)
    created = user is None
    if created:
        user = await UserRepository.create(
            session,
            telegram_id=spec.telegram_id,
            username=spec.username,
        )
    await UserRepository.update(
        session,
        user,
        username=spec.username,
        name=spec.name,
        city=spec.city,
        phone=spec.phone,
        birth_date=spec.birth_date,
        age=spec.age,
        short_description=spec.short_description,
        full_description=spec.full_description,
        qualities=spec.qualities,
        is_minor=False,
        is_registered=True,
        ban_status="none",
        language=spec.language,
        subscription_active=False,
        super_like_used=False,
    )
    await TestResultRepository.create_or_update(
        session,
        spec.telegram_id,
        **_build_test_result_kwargs(spec),
    )
    await session.refresh(user)
    return user, created


async def seed_demo_test_users(session: AsyncSession, count: int) -> list[tuple[DemoUserSpec, User, bool]]:
    """Добавить count новых демо-пользователей (чередование RU/EN, шаблоны из пула)."""
    count = min(max(1, count), DEMO_SEED_MAX_BATCH)
    new_ids = await allocate_demo_telegram_ids(session, count)
    results: list[tuple[DemoUserSpec, User, bool]] = []
    for i, telegram_id in enumerate(new_ids):
        template = ALL_TEMPLATES[i % len(ALL_TEMPLATES)]
        spec = build_demo_spec(telegram_id, template, slot=i + int(telegram_id))
        user, created = await upsert_demo_test_user(session, spec)
        results.append((spec, user, created))
    return results


async def delete_all_demo_users(session: AsyncSession) -> dict[str, int]:
    """Удалить всех демо-пользователей и связанные свайпы/тесты/архив."""
    demo_range = and_(
        User.telegram_id >= DEMO_TELEGRAM_ID_MIN,
        User.telegram_id <= DEMO_TELEGRAM_ID_MAX,
    )
    id_range_swipe = lambda col: and_(col >= DEMO_TELEGRAM_ID_MIN, col <= DEMO_TELEGRAM_ID_MAX)

    users_count = await count_demo_users(session)

    swipes_result = await session.execute(
        delete(Swipe).where(
            or_(
                id_range_swipe(Swipe.swiper_id),
                id_range_swipe(Swipe.swiped_id),
            )
        )
    )
    tests_result = await session.execute(
        delete(TestResult).where(
            and_(
                TestResult.user_id >= DEMO_TELEGRAM_ID_MIN,
                TestResult.user_id <= DEMO_TELEGRAM_ID_MAX,
            )
        )
    )
    archive_result = await session.execute(
        delete(AdminUserArchive).where(
            and_(
                AdminUserArchive.telegram_id >= DEMO_TELEGRAM_ID_MIN,
                AdminUserArchive.telegram_id <= DEMO_TELEGRAM_ID_MAX,
            )
        )
    )
    users_result = await session.execute(delete(User).where(demo_range))
    await session.commit()

    return {
        "users": users_result.rowcount or users_count,
        "swipes": swipes_result.rowcount or 0,
        "tests": tests_result.rowcount or 0,
        "archive": archive_result.rowcount or 0,
    }


def format_demo_users_seed_report(
    results: list[tuple[DemoUserSpec, User, bool]],
    *,
    total_in_db: int,
) -> str:
    created = sum(1 for _s, _u, c in results if c)
    lines = [
        f"✅ <b>Добавлено демо: {len(results)}</b> (новых: {created})",
        f"Всего демо в базе: <b>{total_in_db}</b>",
        "",
    ]
    for spec, _user, _ in results[:8]:
        flag = "🇷🇺" if spec.language == "ru" else "🇬🇧"
        lines.append(
            f"{flag} <b>{spec.name}</b> · {spec.city}\n"
            f"ID: <code>{spec.telegram_id}</code>"
        )
    if len(results) > 8:
        lines.append(f"… и ещё {len(results) - 8}")
    lines.extend(
        [
            "",
            "Команды:",
            "• <code>/add_test_user 10</code> — добавить 10",
            "• <code>/delete_test_users</code> — удалить всех",
            "Уведомления «Новый пользователь» для демо не отправляются.",
        ]
    )
    return "\n".join(lines)


def format_demo_users_delete_report(stats: dict[str, int]) -> str:
    return (
        "🗑 <b>Демо-пользователи удалены</b>\n\n"
        f"Пользователей: {stats.get('users', 0)}\n"
        f"Свайпов: {stats.get('swipes', 0)}\n"
        f"Тестов: {stats.get('tests', 0)}\n"
        f"Архив: {stats.get('archive', 0)}"
    )


def format_demo_users_menu(total: int) -> str:
    max_slots = DEMO_TELEGRAM_ID_MAX - DEMO_TELEGRAM_ID_MIN + 1
    return (
        "🧪 <b>Демо-пользователи</b>\n\n"
        f"Сейчас в базе: <b>{total}</b> из {max_slots}\n"
        f"Шаблонов анкет: {len(ALL_TEMPLATES)} (RU + EN, компании в «кавычках»)\n\n"
        "Добавление — новые ID в диапазоне 9000000001–9000010000.\n"
        "Уведомления админам о «новом пользователе» для демо <b>не</b> приходят."
    )
