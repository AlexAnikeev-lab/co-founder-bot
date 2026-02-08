"""
Запись расчёта совместимости в .txt при каждом показе анкеты с процентом совместимости.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from services.compatibility_service import CompatibilityService

# Путь к файлу в корне проекта (относительно этого модуля), чтобы файл всегда создавался там
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPATIBILITY_LOG_FILE = os.path.join(_BASE_DIR, "compatibility_calculation.txt")

logger = logging.getLogger(__name__)


def _format_details_for_txt(details: Dict[str, Any], indent: str = "  ") -> str:
    """Форматирование деталей расчёта в читаемый текст."""
    lines = []
    for key, value in details.items():
        if key in ("profile_a", "profile_b"):
            continue
        if isinstance(value, dict):
            lines.append(f"{indent}{key}:")
            lines.append(_format_details_for_txt(value, indent=indent + "  "))
        elif isinstance(value, list):
            lines.append(f"{indent}{key}:")
            for item in value:
                lines.append(f"{indent}  - {item}")
        else:
            lines.append(f"{indent}{key}: {value}")
    return "\n".join(lines) if lines else ""


def log_compatibility_calculation(
    viewer_telegram_id: int,
    shown_user_telegram_id: int,
    profile_viewer: Dict[str, Any],
    profile_shown: Dict[str, Any],
    viewer_name: Optional[str] = None,
    shown_name: Optional[str] = None,
) -> None:
    """
    Каждый раз при показе анкеты с совместимостью записывает в .txt файл,
    как считался процент: профили, шаги E1–E5, итог.

    Args:
        viewer_telegram_id: telegram_id того, кому показывают анкету
        shown_user_telegram_id: telegram_id того, чью анкету показывают
        profile_viewer: профиль зрителя (из тестов)
        profile_shown: профиль показываемого пользователя
        viewer_name: имя зрителя (опционально)
        shown_name: имя показываемого (опционально)
    """
    try:
        final_score, details = CompatibilityService.calculate_compatibility_detailed(
            profile_viewer, profile_shown
        )
        # Явно создаём файл в корне проекта
        with open(COMPATIBILITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write(f"ПОКАЗ АНКЕТЫ С СОВМЕСТИМОСТЬЮ — {datetime.utcnow().isoformat()}Z\n")
            f.write("=" * 80 + "\n")
            f.write(f"Кому показывают (viewer): id={viewer_telegram_id}")
            if viewer_name:
                f.write(f", имя={viewer_name}")
            f.write("\n")
            f.write(f"Кого показывают (shown):   id={shown_user_telegram_id}")
            if shown_name:
                f.write(f", имя={shown_name}")
            f.write("\n")
            f.write(f"Итоговый процент совместимости: {final_score}%\n")
            f.write("\n--- Профили (баллы) ---\n")
            f.write("Profile viewer: " + str(details.get("profile_a", {})) + "\n")
            f.write("Profile shown:   " + str(details.get("profile_b", {})) + "\n")
            f.write("\n--- Как считался процент ---\n")
            f.write("E1 — частные совместимости по факторам (ethics, goals, risk, decision, comm):\n")
            e1 = details.get("E1_scores", {})
            for k, v in e1.items():
                f.write(f"  {k}: {v}\n")
            f.write("E2 — роли (разницы d_h, d_k, d_p, similarity, role_score):\n")
            e2 = details.get("E2_roles", {})
            for k, v in e2.items():
                f.write(f"  {k}: {v}\n")
            f.write(f"E3 — базовая совместимость (веса 0.22, 0.18, 0.16, 0.14, 0.15, 0.15): {details.get('E3_base', '')}\n")
            f.write(f"E4 — штрафы (red flags): {details.get('E4_penalty', 0)}\n")
            for line in details.get("E4_penalty_details", []):
                f.write(f"  - {line}\n")
            f.write(f"E5 — итог (base - penalty): {details.get('E5_final', '')}%\n")
            f.write("=" * 80 + "\n")
        logger.info("Запись расчёта совместимости в %s", COMPATIBILITY_LOG_FILE)
    except Exception as e:
        logger.error(
            "Ошибка записи в %s: %s (полный путь: %s)",
            COMPATIBILITY_LOG_FILE,
            e,
            os.path.abspath(COMPATIBILITY_LOG_FILE),
            exc_info=True,
        )


def log_compatibility_show_minimal(
    viewer_telegram_id: int,
    shown_user_telegram_id: int,
    compatibility_percent: int,
    reason: str = "нет полных профилей теста для расчёта",
) -> None:
    """
    Записывает в .txt факт показа анкеты, когда полный расчёт невозможен (нет тестов у кого-то).
    Чтобы файл создавался при любом показе.
    """
    try:
        with open(COMPATIBILITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write(f"ПОКАЗ АНКЕТЫ — {datetime.utcnow().isoformat()}Z\n")
            f.write("=" * 80 + "\n")
            f.write(f"Кому показывают (viewer): id={viewer_telegram_id}\n")
            f.write(f"Кого показывают (shown):   id={shown_user_telegram_id}\n")
            f.write(f"Показанный процент совместимости: {compatibility_percent}%\n")
            f.write(f"Примечание: {reason}\n")
            f.write("=" * 80 + "\n")
        logger.info("Запись показа анкеты (краткая) в %s", COMPATIBILITY_LOG_FILE)
    except Exception as e:
        logger.error(
            "Ошибка записи в %s: %s (полный путь: %s)",
            COMPATIBILITY_LOG_FILE,
            e,
            os.path.abspath(COMPATIBILITY_LOG_FILE),
            exc_info=True,
        )
