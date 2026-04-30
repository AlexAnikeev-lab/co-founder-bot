#!/usr/bin/env python3
"""
Скрипт загрузки английских фото (photos_engls/) в Telegram для получения file_id.
Запуск: python scripts/upload_photos_for_file_id_en.py

Требования: в .env указаны BOT_TOKEN и ADMIN_ID. Картинки лежат в photos_engls/.
Имена файлов берутся из config.REGISTRATION_PHOTOS_EN (если заданы) или из REGISTRATION_PHOTOS.
Полученные file_id записываются в photos_file_ids.py как REGISTRATION_PHOTO_FILE_IDS_EN.
Существующий REGISTRATION_PHOTO_FILE_IDS (русские) не трогается.
"""

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# Безопасная загрузка .env (как в config)
def _load_dotenv_safe() -> None:
    for enc in ("utf-8", "cp1251", "utf-8-sig"):
        try:
            with open(ROOT / ".env", "r", encoding=enc) as f:
                import dotenv
                dotenv.load_dotenv(stream=f)
            return
        except Exception:
            continue
    load_dotenv(ROOT / ".env")

_load_dotenv_safe()


async def main() -> None:
    from config import REGISTRATION_PHOTOS, REGISTRATION_PHOTOS_EN, PHOTOS_DIR_EN

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        print("❌ В .env не указан BOT_TOKEN")
        return

    raw_admin = os.getenv("ADMIN_ID", "").strip()
    if not raw_admin:
        print("❌ В .env не указан ADMIN_ID (нужен чат, куда бот отправит фото)")
        return
    try:
        chat_id = int(raw_admin.split(",")[0].strip())
    except ValueError:
        print("❌ ADMIN_ID должен содержать число (id чата)")
        return

    try:
        from aiogram import Bot
        from aiogram.types import FSInputFile
    except ImportError:
        print("❌ Установи aiogram: pip install aiogram")
        return

    photos_dir = ROOT / PHOTOS_DIR_EN
    if not photos_dir.is_dir():
        print(f"❌ Папка {PHOTOS_DIR_EN}/ не найдена")
        return

    # Шаги и файлы: для en используем REGISTRATION_PHOTOS_EN или fallback на REGISTRATION_PHOTOS
    steps_and_files = [
        (step, REGISTRATION_PHOTOS_EN.get(step) or filename)
        for step, filename in REGISTRATION_PHOTOS.items()
    ]

    bot = Bot(token=token)
    result: dict[str, str] = {}
    seen_files: set[str] = set()

    try:
        for step, filename in steps_and_files:
            if filename in seen_files:
                prev_step = next(s for s, f in steps_and_files if f == filename and s in result)
                result[step] = result[prev_step]
                print(f"  {step}: (то же, что {prev_step}) {filename}")
                continue
            path = photos_dir / filename
            if not path.exists():
                print(f"  ⚠️ Пропуск {step}: файл не найден {filename}")
                continue
            try:
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=FSInputFile(path),
                )
                file_id = msg.photo[-1].file_id
                result[step] = file_id
                seen_files.add(filename)
                print(f"  ✅ {step}: {filename} -> {file_id[:40]}...")
            except Exception as e:
                print(f"  ❌ {step} {filename}: {e}")
    finally:
        await bot.session.close()

    if not result:
        print("Не удалось получить ни одного file_id.")
        return

    out_path = ROOT / "photos_file_ids.py"
    # Сохраняем существующий REGISTRATION_PHOTO_FILE_IDS, если файл уже есть
    existing_ru: str | None = None
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8")
        idx = text.find("REGISTRATION_PHOTO_FILE_IDS = {")
        if idx != -1:
            start = idx
            depth = 0
            for i, c in enumerate(text[start:], start):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        existing_ru = text[start : i + 1]
                        break

    lines = [
        "# Сгенерировано/обновлено скриптами upload_photos_for_file_id.py и upload_photos_for_file_id_en.py.",
        "# Не редактируй вручную. Чтобы обновить — заново запусти нужный скрипт.",
        "",
    ]
    if existing_ru:
        lines.append(existing_ru)
        lines.append("")
    else:
        lines.append("REGISTRATION_PHOTO_FILE_IDS = {}  # запусти upload_photos_for_file_id.py для русских фото")
        lines.append("")
    lines.append("REGISTRATION_PHOTO_FILE_IDS_EN = {")
    for step, fid in result.items():
        lines.append(f'    "{step}": "{fid}",')
    lines.append("}")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ REGISTRATION_PHOTO_FILE_IDS_EN записано в {out_path.name}")
    print("Бот будет отправлять английские фото по этим токенам.")


if __name__ == "__main__":
    asyncio.run(main())
