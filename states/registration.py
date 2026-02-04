"""
Состояния для процесса регистрации
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния регистрации"""
    waiting_for_age = State()
    waiting_for_legal_agreement = State()
    waiting_for_telegram_access = State()
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_parent_email = State()  # Для несовершеннолетних


class ProfileEditStates(StatesGroup):
    """Состояния редактирования профиля"""
    editing_name = State()
    editing_photo = State()
    editing_strengths = State()
    editing_short_description = State()
    editing_full_description = State()
