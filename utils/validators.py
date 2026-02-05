"""
Валидация данных от пользователя
"""

import re
from typing import Optional


def validate_age(age_str: str) -> Optional[int]:
    """Валидация возраста"""
    try:
        age = int(age_str)
        if 1 <= age <= 120:
            return age
        return None
    except ValueError:
        return None


def validate_name(name: str) -> bool:
    """Валидация имени"""
    if not name or len(name.strip()) < 2:
        return False
    if len(name) > 50:
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
    if len(text) > 200:
        return False
    return True


def validate_full_description(text: str) -> bool:
    """Валидация полного описания"""
    if not text or len(text.strip()) < 20:
        return False
    if len(text) > 1000:
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
        if len(quality) < 2 or len(quality) > 50:
            return False
    return True
