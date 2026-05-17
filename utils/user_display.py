"""Отображение возраста пользователя (динамический расчёт из даты рождения)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from utils.validators import age_from_birth_date


def get_display_age(user) -> Optional[int]:
    """Возраст на сегодня: из birth_date, иначе сохранённый age."""
    birth_raw = getattr(user, "birth_date", None)
    if birth_raw:
        try:
            birth = date.fromisoformat(str(birth_raw))
            return age_from_birth_date(birth)
        except (TypeError, ValueError):
            pass
    age = getattr(user, "age", None)
    return int(age) if age is not None else None


def format_years_ru(age: int) -> str:
    """Склонение «год / года / лет» для русского."""
    n = abs(int(age))
    if n % 100 in (11, 12, 13, 14):
        word = "лет"
    else:
        last = n % 10
        if last == 1:
            word = "год"
        elif last in (2, 3, 4):
            word = "года"
        else:
            word = "лет"
    return f"{age} {word}"


def format_age_label(age: Optional[int], lang: str = "ru") -> str:
    """Подпись возраста для карточки/профиля."""
    if age is None:
        return ""
    if lang == "ru":
        return format_years_ru(age)
    from texts.i18n import t
    return f"{age} {t(lang, 'card_years')}"
