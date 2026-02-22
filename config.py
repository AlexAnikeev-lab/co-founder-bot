"""
Конфигурация бота
Все настройки загружаются из переменных окружения
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Корень проекта (для путей к фото и т.д.)
PROJECT_ROOT = Path(__file__).resolve().parent

# Фото по шагам: приветствие и регистрация по порядку (62, 63, …).
# Чтобы поменять картинку на шаге — измени только имя файла здесь.
REGISTRATION_PHOTOS: dict[str, str] = {
    "welcome_1": "62.png",   # Добро пожаловать в Co-founder
    "welcome_2": "63.png",   # После «Газ» — второй экран приветствия
    "age": "64.png",
    "legal": "65.png",
    "learning_mode": "65.png",
    "telegram": "66.png",
    "name": "67.png",
    "photo": "68.png",
    "quality_1": "69.png",   # сильная сторона 1
    "quality_2": "70.png",   # сильная сторона 2
    "quality_3": "71.png",   # сильная сторона 3
    "short_desc": "72.png",  # краткое описание
    "full_desc": "73.png",   # полное описание
    "success": "74.png",
}


def get_registration_photo_path(step: str) -> Optional[Path]:
    """Путь к файлу фото для шага регистрации или None, если нет/не найден."""
    filename = REGISTRATION_PHOTOS.get(step)
    if not filename:
        return None
    path = PROJECT_ROOT / "photos" / filename
    return path if path.exists() else None


# file_id (токены) после загрузки скриптом upload_photos_for_file_id.py
def _load_photo_file_ids() -> dict[str, str]:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "photos_file_ids", PROJECT_ROOT / "photos_file_ids.py"
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return getattr(mod, "REGISTRATION_PHOTO_FILE_IDS", {}) or {}
    except Exception:
        pass
    return {}


REGISTRATION_PHOTO_FILE_IDS = _load_photo_file_ids()


def get_registration_photo_file_id(step: str) -> Optional[str]:
    """file_id для шага (если уже загружали скриптом). По file_id отправка мгновенная."""
    return REGISTRATION_PHOTO_FILE_IDS.get(step)


def _load_dotenv_safe() -> None:
    """Загрузка .env с поддержкой UTF-8 и Windows (cp1251)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        load_dotenv()
        return
    for encoding in ("utf-8", "cp1251", "utf-8-sig"):
        try:
            with open(env_path, "r", encoding=encoding) as f:
                load_dotenv(stream=f)
            return
        except UnicodeDecodeError:
            continue
    load_dotenv()


_load_dotenv_safe()


class Config:
    """Класс конфигурации бота"""
    
    # Версия бота
    VERSION: str = "1.0.0"
    
    # Токен бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # ID администраторов (через запятую в .env, например: 123,456,789)
    ADMIN_IDS: tuple[int, ...] = ()
    
    # Настройки базы данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///cofounder.db")
    
    # Минимальный возраст для полного функционала
    MIN_AGE_FULL: int = 14
    
    # Настройки OpenRouter API (для ИИ функций)
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_SITE_URL: Optional[str] = os.getenv("OPENROUTER_SITE_URL", "")
    OPENROUTER_SITE_NAME: Optional[str] = os.getenv("OPENROUTER_SITE_NAME", "Co-founder Bot")
    
    # Настройки логирования
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    def __init__(self):
        """Проверка обязательных параметров и парсинг ADMIN_IDS"""
        raw = os.getenv("ADMIN_ID", "").strip()
        if raw:
            ids = []
            for part in raw.split(","):
                part = part.strip()
                if part:
                    try:
                        ids.append(int(part))
                    except ValueError:
                        pass
            self.ADMIN_IDS = tuple(ids)
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в переменных окружения")
        if not self.ADMIN_IDS:
            raise ValueError("ADMIN_ID не установлен в переменных окружения (можно несколько через запятую)")
