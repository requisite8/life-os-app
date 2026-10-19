"""Подключение к SQLite и схема БД."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile

from .config import APP_DIR


DB_PATH = APP_DIR / "lifeOS.db"


def resolve_db_path() -> Path:
    primary = APP_DIR / "lifeOS.db"
    fallback = Path(tempfile.gettempdir()) / "lifeOS_local.db"
    for candidate in (primary, fallback):
        try:
            con = sqlite3.connect(candidate)
            con.execute("CREATE TABLE IF NOT EXISTS _db_probe(id INTEGER PRIMARY KEY)")
            con.commit()
            con.close()
            return candidate
        except sqlite3.Error:
            continue
    return fallback


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=10000")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def ensure_column(con: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
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
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                section TEXT,
                priority TEXT,
                deadline TEXT,
                done INTEGER DEFAULT 0,
                done_at TEXT,
                from_ai INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                reminder_sent_at TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                icon TEXT,
                frequency TEXT,
                streak INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reminder_time TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER,
                user_id INTEGER,
                date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(habit_id, date)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                duration_min REAL,
                category TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS reminder_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                kind TEXT,
                ref_id INTEGER,
                date_key TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, kind, ref_id, date_key)
            )
            """
        )
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
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS health_water (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                ml INTEGER,
                updated_at TEXT,
                UNIQUE(user_id, date)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS health_sleep (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                hours REAL,
                bedtime TEXT,
                waketime TEXT,
                quality TEXT,
                updated_at TEXT,
                UNIQUE(user_id, date)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS health_nutrition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                calories INTEGER,
                protein INTEGER,
                fat INTEGER,
                carbs INTEGER,
                updated_at TEXT,
                UNIQUE(user_id, date)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS health_meals_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                description TEXT,
                calories INTEGER,
                protein INTEGER,
                fat INTEGER,
                carbs INTEGER,
                source TEXT,
                created_at TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS health_workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                type TEXT,
                description TEXT,
                duration_min INTEGER,
                calories INTEGER,
                source TEXT,
                created_at TEXT
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_meals_user_date ON health_meals_log(user_id, date)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON health_workouts(user_id, date)")
        ensure_column(con, "users", "chat_id", "INTEGER")
        ensure_column(con, "users", "weekly_last_sent", "TEXT")
        ensure_column(con, "users", "alarm_optin", "INTEGER")
        ensure_column(con, "users", "fitness_goal", "TEXT")
        ensure_column(con, "users", "fitness_level", "TEXT")
        ensure_column(con, "users", "steps_token", "TEXT")
        ensure_column(con, "tasks", "deleted", "INTEGER DEFAULT 0")
        ensure_column(con, "tasks", "reminder_sent_at", "TEXT")
        ensure_column(con, "habits", "reminder_time", "TEXT")
        ensure_column(con, "habits", "weekdays", "TEXT")

        con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_focus_user ON focus_sessions(user_id)")


def configure_db_path() -> None:
    """Выбирает рабочий файл БД при старте приложения."""
    global DB_PATH
    DB_PATH = resolve_db_path()
