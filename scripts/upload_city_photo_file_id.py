#!/usr/bin/env python3
"""
Загружает ТОЛЬКО фото шага "city" (ru/en) и обновляет photos_file_ids.py.

Зачем:
- не трогает остальные шаги регистрации;
- обновляет только ключи city в словарях:
  - REGISTRATION_PHOTO_FILE_IDS["city"]
  - REGISTRATION_PHOTO_FILE_IDS_EN["city"]

Запуск:
    python scripts/upload_city_photo_file_id.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def _load_dotenv_safe() -> None:
    """Загрузка .env с fallback по кодировкам."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for enc in ("utf-8", "cp1251", "utf-8-sig"):
        try:
            with open(env_path, "r", encoding=enc) as f:
                import dotenv

                dotenv.load_dotenv(stream=f)
            return
        except Exception:
            continue


_load_dotenv_safe()


def _extract_block(text: str, block_name: str) -> str | None:
    start_idx = text.find(f"{block_name} = {{")
    if start_idx == -1:
        return None
    depth = 0
    begin = None
    for i, ch in enumerate(text[start_idx:], start_idx):
        if ch == "{":
            if begin is None:
                begin = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]
    return None


def _parse_block_to_dict(block: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith('"') or '":' not in line:
            continue
        try:
            key = line.split('":', 1)[0].strip().strip('"')
            value = line.split('":', 1)[1].strip().rstrip(",").strip().strip('"')
            if key and value:
                result[key] = value
        except Exception:
            continue
    return result


def _dict_to_block(name: str, data: dict[str, str]) -> str:
    lines = [f"{name} = {{"]
    for key in sorted(data.keys()):
        lines.append(f'    "{key}": "{data[key]}",')
    lines.append("}")
    return "\n".join(lines)


def _update_photos_file_ids(*, city_ru: str | None, city_en: str | None) -> None:
    out_path = ROOT / "photos_file_ids.py"

    existing_text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    ru_block = _extract_block(existing_text, "REGISTRATION_PHOTO_FILE_IDS")
    en_block = _extract_block(existing_text, "REGISTRATION_PHOTO_FILE_IDS_EN")

    ru_data = _parse_block_to_dict(ru_block or "REGISTRATION_PHOTO_FILE_IDS = {}")
    en_data = _parse_block_to_dict(en_block or "REGISTRATION_PHOTO_FILE_IDS_EN = {}")

    if city_ru:
        ru_data["city"] = city_ru
    if city_en:
        en_data["city"] = city_en

    content = [
        "# Сгенерировано/обновлено скриптами загрузки file_id.",
        "# Этот файл можно обновлять частично (например, только city).",
        "",
        _dict_to_block("REGISTRATION_PHOTO_FILE_IDS", ru_data),
        "",
        _dict_to_block("REGISTRATION_PHOTO_FILE_IDS_EN", en_data),
        "",
    ]
    out_path.write_text("\n".join(content), encoding="utf-8")


async def main() -> None:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        print("❌ В .env не указан BOT_TOKEN")
        return

    raw_admin = os.getenv("ADMIN_ID", "").strip()
    if not raw_admin:
        print("❌ В .env не указан ADMIN_ID")
        return
    try:
        chat_id = int(raw_admin.split(",")[0].strip())
    except ValueError:
        print("❌ ADMIN_ID должен содержать число")
        return

    try:
        from aiogram import Bot
        from aiogram.types import FSInputFile
    except ImportError:
        print("❌ Установи зависимости: pip install -r requirements.txt")
        return

    ru_path = ROOT / "photos" / "gorod.png"
    en_path = ROOT / "photos_engls" / "city.png"
    if not ru_path.exists() and not en_path.exists():
        print("❌ Не найдены файлы city: photos/gorod.png и photos_engls/city.png")
        return

    bot = Bot(token=token)
    city_ru: str | None = None
    city_en: str | None = None
    try:
        if ru_path.exists():
            msg_ru = await bot.send_photo(chat_id=chat_id, photo=FSInputFile(ru_path))
            city_ru = msg_ru.photo[-1].file_id
            print(f"✅ RU city: {city_ru[:40]}...")
        else:
            print("⚠️ RU city пропущен: photos/gorod.png не найден")

        if en_path.exists():
            msg_en = await bot.send_photo(chat_id=chat_id, photo=FSInputFile(en_path))
            city_en = msg_en.photo[-1].file_id
            print(f"✅ EN city: {city_en[:40]}...")
        else:
            print("⚠️ EN city пропущен: photos_engls/city.png не найден")
    finally:
        await bot.session.close()

    if not city_ru and not city_en:
        print("❌ Не удалось получить ни одного file_id для city")
        return

    _update_photos_file_ids(city_ru=city_ru, city_en=city_en)
    print("✅ Обновлено: photos_file_ids.py (только ключи city)")


if __name__ == "__main__":
    asyncio.run(main())
