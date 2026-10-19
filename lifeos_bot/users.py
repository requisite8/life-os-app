"""Пользователи бота."""

from aiogram import Bot

from .config import ADMIN_CHAT_ID
from .database import db


def ensure_user(telegram_id: int, first_name: str, username: str | None, chat_id: int) -> tuple[int, bool]:
    with db() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                first_name TEXT,
                username TEXT,
                chat_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                weekly_last_sent TEXT
            )
            """
        )
        row = con.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
        if row:
            con.execute(
                "UPDATE users SET first_name=?, username=?, chat_id=? WHERE id=?",
                (first_name, username, chat_id, row["id"]),
            )
            return int(row["id"]), False
        cur = con.execute(
            "INSERT INTO users(telegram_id, first_name, username, chat_id) VALUES(?,?,?,?)",
            (telegram_id, first_name, username, chat_id),
        )
        return int(cur.lastrowid), True


async def notify_admin_new_user(bot: Bot, user) -> None:
    uname = f"@{user.username}" if user.username else "без username"
    with db() as con:
        total = con.execute("SELECT COUNT(*) c FROM users WHERE telegram_id IS NOT NULL").fetchone()["c"]
    text = (
        f"🆕 Новый пользователь бота: {user.first_name or ''} ({uname}, id {user.id})\n"
        f"Всего пользователей: {total}"
    )
    try:
        await bot.send_message(ADMIN_CHAT_ID, text)
    except Exception:
        pass
