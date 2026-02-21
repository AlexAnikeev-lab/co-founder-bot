"""
Миграция: добавление поля language в таблицу users (ru | en).
"""

import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).resolve().parent / "cofounder.db"
    if not db_path.exists():
        print("База данных не найдена.")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [c[1] for c in cursor.fetchall()]
        if "language" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'")
            conn.commit()
            print("✅ Добавлено поле language")
        else:
            print("ℹ️ Поле language уже есть")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
