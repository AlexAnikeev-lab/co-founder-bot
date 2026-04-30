#!/usr/bin/env python3
"""
Загружает обложку раздела «Мероприятия» в Telegram и записывает file_id
в photos_file_ids.py как ключ ["events"] в RU/EN словаре.
"""

from __future__ import annotations

import asyncio
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_env_fallback(path: Path) -> None:
    """
    Загрузка .env без внешних зависимостей.
    Поддерживает строки вида KEY=VALUE и игнорирует комментарии/пустые строки.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(ROOT / ".env")
except Exception:
    _load_env_fallback(ROOT / ".env")


def _upsert_events_file_id(target: Path, file_id: str, *, lang: str) -> None:
    if target.exists():
        text = target.read_text(encoding="utf-8")
    else:
        text = (
            "# Сгенерировано скриптами upload_*_file_id.py\n\n"
            "REGISTRATION_PHOTO_FILE_IDS = {\n}\n\n"
            "REGISTRATION_PHOTO_FILE_IDS_EN = {\n}\n"
        )

    dict_name = "REGISTRATION_PHOTO_FILE_IDS_EN" if lang == "en" else "REGISTRATION_PHOTO_FILE_IDS"
    dict_pattern = rf"({dict_name}\s*=\s*\{{)(.*?)(\n\}})"
    m = re.search(dict_pattern, text, flags=re.S)
    if not m:
        raise RuntimeError(f"Не найден {dict_name} в photos_file_ids.py")

    body = m.group(2)
    if re.search(r'^\s*"events"\s*:\s*".*?",?\s*$', body, flags=re.M):
        body_new = re.sub(
            r'^\s*"events"\s*:\s*".*?",?\s*$',
            f'    "events": "{file_id}",',
            body,
            flags=re.M,
        )
    else:
        body_new = body
        if body_new.strip():
            if not body_new.endswith("\n"):
                body_new += "\n"
            body_new += f'    "events": "{file_id}",\n'
        else:
            body_new = "\n    " + f'"events": "{file_id}",' + "\n"

    text_new = text[: m.start(2)] + body_new + text[m.end(2) :]
    target.write_text(text_new, encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Загрузить обложку раздела мероприятий и сохранить file_id")
    parser.add_argument("--lang", choices=("ru", "en"), default="ru", help="Язык обложки (ru или en)")
    parser.add_argument(
        "--file",
        default="",
        help="Явный путь до файла (опционально). Если не задан, берётся стандартный для выбранного языка.",
    )
    args = parser.parse_args()

    token = os.getenv("BOT_TOKEN", "").strip()
    raw_admin = os.getenv("ADMIN_ID", "").strip()
    if not token:
        print("❌ BOT_TOKEN не найден в .env")
        return
    if not raw_admin:
        print("❌ ADMIN_ID не найден в .env")
        return

    try:
        chat_id = int(raw_admin.split(",")[0].strip())
    except ValueError:
        print("❌ ADMIN_ID должен быть числом (или списком чисел через запятую)")
        return

    if args.file:
        photo_path = Path(args.file).expanduser()
        if not photo_path.is_absolute():
            photo_path = ROOT / photo_path
    elif args.lang == "en":
        photo_path = ROOT / "photos_engls" / "IMG_7209.PNG"
    else:
        photo_path = ROOT / "photos" / "events.png"
    if not photo_path.exists():
        print(f"❌ Файл не найден: {photo_path}")
        return

    try:
        from aiogram import Bot
        from aiogram.types import FSInputFile
    except ImportError:
        print("❌ Установи aiogram: pip install aiogram")
        return

    bot = Bot(token=token)
    try:
        msg = await bot.send_photo(chat_id=chat_id, photo=FSInputFile(photo_path))
        file_id = msg.photo[-1].file_id
    finally:
        await bot.session.close()

    target = ROOT / "photos_file_ids.py"
    _upsert_events_file_id(target, file_id, lang=args.lang)

    dict_name = "REGISTRATION_PHOTO_FILE_IDS_EN" if args.lang == "en" else "REGISTRATION_PHOTO_FILE_IDS"
    print(f"✅ {photo_path.name} [{args.lang}] -> {file_id}")
    print(f"✅ Записано в {target.name} (ключ {dict_name}['events'])")


if __name__ == "__main__":
    asyncio.run(main())
