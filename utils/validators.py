"""
Валидация данных от пользователя
"""

import re
from datetime import date
from typing import Optional

# Названия месяцев по-русски (родительный падеж) для парсинга даты
MONTH_NAMES_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def _normalize_year(y: int) -> int:
    """Двузначный год: 09 -> 2009, 25 -> 2025, 99 -> 1999."""
    if y >= 100:
        return y
    if y <= 30:  # 00–30 считаем 2000–2030
        return 2000 + y
    return 1900 + y  # 31–99 -> 1931–1999


def parse_birth_date(text: str) -> Optional[date]:
    """
    Парсит дату рождения из строки.
    Принимает: 31.07.2009, 31.07.09, 31 июля 2009, 31 июля 09.
    """
    if not text or not text.strip():
        return None
    s = text.strip()

    # 31.07.2009 или 31.07.09
    m = re.match(r"^(\d{1,2})[.\s]+(\d{1,2})[.\s]+(\d{2,4})$", s, re.IGNORECASE)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year = _normalize_year(year)
        try:
            return date(year, month, day)
        except ValueError:
            return None

    # 31 июля 2009 или 31 июля 09
    for name, month in MONTH_NAMES_RU.items():
        if name not in s.lower():
            continue
        m = re.match(r"^(\d{1,2})\s+" + re.escape(name) + r"\s+(\d{2,4})$", s, re.IGNORECASE)
        if m:
            day, year = int(m.group(1)), int(m.group(2))
            if year < 100:
                year = _normalize_year(year)
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None


def age_from_birth_date(birth: date) -> int:
    """Возраст в полных годах на сегодня."""
    today = date.today()
    age = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        age -= 1
    return age


def validate_age(age_str: str) -> Optional[int]:
    """Валидация возраста: число 1–120 или дата рождения (дд.мм.гггг / 31 июля 2009 и т.д.)."""
    s = (age_str or "").strip()
    # Сначала пробуем как число (как раньше)
    try:
        age = int(s)
        if 1 <= age <= 120:
            return age
    except ValueError:
        pass
    # Пробуем как дату рождения
    birth = parse_birth_date(s)
    if birth is None:
        return None
    age = age_from_birth_date(birth)
    if 1 <= age <= 120:
        return age
    return None


def validate_name(name: str) -> bool:
    """Валидация имени"""
    if not name or len(name.strip()) < 2:
        return False
    if len(name) > 40:
        return False
    # Проверка на допустимые символы (буквы, пробелы, дефисы)
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', name):
        return False
    return True


def validate_phone(phone: str) -> bool:
    """Валидация номера телефона"""
    # Упрощённая валидация - проверка на наличие цифр
    digits = re.sub(r'\D', '', phone)
    return len(digits) >= 10


def validate_photo(photo_id: Optional[str]) -> bool:
    """Валидация наличия фото"""
    return photo_id is not None and len(photo_id) > 0


def validate_short_description(text: str) -> bool:
    """Валидация краткого описания"""
    if not text or len(text.strip()) < 10:
        return False
    if len(text) > 180:
        return False
    return True


def validate_full_description(text: str) -> bool:
    """Валидация полного описания"""
    if not text or len(text.strip()) < 20:
        return False
    if len(text) > 500:
        return False
    return True


def validate_qualities(text: str) -> bool:
    """Валидация качеств (должно быть 3 через запятую)"""
    if not text:
        return False
    qualities = [q.strip() for q in text.split(',')]
    if len(qualities) != 3:
        return False
    # Проверяем, что каждое качество не пустое и не слишком длинное
    for quality in qualities:
        if len(quality) < 2 or len(quality) > 40:
            return False
    return True


# Диапазоны Unicode для эмодзи (упрощённо: символы-картинки)
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc Symbols, Emoticons, etc.
    "\U00002600-\U000026FF"  # Misc symbols
    "\U00002700-\U000027BF"
    "\U0001F600-\U0001F64F"
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U0001F900-\U0001F9FF"
    "]+",
    flags=re.UNICODE,
)


def text_contains_emoji(text: str) -> bool:
    """Проверка, есть ли в тексте эмодзи (нельзя вводить в текст качества — смайлик выбирается отдельно)."""
    return bool(text and _EMOJI_PATTERN.search(text))


def validate_single_quality(text: str) -> bool:
    """Валидация одного качества (2–40 символов)"""
    if not text or not text.strip():
        return False
    t = text.strip()
    return 2 <= len(t) <= 40
