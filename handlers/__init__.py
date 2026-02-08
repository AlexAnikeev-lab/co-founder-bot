"""
Регистрация всех обработчиков
"""

from aiogram import Dispatcher
from handlers import start, registration, profile, test, learning, common, swipe, admin


def register_all_handlers(dp: Dispatcher) -> None:
    """Регистрация всех handlers"""
    start.register_handlers(dp)
    registration.register_handlers(dp)
    profile.register_handlers(dp)
    test.register_handlers(dp)
    learning.register_handlers(dp)
    common.register_handlers(dp)
    swipe.register_handlers(dp)
    admin.register_handlers(dp)
