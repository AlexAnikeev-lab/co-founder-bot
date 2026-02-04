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
