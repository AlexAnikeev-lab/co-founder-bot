"""
Миграция: поля подписки в users и таблица subscription_pending_codes.
"""

import sqlite3
from pathlib import Path


def migrate():
    """Добавление полей подписки и таблицы кодов."""
    db_path = Path("cofounder.db")

    if not db_path.exists():
        print("База данных не найдена. Запусти init_db.py сначала.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [c[1] for c in cursor.fetchall()]

        for col, typ, default in (
            ("subscription_active", "INTEGER", "0"),
            ("subscription_until", "TEXT", "NULL"),
            ("super_like_used", "INTEGER", "0"),
        ):
            if col not in columns:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {typ} DEFAULT {default}")
                print(f"✅ Добавлено поле users.{col}")
            else:
                print(f"ℹ️ Поле users.{col} уже существует")

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='subscription_pending_codes'"
        )
        if cursor.fetchone() is None:
            cursor.execute("""
                CREATE TABLE subscription_pending_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    created_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX ix_subscription_pending_codes_code ON subscription_pending_codes (code)")
            cursor.execute("CREATE INDEX ix_subscription_pending_codes_user_id ON subscription_pending_codes (user_id)")
            print("✅ Создана таблица subscription_pending_codes")
        else:
            print("ℹ️ Таблица subscription_pending_codes уже существует")

        conn.commit()
        print("\n✅ Миграция подписки завершена успешно!")

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
