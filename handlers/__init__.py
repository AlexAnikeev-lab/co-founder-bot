"""
Регистрация всех обработчиков
"""

from aiogram import Dispatcher
from handlers import admin_events, start, registration, profile, test, learning, events, common, swipe, admin, subscription


def register_all_handlers(dp: Dispatcher) -> None:
    """Регистрация всех handlers. Админ — первым, чтобы «Написать» и рассылка обрабатывались до общих хендлеров."""
    admin.register_handlers(dp)
    admin_events.register_handlers(dp)
    start.register_handlers(dp)
    registration.register_handlers(dp)
    profile.register_handlers(dp)
    test.register_handlers(dp)
    learning.register_handlers(dp)
    events.register_handlers(dp)
    common.register_handlers(dp)
    swipe.register_handlers(dp)
    subscription.register_handlers(dp)
