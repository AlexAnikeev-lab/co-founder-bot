"""
Миграция: добавление поля last_seen_at в таблицу users (последняя активность).
"""

import sqlite3
from pathlib import Path

# Путь к БД как в других миграциях
DB_PATH = Path("cofounder.db")


def migrate():
    if not DB_PATH.exists():
        print("База данных не найдена. Запусти init_db.py сначала.")
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [c[1] for c in cursor.fetchall()]
        if "last_seen_at" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN last_seen_at TEXT")
            print("✅ Добавлено поле last_seen_at")
        else:
            print("ℹ️ Поле last_seen_at уже существует")
        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
