import aiosqlite

DB_NAME = "quiz_bot.db"

async def init_db():
    """Создает таблицу пользователей, если её нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                city TEXT,
                weight REAL,
                height REAL,
                age INTEGER,
                activity_minutes INTEGER,
                water_goal REAL,
                calories_goal REAL,
                logged_water REAL DEFAULT 0,
                logged_calories REAL DEFAULT 0,
                burned_calories REAL DEFAULT 0
            )
        """)
        await db.commit()

async def update_user_profile(user_id, city, weight, height, age, activity_minutes, water_goal, calories_goal):
    """Создает или обновляет профиль пользователя. При этом сбрасывает дневные счетчики."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (
                user_id, city, weight, height, age, activity_minutes, 
                water_goal, calories_goal, logged_water, logged_calories, burned_calories
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
        """, (user_id, city, weight, height, age, activity_minutes, water_goal, calories_goal))
        await db.commit()

async def get_user(user_id):
    """Возвращает данные пользователя в виде словаря или None."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def add_water(user_id, amount):
    """Добавляет воду к текущему значению."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET logged_water = logged_water + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def add_calories(user_id, amount):
    """Добавляет калории."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET logged_calories = logged_calories + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def add_burned_calories(user_id, amount):
    """Добавляет сожженные калории."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET burned_calories = burned_calories + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()