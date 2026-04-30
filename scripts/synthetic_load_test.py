"""
Синтетический нагрузочный тест (без Telegram API).

Проверяет, как БД переживает конкурирующие запросы/коммиты на сценарии свайпов:
- подготовка N зарегистрированных пользователей и завершённых тестов
- параллельно для M пользователей:
  - get_next_user_for_swipe(...)
  - SwipeRepository.create_swipe(..., action="like")

Запуск:
  ./.venv/bin/python scripts/synthetic_load_test.py --users 100 --concurrency 20 --iterations 5
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import statistics
import time
from dataclasses import dataclass
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic load test (no Telegram).")
    parser.add_argument("--users", type=int, default=100, help="Сколько пользователей создать для теста.")
    parser.add_argument("--iterations", type=int, default=5, help="Сколько свайпов сделать на пользователя.")
    parser.add_argument("--concurrency", type=int, default=20, help="Максимум параллельных тасков.")
    parser.add_argument("--db", type=str, default="loadtest.db", help="Файл БД для теста.")
    parser.add_argument("--base-telegram-id", type=int, default=9_000_000_000, help="Базовый Telegram ID.")
    parser.add_argument("--seed", type=int, default=42, help="Seed для воспроизводимости.")
    return parser.parse_args()


@dataclass(frozen=True)
class Stats:
    total_ops: int
    errors: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    throughput_ops_per_sec: float


def _compute_stats(durations_s: list[float], errors: int, start_wall: float, end_wall: float, ops_expected: int) -> Stats:
    durations_ms = [d * 1000.0 for d in durations_s]
    durations_ms.sort()
    total_ops = len(durations_ms)
    if not durations_ms:
        return Stats(
            total_ops=0,
            errors=errors,
            p50_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            avg_ms=0.0,
            throughput_ops_per_sec=0.0,
        )

    def pct(p: float) -> float:
        if len(durations_ms) == 1:
            return durations_ms[0]
        k = (len(durations_ms) - 1) * p
        f = int(k)
        c = min(f + 1, len(durations_ms) - 1)
        if f == c:
            return durations_ms[f]
        return durations_ms[f] * (c - k) + durations_ms[c] * (k - f)

    elapsed = max(1e-9, end_wall - start_wall)
    return Stats(
        total_ops=total_ops,
        errors=errors,
        p50_ms=pct(0.50),
        p95_ms=pct(0.95),
        p99_ms=pct(0.99),
        avg_ms=statistics.mean(durations_ms),
        throughput_ops_per_sec=total_ops / elapsed,
    )


async def _seed_data(
    users: int,
    base_telegram_id: int,
    rand: random.Random,
    *,
    async_session_maker: Any,
    user_repo: Any,
    test_repo: Any,
) -> list[int]:
    telegram_ids: list[int] = [base_telegram_id + i for i in range(users)]

    # Сидим последовательно: это не часть измерений (хотим нагрузить именно конкуренцию операций).
    for i in range(users):
        tid = telegram_ids[i]
        lang = "ru"
        # Синтетические, но валидные поля анкеты (иначе swipe query ничего не найдёт).
        qualities = "🔥 Hustler\n💡 Hacker\n🌿 Hipster"
        short_desc = f"Короткое описание {tid}"
        full_desc = f"Полное описание {tid}"

        async with async_session_maker() as session:
            u = await user_repo.create(session, telegram_id=tid, username=f"user{i}")
            await user_repo.update(
                session,
                u,
                is_registered=True,
                is_minor=False,
                ban_status="none",
                language=lang,
                short_description=short_desc,
                full_description=full_desc,
                qualities=qualities,
                subscription_active=rand.random() < 0.2,
            )

            # Синтетический завершённый тест (важно: main_test_completed=True + score-поля).
            h = rand.randint(0, 100)
            k = rand.randint(0, 100 - h)
            p = 100 - h - k

            ethics = rand.randint(0, 100)
            goals = rand.randint(0, 100)
            risk = rand.randint(0, 100)
            decision = rand.randint(0, 100)
            comm = rand.randint(0, 100)

            # main_test_completed= True и score fields нужны для calculate_compatibility.
            await test_repo.create_or_update(
                session,
                tid,
                main_test_completed=True,
                main_test_answers="{}",
                hustler_percent=h,
                hacker_percent=k,
                hipster_percent=p,
                ethics_score=ethics,
                goals_score=goals,
                risk_score=risk,
                decision_score=decision,
                comm_score=comm,
                profile_label="Hybrid",
            )

    return telegram_ids


async def _worker(
    *,
    sem: asyncio.Semaphore,
    telegram_id: int,
    iterations: int,
    async_session_maker: Any,
    user_repo: Any,
    test_repo: Any,
    swipe_repo: Any,
    get_next_user_for_swipe: Any,
    rand: random.Random,
    durations_s: list[float],
    errors_counter: list[int],
) -> None:
    async with sem:
        # current_user в get_next_user_for_swipe реально не используется по факту,
        # но храним чтобы не ломать сигнатуру.
        async with async_session_maker() as session:
            current_user = await user_repo.get_by_telegram_id(session, telegram_id)

        for _ in range(iterations):
            start = time.perf_counter()
            try:
                async with async_session_maker() as session:
                    next_data = await get_next_user_for_swipe(
                        session,
                        telegram_id,
                        current_user,
                    )
                    if not next_data:
                        break
                    next_user, _compat = next_data
                    await swipe_repo.create_swipe(session, telegram_id, next_user.telegram_id, "like")
            except Exception:
                errors_counter[0] += 1
            finally:
                end = time.perf_counter()
                durations_s.append(end - start)


async def run_test(
    *,
    users: int,
    iterations: int,
    concurrency: int,
    db_url: str,
    base_telegram_id: int,
    seed: int,
) -> Stats:
    # Важно: выставляем окружение до импорта БД.
    os.environ["DATABASE_URL"] = db_url

    # Импорты после DATABASE_URL, чтобы engine использовал тестовую БД.
    from init_db import init_database
    from repositories.database import async_session_maker
    from repositories.user_repository import UserRepository
    from repositories.test_repository import TestResultRepository
    from repositories.swipe_repository import SwipeRepository
    from handlers.swipe import get_next_user_for_swipe

    await init_database()

    rand = random.Random(seed)

    telegram_ids = await _seed_data(
        users,
        base_telegram_id,
        rand,
        async_session_maker=async_session_maker,
        user_repo=UserRepository,
        test_repo=TestResultRepository,
    )

    sem = asyncio.Semaphore(concurrency)
    durations_s: list[float] = []
    errors_counter = [0]

    start_wall = time.time()
    tasks: list[asyncio.Task[None]] = []
    for tid in telegram_ids:
        tasks.append(
            asyncio.create_task(
                _worker(
                    sem=sem,
                    telegram_id=tid,
                    iterations=iterations,
                    async_session_maker=async_session_maker,
                    user_repo=UserRepository,
                    test_repo=TestResultRepository,
                    swipe_repo=SwipeRepository,
                    get_next_user_for_swipe=get_next_user_for_swipe,
                    rand=rand,
                    durations_s=durations_s,
                    errors_counter=errors_counter,
                )
            )
        )

    await asyncio.gather(*tasks)
    end_wall = time.time()

    return _compute_stats(
        durations_s=durations_s,
        errors=errors_counter[0],
        start_wall=start_wall,
        end_wall=end_wall,
        ops_expected=users * iterations,
    )


def _print_stats(stats: Stats) -> None:
    print("\n=== Synthetic load test results ===")
    print(f"Ops (успешных/измеренных): {stats.total_ops}")
    print(f"Errors: {stats.errors}")
    print(f"Avg latency: {stats.avg_ms:.2f} ms")
    print(f"p50: {stats.p50_ms:.2f} ms")
    print(f"p95: {stats.p95_ms:.2f} ms")
    print(f"p99: {stats.p99_ms:.2f} ms")
    print(f"Throughput: {stats.throughput_ops_per_sec:.2f} ops/sec")
    print("====================================\n")


def main() -> None:
    args = _parse_args()
    # Корневая директория проекта (папка этого файла).
    root = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(root, args.db)
    db_url = f"sqlite+aiosqlite:///{db_path}"

    stats = asyncio.run(
        run_test(
            users=args.users,
            iterations=args.iterations,
            concurrency=args.concurrency,
            db_url=db_url,
            base_telegram_id=args.base_telegram_id,
            seed=args.seed,
        )
    )
    _print_stats(stats)


if __name__ == "__main__":
    main()

