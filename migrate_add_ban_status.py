"""
Миграция: добавление поля ban_status в таблицу users (none | shadow | full)
"""

import sqlite3
from pathlib import Path


def migrate():
    """Добавление поля ban_status в таблицу users"""
    db_path = Path("cofounder.db")

    if not db_path.exists():
        print("База данных не найдена. Запусти init_db.py сначала.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if "ban_status" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN ban_status TEXT DEFAULT 'none'")
            cursor.execute("UPDATE users SET ban_status = 'none' WHERE ban_status IS NULL")
            print("✅ Добавлено поле ban_status")
        else:
            print("ℹ️ Поле ban_status уже существует")
            cursor.execute("UPDATE users SET ban_status = 'none' WHERE ban_status IS NULL")

        conn.commit()
        print("\n✅ Миграция завершена успешно!")

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
