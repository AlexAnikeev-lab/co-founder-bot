"""
Миграция: добавление полей short_description, full_description, qualities
"""

import asyncio
import sqlite3
from pathlib import Path


async def migrate():
    """Добавление новых полей в таблицу users"""
    db_path = Path("cofounder.db")
    
    if not db_path.exists():
        print("База данных не найдена. Запусти init_db.py сначала.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существуют ли уже эти поля
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем поля, если их нет
        if 'short_description' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN short_description TEXT")
            print("✅ Добавлено поле short_description")
        else:
            print("ℹ️ Поле short_description уже существует")
        
        if 'full_description' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN full_description TEXT")
            print("✅ Добавлено поле full_description")
        else:
            print("ℹ️ Поле full_description уже существует")
        
        if 'qualities' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN qualities TEXT")
            print("✅ Добавлено поле qualities")
        else:
            print("ℹ️ Поле qualities уже существует")
        
        conn.commit()
        print("\n✅ Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
