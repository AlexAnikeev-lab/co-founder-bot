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

# Фото по шагам: приветствие и регистрация (русская версия — папка photos/).
REGISTRATION_PHOTOS: dict[str, str] = {
    "welcome_1": "62.png",
    "welcome_2": "63.png",
    "age": "64.png",
    "legal": "65.png",
    "learning_mode": "65.png",
    "telegram": "66.png",
    "name": "67.png",
    "photo": "68.png",
    "city": "gorod.png",
    "quality_1": "69.png",
    "quality_2": "70.png",
    "quality_3": "71.png",
    "short_desc": "72.png",
    "full_desc": "73.png",
    "success": "74.png",
}

# Папка с фото на английском (при lang="en"). Имена файлов — те же, что в REGISTRATION_PHOTOS,
# если не переопределены в REGISTRATION_PHOTOS_EN.
PHOTOS_DIR_EN = "photos_engls"
# Маппинг шагов регистрации (en) на файлы в photos_engls:
# 63(1) приветствие, 65(1) найти партнёра, 67 дата рождения, 69 правила, 71 телефон,
# 73 имя, 75 фото, 77–81 качества 1–3, 83 краткая био, 85 детальное, 87 о тестах, 89 главный тест.
REGISTRATION_PHOTOS_EN: dict[str, str] = {
    "welcome_1": "63 (1).png",      # приветствие
    "welcome_2": "65 (1).png",       # ты можешь найти бизнес-партнёра
    "age": "67 (1).png",             # дата рождения (64(1) удалён)
    "legal": "69 (1).png",           # правила
    "learning_mode": "69 (1).png",   # правила (тот же экран)
    "telegram": "71 (1).png",        # номер телефона
    "name": "73 (1).png",            # имя
    "photo": "75 (1).png",           # фото
    "city": "city.png",              # город
    "quality_1": "77.png",           # сильная сторона 1
    "quality_2": "79.png",           # сильная сторона 2
    "quality_3": "81.png",           # сильная сторона 3
    "short_desc": "83.png",          # краткая био
    "full_desc": "85.png",           # детальное описание
    "success": "87.png",             # о тестах
    # 89.png — главный тест (используется в тестах, не в шагах регистрации)
}


def get_registration_photo_path(step: str, lang: str = "ru") -> Optional[Path]:
    """Путь к файлу фото для шага регистрации по языку (ru → photos/, en → photos_engls/)."""
    if lang == "en":
        folder = PHOTOS_DIR_EN
        filename = REGISTRATION_PHOTOS_EN.get(step) or REGISTRATION_PHOTOS.get(step)
    else:
        folder = "photos"
        filename = REGISTRATION_PHOTOS.get(step)
    if not filename:
        return None
    path = PROJECT_ROOT / folder / filename
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


def _load_photo_file_ids_en() -> dict[str, str]:
    """Загрузка file_id для английских фото (REGISTRATION_PHOTO_FILE_IDS_EN в photos_file_ids.py)."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "photos_file_ids", PROJECT_ROOT / "photos_file_ids.py"
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return getattr(mod, "REGISTRATION_PHOTO_FILE_IDS_EN", {}) or {}
    except Exception:
        pass
    return {}


REGISTRATION_PHOTO_FILE_IDS = _load_photo_file_ids()
REGISTRATION_PHOTO_FILE_IDS_EN = _load_photo_file_ids_en()
EVENTS_LIST_PHOTO_FILE_ID_RU = REGISTRATION_PHOTO_FILE_IDS.get("events")
EVENTS_LIST_PHOTO_FILE_ID_EN = REGISTRATION_PHOTO_FILE_IDS_EN.get("events") or REGISTRATION_PHOTO_FILE_IDS.get("events_en")


def get_registration_photo_file_id(step: str, lang: str = "ru") -> Optional[str]:
    """file_id для шага и языка (если загружали скриптом). По file_id отправка мгновенная."""
    if lang == "en":
        return REGISTRATION_PHOTO_FILE_IDS_EN.get(step) or REGISTRATION_PHOTO_FILE_IDS.get(step)
    return REGISTRATION_PHOTO_FILE_IDS.get(step)


def get_events_list_photo_file_id(lang: str = "ru") -> Optional[str]:
    """
    file_id обложки для экрана «Мероприятия».
    Для ru: REGISTRATION_PHOTO_FILE_IDS["events"].
    Для en: REGISTRATION_PHOTO_FILE_IDS_EN["events"] (или fallback на ru).
    """
    if lang == "en":
        return EVENTS_LIST_PHOTO_FILE_ID_EN or EVENTS_LIST_PHOTO_FILE_ID_RU
    return EVENTS_LIST_PHOTO_FILE_ID_RU


def get_events_list_photo_path(lang: str = "ru") -> Optional[Path]:
    """
    Локальный fallback-файл обложки экрана «Мероприятия».
    """
    if lang == "en":
        path = PROJECT_ROOT / "photos_engls" / "IMG_7209.PNG"
        if path.exists():
            return path
    path = PROJECT_ROOT / "photos" / "events.png"
    return path if path.exists() else None


def _is_truthy(value: Optional[str]) -> bool:
    """Парсинг булевых значений из .env (true/1/yes/on)."""
    if not value:
        return False
    return value.strip().lower() in ("1", "true", "yes", "on")


def _load_env_file(env_name: str, *, override: bool = False) -> None:
    """Загрузка одного env-файла с поддержкой UTF-8 и Windows (cp1251)."""
    env_path = PROJECT_ROOT / env_name
    if not env_path.exists():
        if env_name == ".env":
            load_dotenv(override=override)
        return
    for encoding in ("utf-8", "cp1251", "utf-8-sig"):
        try:
            with open(env_path, "r", encoding=encoding) as f:
                load_dotenv(stream=f, override=override)
            return
        except UnicodeDecodeError:
            continue
    load_dotenv(override=override)


def _load_dotenv_safe() -> None:
    """
    Загрузка переменных окружения:
    - ENV_FILE в shell (run_test.sh, Docker) — только этот файл;
    - иначе .env, и при TEST_MODE=true — поверх .env.test.
    """
    env_file_from_shell = os.getenv("ENV_FILE", "").strip()
    if env_file_from_shell:
        _load_env_file(env_file_from_shell)
        return

    _load_env_file(".env")
    if _is_truthy(os.getenv("TEST_MODE")):
        _load_env_file(".env.test", override=True)


_load_dotenv_safe()


class Config:
    """Класс конфигурации бота"""

    # Тестовый режим: конфиг из .env.test (см. TEST_MODE в .env)
    TEST_MODE: bool = _is_truthy(os.getenv("TEST_MODE"))
    
    # Версия бота
    VERSION: str = "1.0.1"
    
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

    # Подписка: оплата через группу (код в сообщении)
    SUBSCRIPTION_STARS_PRICE: int = int(os.getenv("SUBSCRIPTION_STARS_PRICE", "100"))
    PAYMENT_GROUP_ID: Optional[int] = None  # ID группы, куда пользователь пишет код (из .env)
    PAYMENT_CODE_BASE: str = os.getenv("PAYMENT_CODE_BASE", "S4K3FF")
    BUY_STARS_BOT_URL: str = os.getenv("BUY_STARS_BOT_URL", "https://t.me/BotFather")  # гиперссылка «ссылка» для покупки звёзд
    PAYMENT_GROUP_LINK: str = os.getenv("PAYMENT_GROUP_LINK", "")  # ссылка на группу оплаты (t.me/... или invite)
    
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
        raw_group = os.getenv("PAYMENT_GROUP_ID", "").strip()
        if raw_group:
            try:
                self.PAYMENT_GROUP_ID = int(raw_group)
            except ValueError:
                pass

    def payment_group_chat_id_matches(self, chat_id: int) -> bool:
        """Проверка, что chat_id — это группа оплаты. Учитывает отрицательный ID супергруппы (-100...)."""
        if self.PAYMENT_GROUP_ID is None:
            return False
        if chat_id == self.PAYMENT_GROUP_ID:
            return True
        # Супергруппа: id часто вида -100xxxxxxxxxx; если в .env указан положительный short_id
        if self.PAYMENT_GROUP_ID > 0 and chat_id < 0:
            if chat_id == -1000000000000 - self.PAYMENT_GROUP_ID:
                return True
        return False
