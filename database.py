import aiosqlite
import json

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                category TEXT NOT NULL,
                expression TEXT NOT NULL,
                result TEXT NOT NULL,
                steps TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def save_calculation(user_id, username, category, expression, result, steps):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO calculations 
               (user_id, username, category, expression, result, steps) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, category, expression, result, json.dumps(steps, ensure_ascii=False))
        )
        await db.commit()

async def get_history(user_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM calculations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
