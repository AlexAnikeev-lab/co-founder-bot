#!/usr/bin/env python3
"""
Скрипт загрузки фото в Telegram для получения file_id (токенов).
Запусти один раз: загрузи картинки в папку photos/, настрой .env и выполни скрипт.
Он отправит каждое фото в чат (по умолчанию первому админу из ADMIN_ID),
получит file_id и запишет их в photos_file_ids.py.
Дальше бот будет отправлять фото по file_id — без повторной загрузки файлов.
"""

import asyncio
import os
import sys
from pathlib import Path

# корень проекта
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# порядок шагов и файлов — как в config.REGISTRATION_PHOTOS
STEPS_AND_FILES = [
    ("welcome_1", "62.png"),
    ("welcome_2", "63.png"),
    ("age", "64.png"),
    ("legal", "65.png"),
    ("learning_mode", "65.png"),
    ("telegram", "66.png"),
    ("name", "67.png"),
    ("photo", "68.png"),
    ("short_desc", "69.png"),
    ("full_desc", "70.png"),
    ("quality_1", "71.png"),
    ("quality_2", "72.png"),
    ("quality_3", "73.png"),
    ("success", "74.png"),
]


async def main() -> None:
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

    photos_dir = ROOT / "photos"
    if not photos_dir.is_dir():
        print("❌ Папка photos/ не найдена")
        return

    bot = Bot(token=token)
    result: dict[str, str] = {}
    seen_files: set[str] = set()

    try:
        for step, filename in STEPS_AND_FILES:
            if filename in seen_files:
                prev_step = next(s for s, f in STEPS_AND_FILES if f == filename and s in result)
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
    lines = [
        "# Сгенерировано скриптом upload_photos_for_file_id.py. Не редактируй вручную.",
        "# Чтобы обновить — заново запусти скрипт.",
        "",
        "REGISTRATION_PHOTO_FILE_IDS = {",
    ]
    for step, fid in result.items():
        lines.append(f'    "{step}": "{fid}",')
    lines.append("}")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ Записано в {out_path.name}")
    print("Бот будет отправлять фото по этим токенам (быстро, без загрузки файлов).")


if __name__ == "__main__":
    asyncio.run(main())
