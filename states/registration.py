"""
Состояния для процесса регистрации
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния регистрации"""
    waiting_for_language = State()
    waiting_for_age = State()
    waiting_for_legal_agreement = State()
    waiting_for_telegram_access = State()
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_city = State()
    waiting_for_short_description = State()
    waiting_for_full_description = State()
    waiting_for_quality_1 = State()
    waiting_for_quality_1_emoji = State()
    waiting_for_quality_2 = State()
    waiting_for_quality_2_emoji = State()
    waiting_for_quality_3 = State()
    waiting_for_quality_3_emoji = State()
    waiting_for_parent_email = State()  # Для несовершеннолетних


class ProfileEditStates(StatesGroup):
    """Состояния редактирования профиля"""
    editing_name = State()
    editing_photo = State()
    editing_short_description = State()
    editing_full_description = State()
    editing_quality_1 = State()
    editing_quality_1_emoji = State()
    editing_quality_2 = State()
    editing_quality_2_emoji = State()
    editing_quality_3 = State()
    editing_quality_3_emoji = State()
