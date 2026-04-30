import asyncio
import logging
from functools import lru_cache
from typing import Optional

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4096)
def _translate_sync_cached(text: str, target_lang: str) -> str:
    """Синхронный перевод текста с кэшированием."""
    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return translated.strip() if isinstance(translated, str) and translated.strip() else text
    except Exception as exc:
        logger.warning("Не удалось перевести текст в %s: %s", target_lang, exc)
        return text


async def translate_text_for_language(text: Optional[str], lang: str) -> Optional[str]:
    """
    Переводит текст под язык интерфейса пользователя.
    Поддерживается двусторонний перевод для ru/en:
    - интерфейс en -> перевод в en
    - интерфейс ru -> перевод в ru
    Для других языков возвращает исходный текст.
    """
    if text is None:
        return None
    if not text.strip():
        return text
    if lang not in {"ru", "en"}:
        return text
    return await asyncio.to_thread(_translate_sync_cached, text, lang)


async def translate_qualities_for_language(qualities_raw: Optional[str], lang: str) -> Optional[str]:
    """
    Переводит блок сильных сторон в формате:
    - new: emoji|text (по строкам)
    - legacy: plain lines
    """
    if qualities_raw is None:
        return None
    if not qualities_raw.strip() or lang not in {"ru", "en"}:
        return qualities_raw

    lines = [line.strip() for line in qualities_raw.split("\n") if line.strip()]
    translated_lines: list[str] = []

    for line in lines:
        if "|" in line:
            emoji, text = line.split("|", 1)
            translated_text = await translate_text_for_language(text.strip(), lang) or text.strip()
            translated_lines.append(f"{emoji.strip()}|{translated_text}")
        else:
            translated_text = await translate_text_for_language(line, lang) or line
            translated_lines.append(translated_text)

    return "\n".join(translated_lines)
