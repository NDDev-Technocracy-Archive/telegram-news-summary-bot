from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from src.config import settings

DB_PATH = Path(__file__).parent.parent / settings.DATABASE_PATH


@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def init_database() -> None:
    async with get_connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, channel_name)
            )
        """)
        await conn.commit()


async def get_or_create_user(telegram_id: int) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]

        cursor = await conn.execute(
            "INSERT INTO users (telegram_id) VALUES (?)",
            (telegram_id,)
        )
        await conn.commit()
        return cursor.lastrowid


async def count_user_channels(user_id: int) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM channels WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0


async def add_channel(user_id: int, channel_name: str) -> tuple[bool, str]:
    channel_name = channel_name.lower().strip()

    count = await count_user_channels(user_id)
    if count >= settings.MAX_CHANNELS_PER_USER:
        return False, f"Достигнут лимит каналов ({settings.MAX_CHANNELS_PER_USER})"

    try:
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO channels (user_id, channel_name) VALUES (?, ?)",
                (user_id, channel_name)
            )
            await conn.commit()
        return True, f"Канал @{channel_name} добавлен"
    except aiosqlite.IntegrityError:
        return False, f"Канал @{channel_name} уже в списке"


async def get_user_channels(user_id: int) -> list[str]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT channel_name FROM channels WHERE user_id = ? ORDER BY added_at",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [row["channel_name"] for row in rows]


async def remove_channel(user_id: int, channel_name: str) -> tuple[bool, str]:
    channel_name = channel_name.lower().strip()
    channel_name = channel_name.removeprefix("@")

    async with get_connection() as conn:
        cursor = await conn.execute(
            "DELETE FROM channels WHERE user_id = ? AND channel_name = ?",
            (user_id, channel_name)
        )
        await conn.commit()

        if cursor.rowcount > 0:
            return True, f"Канал @{channel_name} удален"
        return False, f"Канал @{channel_name} не найден в вашем списке"
