"""
Конфигурация бота
Все настройки загружаются из переменных окружения
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Класс конфигурации бота"""
    
    # Версия бота
    VERSION: str = "1.0.0"
    
    # Токен бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # ID администратора
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    
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
        """Проверка обязательных параметров"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в переменных окружения")
        
        if not self.ADMIN_ID:
            raise ValueError("ADMIN_ID не установлен в переменных окружения")
