"""
Запись подробного сравнения при совпадении (взаимный лайк) для проверки логики совместимости.
Запись в файл выполняется в потоке (run_in_executor), чтобы не блокировать event loop при нагрузке.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

# Файл в корне проекта, чтобы было удобно найти
MATCH_COMPARISON_FILE = "match_comparisons.log"

logger = logging.getLogger(__name__)


def _format_details(details: Dict[str, Any], indent: str = "  ") -> str:
    """Форматирование словаря с деталями в читаемый текст."""
    lines = []
    for key, value in details.items():
        if isinstance(value, dict) and key not in ("profile_a", "profile_b"):
            lines.append(f"{indent}{key}:")
            lines.append(_format_details(value, indent=indent + "  "))
        elif isinstance(value, list):
            lines.append(f"{indent}{key}:")
            for item in value:
                lines.append(f"{indent}  - {item}")
        else:
            lines.append(f"{indent}{key}: {value}")
    return "\n".join(lines) if lines else ""


def _write_match_log(content: str) -> None:
    """Синхронная запись в файл (вызывается из executor)."""
    with open(MATCH_COMPARISON_FILE, "a", encoding="utf-8") as f:
        f.write(content)


def log_match_comparison(
    user_a_id: int,
    user_a_name: str,
    user_b_id: int,
    user_b_name: str,
    final_score: int,
    details: Dict[str, Any],
) -> None:
    """
    Дописывает в файл подробное описание сравнения при совпадении двух пользователей.
    
    Args:
        user_a_id: telegram_id пользователя A
        user_a_name: имя пользователя A
        user_b_id: telegram_id пользователя B
        user_b_name: имя пользователя B
        final_score: итоговый процент совместимости
        details: словарь из CompatibilityService.calculate_compatibility_detailed
    """
    try:
        content = "\n".join([
            "",
            "=" * 80,
            f"СОВПАДЕНИЕ — {datetime.utcnow().isoformat()}Z",
            "=" * 80,
            f"Пользователь A: id={user_a_id}, имя={user_a_name}",
            f"Пользователь B: id={user_b_id}, имя={user_b_name}",
            f"Итоговая совместимость: {final_score}%",
            "",
            "--- Профили (баллы) ---",
            "Profile A: " + str(details.get("profile_a", {})),
            "Profile B: " + str(details.get("profile_b", {})),
            "",
            "--- Детали расчёта ---",
            _format_details({k: v for k, v in details.items() if k not in ("profile_a", "profile_b")}),
            "",
            "=" * 80,
        ]) + "\n"
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _write_match_log, content)
        except RuntimeError:
            _write_match_log(content)
    except Exception as e:
        logger.error("Ошибка записи в match_comparisons.log: %s", e, exc_info=True)
