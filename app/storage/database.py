import os
import aiosqlite


class Database:
    """SQLite database manager for persistence."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.environ.get("DATABASE_PATH", "agent.db")
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        parent = os.path.dirname(self._db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._init_tables()

    async def _init_tables(self) -> None:
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS telegram_chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                username TEXT
            );
            CREATE TABLE IF NOT EXISTS slack_channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT,
                team_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_scope
                ON conversations(platform, channel_id, created_at);
        """)
        await self._conn.commit()

    async def execute(self, sql: str, params: tuple = ()) -> None:
        await self._conn.execute(sql, params)
        await self._conn.commit()

    async def fetch(self, sql: str, params: tuple = ()) -> list:
        cursor = await self._conn.execute(sql, params)
        return await cursor.fetchall()

    async def save_telegram_chat(self, chat_id: int, title: str | None = None, username: str | None = None) -> None:
        await self._conn.execute(
            "INSERT OR REPLACE INTO telegram_chats (chat_id, title, username) VALUES (?, ?, ?)",
            (chat_id, title, username),
        )
        await self._conn.commit()

    async def save_slack_channel(self, channel_id: str, channel_name: str, team_id: str) -> None:
        await self._conn.execute(
            "INSERT OR REPLACE INTO slack_channels (channel_id, channel_name, team_id) VALUES (?, ?, ?)",
            (channel_id, channel_name, team_id),
        )
        await self._conn.commit()

    async def save_conversation(self, platform: str, channel_id: str, role: str, content: str) -> None:
        await self._conn.execute(
            "INSERT INTO conversations (platform, channel_id, role, content) VALUES (?, ?, ?, ?)",
            (platform, channel_id, role, content),
        )
        await self._conn.commit()

    async def get_conversation_history(self, platform: str, channel_id: str, limit: int = 10) -> list[dict]:
        cursor = await self._conn.execute(
            "SELECT role, content FROM conversations WHERE platform = ? AND channel_id = ? ORDER BY created_at DESC LIMIT ?",
            (platform, channel_id, limit),
        )
        rows = await cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    async def get_all_telegram_chats(self) -> list:
        cursor = await self._conn.execute("SELECT chat_id, title, username FROM telegram_chats ORDER BY chat_id")
        return await cursor.fetchall()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
