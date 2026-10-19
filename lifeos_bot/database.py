"""Подключение к БД бота."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from .config import DB_FALLBACK, DB_PRIMARY


def db_path() -> Path:
    if DB_PRIMARY.exists():
        return DB_PRIMARY
    return DB_FALLBACK


@contextmanager
def db():
    con = sqlite3.connect(db_path(), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=10000")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def ensure_alarm_tables(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_actions (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            kind TEXT,
            payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cols = {r["name"] for r in con.execute("PRAGMA table_info(users)")}
    if "alarm_optin" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN alarm_optin INTEGER")
    if "steps_token" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN steps_token TEXT")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS health_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            steps INTEGER,
            updated_at TEXT,
            UNIQUE(user_id, date)
        )
        """
    )
