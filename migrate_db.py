"""
Миграция базы данных: добавление недостающих полей
"""

import asyncio
import aiosqlite
from pathlib import Path
from config import Config

config = Config()


async def migrate_database():
    """Добавление недостающих полей в таблицу users"""
    # Получаем путь к базе данных из DATABASE_URL
    db_path = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    if not Path(db_path).exists():
        print(f"❌ База данных не найдена: {db_path}")
        print("Запустите init_db.py для создания базы данных.")
        return
    
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.cursor()
        
        try:
            # Проверяем существующие колонки
            await cursor.execute("PRAGMA table_info(users)")
            columns_info = await cursor.fetchall()
            existing_columns = [column[1] for column in columns_info]
            
            print(f"Найдено колонок в таблице users: {len(existing_columns)}")
            
            # Добавляем недостающие поля
            fields_to_add = {
                'short_description': 'TEXT',
                'full_description': 'TEXT',
                'qualities': 'TEXT'
            }
            
            for field_name, field_type in fields_to_add.items():
                if field_name not in existing_columns:
                    await cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                    print(f"✅ Добавлено поле: {field_name}")
                else:
                    print(f"ℹ️ Поле {field_name} уже существует")
            
            await conn.commit()
            print("\n✅ Миграция завершена успешно!")
            
        except Exception as e:
            print(f"❌ Ошибка при миграции: {e}")
            await conn.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(migrate_database())
