import asyncio
import logging
import re
from functools import lru_cache
from typing import Optional

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

_GUILLEMET_RE = re.compile(r"«[^»]*»")


def _protect_guillemets(text: str) -> tuple[str, list[str]]:
    """Заменяет фрагменты «…» плейсхолдерами, чтобы не переводить имена/названия."""
    protected: list[str] = []

    def repl(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"⟦{len(protected) - 1}⟧"

    return _GUILLEMET_RE.sub(repl, text), protected


def _restore_guillemets(text: str, protected: list[str]) -> str:
    for i, fragment in enumerate(protected):
        text = text.replace(f"⟦{i}⟧", fragment)
    return text


@lru_cache(maxsize=4096)
def _translate_sync_cached(text: str, target_lang: str) -> str:
    """Синхронный перевод текста с кэшированием."""
    try:
        prepared, protected = _protect_guillemets(text)
        translated = GoogleTranslator(source="auto", target=target_lang).translate(prepared)
        if not isinstance(translated, str) or not translated.strip():
            return text
        result = _restore_guillemets(translated.strip(), protected)
        return result
    except Exception as exc:
        logger.warning("Не удалось перевести текст в %s: %s", target_lang, exc)
        return text


async def translate_text_for_language(text: Optional[str], lang: str) -> Optional[str]:
    """
    Переводит текст под язык интерфейса пользователя.
    Поддерживается двусторонний перевод для ru/en:
    - интерфейс en -> перевод в en
    - интерфейс ru -> перевод в ru
    Фрагменты в «ёлочках» не переводятся.
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
