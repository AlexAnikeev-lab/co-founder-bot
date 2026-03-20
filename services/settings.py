"""
Настройки бота, изменяемые из админ-панели (хранятся в JSON-файле).
"""

import json
import logging
from pathlib import Path

from config import PROJECT_ROOT

logger = logging.getLogger(__name__)

SETTINGS_DIR = PROJECT_ROOT / "data"
SETTINGS_FILE = SETTINGS_DIR / "bot_settings.json"

DEFAULT_LIKES_PER_WEEK = 5
DEFAULT_BOOKMARKS_PER_WEEK = 10


def _ensure_dir() -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def _read_settings() -> dict:
    """Прочитать настройки из файла. При ошибке — вернуть дефолты."""
    if not SETTINGS_FILE.exists():
        return {
            "likes_per_week_limit": DEFAULT_LIKES_PER_WEEK,
            "bookmarks_per_week_limit": DEFAULT_BOOKMARKS_PER_WEEK,
        }
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {
                "likes_per_week_limit": DEFAULT_LIKES_PER_WEEK,
                "bookmarks_per_week_limit": DEFAULT_BOOKMARKS_PER_WEEK,
            }
        return data
    except Exception as e:
        logger.warning("Не удалось прочитать настройки из %s: %s", SETTINGS_FILE, e)
        return {
            "likes_per_week_limit": DEFAULT_LIKES_PER_WEEK,
            "bookmarks_per_week_limit": DEFAULT_BOOKMARKS_PER_WEEK,
        }


def _write_settings(data: dict) -> None:
    _ensure_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_likes_per_week_limit() -> int:
    """Текущий лимит обычных лайков в неделю (на одного пользователя)."""
    data = _read_settings()
    try:
        v = data.get("likes_per_week_limit", DEFAULT_LIKES_PER_WEEK)
        return max(0, int(v))
    except (TypeError, ValueError):
        return DEFAULT_LIKES_PER_WEEK


def set_likes_per_week_limit(limit: int) -> None:
    """Установить лимит обычных лайков в неделю. limit должен быть >= 0."""
    data = _read_settings()
    data["likes_per_week_limit"] = max(0, limit)
    _write_settings(data)


def get_bookmarks_per_week_limit() -> int:
    """Текущий лимит избранных мест (на одного пользователя).

    Исторически ключ назывался `bookmarks_per_week_limit`, но логика сейчас работает как "всего мест".
    """
    data = _read_settings()
    try:
        v = data.get("bookmarks_per_week_limit", DEFAULT_BOOKMARKS_PER_WEEK)
        return max(0, int(v))
    except (TypeError, ValueError):
        return DEFAULT_BOOKMARKS_PER_WEEK


def set_bookmarks_per_week_limit(limit: int) -> None:
    """Установить лимит избранных мест. limit должен быть >= 0."""
    data = _read_settings()
    data["bookmarks_per_week_limit"] = max(0, limit)
    _write_settings(data)
