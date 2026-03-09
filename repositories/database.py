"""
Настройка подключения к базе данных
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import Config

config = Config()

# Создание движка базы данных
# pool_size и max_overflow под пик 400+ пользователей (одна сессия на запрос)
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Базовый класс для моделей"""
    pass


async def get_session():
    """Получение сессии базы данных (контекстный менеджер)"""
    async with async_session_maker() as session:
        yield session
