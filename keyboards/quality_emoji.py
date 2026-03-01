"""
Клавиатура выбора смайлика для качества (сильная сторона)
в регистрации и при редактировании профиля.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Тематичные эмодзи: бизнес, деньги, продукт, код, контент, обучение
QUALITY_EMOJI_LIST = [
    "💼", "💰", "📈", "📊", "🚀", "🎯", "💡", "🧠",
    "💻", "🧑‍💻", "👨‍💻", "👩‍💻", "⚙️", "🛠️",
    "📱", "📸", "🎥", "✍️", "📚", "🎨",
    "🤝", "⭐", "🌟", "🏆",
]


def get_quality_emoji_keyboard(step: int, prefix: str = "reg", lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Inline‑клавиатура выбора смайлика для качества.

    - step: 1, 2 или 3 (номер качества).
    - prefix: "reg" для регистрации (callback вида reg_q1_emoji:🔥),
              "edit" для редактирования профиля (edit_q1_emoji:🔥).
    - lang: язык для подписи служебных кнопок.
    """
    from texts.i18n import t

    builder = InlineKeyboardBuilder()
    cb_prefix = f"{prefix}_q{step}_emoji"

    for emoji in QUALITY_EMOJI_LIST:
        builder.add(
            InlineKeyboardButton(text=emoji, callback_data=f"{cb_prefix}:{emoji}")
        )

    builder.adjust(6)

    if prefix == "edit":
        # В режиме редактирования профиля даём только «Отмена»
        builder.row(
            InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel")
        )
    else:
        # В регистрации — «Пропустить» (регистрация качеств необязательна)
        builder.row(
            InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="reg_skip")
        )

    return builder.as_markup()

