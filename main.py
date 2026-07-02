import asyncio
import json
import logging
import os
import re
import sqlite3
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DB_PATH = APP_DIR / "lifeOS.db"
try:
    MSK = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MSK = timezone(timedelta(hours=3))


def load_local_env() -> dict[str, str]:
    env_path = APP_DIR / ".env"
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        result[key.strip().lstrip("\ufeff")] = val.strip().strip("\"'")
    return result


_LOCAL_ENV = load_local_env()
TELEGRAM_BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or _LOCAL_ENV.get("TELEGRAM_BOT_TOKEN", "")
).strip()
WEBAPP_URL = (os.getenv("WEBAPP_URL") or _LOCAL_ENV.get("WEBAPP_URL", "")).strip()
TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else ""
ENABLE_EMBEDDED_WORKERS = (
    (os.getenv("ENABLE_EMBEDDED_WORKERS") or _LOCAL_ENV.get("ENABLE_EMBEDDED_WORKERS", "0")).strip().lower()
    in {"1", "true", "yes", "on"}
)
OPENAI_API_KEY = (
    os.getenv("OPENAI_API_KEY") or _LOCAL_ENV.get("OPENAI_API_KEY", "")
).strip()

logger = logging.getLogger("lifeos")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Life OS API")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_stop_event = asyncio.Event()
_bot_offset = 0
_worker_task: asyncio.Task | None = None
_bot_task: asyncio.Task | None = None


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


class UserCreate(BaseModel):
    telegram_id: int | None = None
    first_name: str = "Пользователь"
    username: str | None = None


class FocusCreate(BaseModel):
    user_id: int
    duration_min: float
    category: str | None = None


class HabitCreate(BaseModel):
    user_id: int
    name: str
    icon: str = "✅"
    frequency: str = "Каждый день"
    reminder_time: str | None = None
    weekdays: list[int] | None = None


class HabitUpdate(BaseModel):
    name: str
    icon: str = "✅"
    frequency: str = "Каждый день"
    reminder_time: str | None = None
    weekdays: list[int] | None = None


class HabitToggle(BaseModel):
    habit_id: int
    user_id: int
    date: str


class TaskCreate(BaseModel):
    user_id: int
    name: str
    section: str = "work"
    priority: str = "mid"
    deadline: str | None = None
    from_ai: bool = False


class TaskPatch(BaseModel):
    done: bool


class AIChatRequest(BaseModel):
    user_id: int
    message: str
    history: list[dict[str, Any]] | None = None


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def now_msk() -> datetime:
    return datetime.now(MSK)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_client_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=MSK)
        return dt.astimezone(MSK)
    except ValueError:
        return None


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
        ensure_column(con, "users", "chat_id", "INTEGER")
        ensure_column(con, "users", "weekly_last_sent", "TEXT")
        ensure_column(con, "tasks", "deleted", "INTEGER DEFAULT 0")
        ensure_column(con, "tasks", "reminder_sent_at", "TEXT")
        ensure_column(con, "habits", "reminder_time", "TEXT")
        ensure_column(con, "habits", "weekdays", "TEXT")

        con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_focus_user ON focus_sessions(user_id)")


def streak_for_habit(con: sqlite3.Connection, habit_id: int) -> int:
    rows = con.execute(
        "SELECT date FROM habit_logs WHERE habit_id=? ORDER BY date DESC", (habit_id,)
    ).fetchall()
    done = {r["date"] for r in rows}
    cursor = now_msk().date()
    streak = 0
    while cursor.isoformat() in done:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def is_frequency_active(freq: str, date_obj) -> bool:
    weekday = date_obj.weekday()  # 0 monday
    # custom weekday set has higher priority
    # weekdays are stored as JSON list: [0..6]
    if isinstance(freq, list):
        return weekday in freq
    if not freq or freq == "Каждый день":
        return True
    if freq == "Пн-Пт":
        return weekday <= 4
    if freq == "Пн, Ср, Пт":
        return weekday in (0, 2, 4)
    return True


def normalize_weekdays(values: list[int] | None) -> list[int]:
    if not values:
        return []
    unique = sorted({int(v) for v in values if 0 <= int(v) <= 6})
    return unique


def parse_weekdays_json(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
        if isinstance(loaded, list):
            return normalize_weekdays([int(x) for x in loaded])
    except Exception:
        return []
    return []


def week_range(week_offset: int) -> tuple[datetime, datetime]:
    now = now_msk()
    monday = now - timedelta(days=now.weekday())
    monday = datetime(monday.year, monday.month, monday.day, tzinfo=MSK) + timedelta(
        weeks=week_offset
    )
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


def user_chat_id(con: sqlite3.Connection, user_id: int) -> int | None:
    row = con.execute("SELECT chat_id FROM users WHERE id=?", (user_id,)).fetchone()
    return int(row["chat_id"]) if row and row["chat_id"] else None


def tg_request(method: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not TG_API:
        return None
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{TG_API}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        logger.warning("telegram %s failed: %s", method, e)
        return None


def send_tg(chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    tg_request("sendMessage", payload)


def send_focus_finished(user_id: int, duration: float, category: str | None) -> None:
    with db() as con:
        chat_id = user_chat_id(con, user_id)
    if not chat_id:
        return
    cat = category or "Фокус"
    send_tg(chat_id, f"Фокус-сессия завершена: {int(duration)} мин.\nКатегория: {cat}")


def build_task_list_text(con: sqlite3.Connection, user_id: int) -> str:
    rows = con.execute(
        """
        SELECT name, deadline, section, priority
        FROM tasks
        WHERE user_id=? AND deleted=0 AND done=0
        ORDER BY CASE WHEN deadline IS NULL THEN 1 ELSE 0 END, deadline
        LIMIT 15
        """,
        (user_id,),
    ).fetchall()
    if not rows:
        return "У тебя сейчас нет активных задач."
    lines = ["Текущие задачи:"]
    for i, r in enumerate(rows, start=1):
        dl = ""
        dt = parse_client_dt(r["deadline"])
        if dt:
            dl = f" · {dt.strftime('%d.%m %H:%M')}"
        lines.append(f"{i}. {r['name']} ({r['section']}/{r['priority']}){dl}")
    return "\n".join(lines)


def build_habit_list_text(con: sqlite3.Connection, user_id: int) -> str:
    rows = con.execute(
        "SELECT id, name, icon, frequency, reminder_time FROM habits WHERE user_id=? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    if not rows:
        return "У тебя пока нет привычек."
    lines = ["Текущие привычки:"]
    for i, r in enumerate(rows, start=1):
        time_part = f" · ⏰ {r['reminder_time']}" if r["reminder_time"] else ""
        lines.append(f"{i}. {r['icon']} {r['name']} ({r['frequency']}){time_part}")
    return "\n".join(lines)


def calc_week_stats(con: sqlite3.Connection, user_id: int, week_offset: int) -> dict[str, Any]:
    monday, sunday = week_range(week_offset)
    prev_monday, prev_sunday = week_range(week_offset - 1)

    curr_focus = con.execute(
        "SELECT COALESCE(SUM(duration_min),0) AS v FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<=?",
        (user_id, monday.isoformat(), sunday.isoformat()),
    ).fetchone()["v"]
    prev_focus = con.execute(
        "SELECT COALESCE(SUM(duration_min),0) AS v FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<=?",
        (user_id, prev_monday.isoformat(), prev_sunday.isoformat()),
    ).fetchone()["v"]

    curr_sessions = con.execute(
        "SELECT COUNT(*) AS c FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<=?",
        (user_id, monday.isoformat(), sunday.isoformat()),
    ).fetchone()["c"]
    prev_sessions = con.execute(
        "SELECT COUNT(*) AS c FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<=?",
        (user_id, prev_monday.isoformat(), prev_sunday.isoformat()),
    ).fetchone()["c"]

    curr_tasks_done = con.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE user_id=? AND deleted=0 AND done=1 AND done_at>=? AND done_at<=?",
        (user_id, monday.isoformat(), sunday.isoformat()),
    ).fetchone()["c"]
    prev_tasks_done = con.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE user_id=? AND deleted=0 AND done=1 AND done_at>=? AND done_at<=?",
        (user_id, prev_monday.isoformat(), prev_sunday.isoformat()),
    ).fetchone()["c"]

    focus_by_day: dict[str, float] = {}
    for i in range(7):
        day = monday + timedelta(days=i)
        next_day = day + timedelta(days=1)
        key = day.date().isoformat()
        val = con.execute(
            "SELECT COALESCE(SUM(duration_min),0) AS v FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<?",
            (user_id, day.isoformat(), next_day.isoformat()),
        ).fetchone()["v"]
        focus_by_day[key] = round(float(val or 0), 2)

    return {
        "curr_focus_min": int(round(curr_focus or 0)),
        "curr_sessions": int(curr_sessions or 0),
        "curr_tasks_done": int(curr_tasks_done or 0),
        "focus_diff_min": int(round((curr_focus or 0) - (prev_focus or 0))),
        "sessions_diff": int((curr_sessions or 0) - (prev_sessions or 0)),
        "tasks_diff": int((curr_tasks_done or 0) - (prev_tasks_done or 0)),
        "focus_by_day": focus_by_day,
    }


async def notifications_worker() -> None:
    while not _stop_event.is_set():
        try:
            process_task_reminders()
            process_habit_reminders()
            process_weekly_digest()
        except Exception as e:
            logger.exception("worker error: %s", e)
        await asyncio.sleep(60)


def process_task_reminders() -> None:
    now = now_msk()
    with db() as con:
        rows = con.execute(
            """
            SELECT t.id, t.user_id, t.name, t.deadline, u.chat_id
            FROM tasks t
            JOIN users u ON u.id=t.user_id
            WHERE t.deleted=0 AND t.done=0 AND t.deadline IS NOT NULL
              AND (t.reminder_sent_at IS NULL OR t.reminder_sent_at='')
              AND u.chat_id IS NOT NULL
            """
        ).fetchall()
        for r in rows:
            ddl = parse_client_dt(r["deadline"])
            if not ddl:
                continue
            remind_at = ddl - timedelta(hours=1)
            if remind_at <= now <= ddl + timedelta(minutes=5):
                send_tg(
                    int(r["chat_id"]),
                    f"Через 1 час дедлайн задачи:\n{r['name']}\n⏰ {ddl.strftime('%d.%m %H:%M')}",
                )
                con.execute(
                    "UPDATE tasks SET reminder_sent_at=? WHERE id=?",
                    (utc_now_iso(), r["id"]),
                )


def process_habit_reminders() -> None:
    now = now_msk()
    now_hm = now.strftime("%H:%M")
    today = now.date().isoformat()
    with db() as con:
        rows = con.execute(
            """
            SELECT h.id, h.user_id, h.name, h.icon, h.frequency, h.reminder_time, h.weekdays, u.chat_id
            FROM habits h
            JOIN users u ON u.id=h.user_id
            WHERE h.reminder_time IS NOT NULL AND h.reminder_time!='' AND u.chat_id IS NOT NULL
            """
        ).fetchall()
        for r in rows:
            if r["reminder_time"] != now_hm:
                continue
            weekdays = parse_weekdays_json(r["weekdays"])
            if weekdays:
                if not is_frequency_active(weekdays, now.date()):
                    continue
            elif not is_frequency_active(r["frequency"], now.date()):
                continue
            already = con.execute(
                "SELECT 1 FROM reminder_logs WHERE user_id=? AND kind='habit' AND ref_id=? AND date_key=?",
                (r["user_id"], r["id"], today),
            ).fetchone()
            if already:
                continue
            send_tg(
                int(r["chat_id"]),
                f"Напоминание по привычке:\n{r['icon']} {r['name']}\nВремя: {r['reminder_time']}",
            )
            con.execute(
                "INSERT OR IGNORE INTO reminder_logs(user_id, kind, ref_id, date_key) VALUES(?,?,?,?)",
                (r["user_id"], "habit", r["id"], today),
            )


def process_weekly_digest() -> None:
    now = now_msk()
    if now.weekday() != 0 or now.hour != 9:
        return
    monday_key = now.date().isoformat()
    with db() as con:
        users = con.execute(
            "SELECT id, chat_id, weekly_last_sent FROM users WHERE chat_id IS NOT NULL"
        ).fetchall()
        for u in users:
            if u["weekly_last_sent"] == monday_key:
                continue
            stats = calc_week_stats(con, u["id"], -1)
            text = (
                "Недельная статистика (прошлая неделя):\n"
                f"Фокус: {stats['curr_focus_min']} мин\n"
                f"Сессии: {stats['curr_sessions']}\n"
                f"Выполнено задач: {stats['curr_tasks_done']}"
            )
            send_tg(int(u["chat_id"]), text)
            con.execute("UPDATE users SET weekly_last_sent=? WHERE id=?", (monday_key, u["id"]))


def ensure_user_by_telegram(telegram_id: int, first_name: str, username: str | None, chat_id: int | None = None) -> int:
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
        if row:
            con.execute(
                "UPDATE users SET first_name=?, username=?, chat_id=COALESCE(?, chat_id) WHERE id=?",
                (first_name, username, chat_id, row["id"]),
            )
            return int(row["id"])
        cur = con.execute(
            "INSERT INTO users(telegram_id, first_name, username, chat_id) VALUES(?,?,?,?)",
            (telegram_id, first_name, username, chat_id),
        )
        return int(cur.lastrowid)


def handle_bot_text(telegram_id: int, chat_id: int, first_name: str, username: str | None, text: str) -> None:
    user_id = ensure_user_by_telegram(telegram_id, first_name, username, chat_id)
    command = (text or "").strip()
    keyboard = {
        "keyboard": [
            [{"text": "📋 Мои задачи"}, {"text": "✅ Мои привычки"}],
            [{"text": "📊 Моя неделя"}, {"text": "🚀 Открыть мини-приложение"}],
            [{"text": "❓ Помощь"}],
        ],
        "resize_keyboard": True,
    }
    with db() as con:
        if command in ("/start", "🚀 Открыть мини-приложение"):
            about = (
                "Life OS mini app:\n"
                "1. Фокус-таймер и статистика\n"
                "2. Задачи с дедлайнами и напоминанием за 1 час\n"
                "3. Привычки с ежедневным временем напоминания\n"
                "4. Недельные отчёты по прогрессу\n\n"
                "Команды: /tasks, /habits, /week, /help"
            )
            if WEBAPP_URL:
                about += f"\n\nОткрыть: {WEBAPP_URL}"
            send_tg(chat_id, about, reply_markup=keyboard)
            return
        if command in ("/help", "❓ Помощь"):
            send_tg(
                chat_id,
                "/start - о приложении\n/tasks - текущие задачи\n/habits - текущие привычки\n/week - статистика за неделю",
                reply_markup=keyboard,
            )
            return
        if command in ("/tasks", "📋 Мои задачи"):
            send_tg(chat_id, build_task_list_text(con, user_id), reply_markup=keyboard)
            return
        if command in ("/habits", "✅ Мои привычки"):
            send_tg(chat_id, build_habit_list_text(con, user_id), reply_markup=keyboard)
            return
        if command in ("/week", "📊 Моя неделя"):
            s = calc_week_stats(con, user_id, 0)
            send_tg(
                chat_id,
                f"Текущая неделя:\nФокус: {s['curr_focus_min']} мин\nСессии: {s['curr_sessions']}\nЗадач выполнено: {s['curr_tasks_done']}",
                reply_markup=keyboard,
            )
            return
    send_tg(chat_id, "Не понял команду. Напиши /help", reply_markup=keyboard)


async def bot_polling_loop() -> None:
    global _bot_offset
    if not TELEGRAM_BOT_TOKEN:
        logger.info("TELEGRAM_BOT_TOKEN не задан, polling отключен")
        return
    tg_request(
        "setMyCommands",
        {
            "commands": [
                {"command": "start", "description": "О приложении"},
                {"command": "tasks", "description": "Текущие задачи"},
                {"command": "habits", "description": "Текущие привычки"},
                {"command": "week", "description": "Статистика недели"},
                {"command": "help", "description": "Помощь"},
            ]
        },
    )
    while not _stop_event.is_set():
        payload = {"timeout": 25, "offset": _bot_offset}
        data = tg_request("getUpdates", payload) or {}
        for upd in data.get("result", []):
            _bot_offset = max(_bot_offset, int(upd.get("update_id", 0)) + 1)
            msg = upd.get("message") or {}
            text = msg.get("text")
            user = msg.get("from") or {}
            chat = msg.get("chat") or {}
            if not text or not user or not chat:
                continue
            try:
                handle_bot_text(
                    telegram_id=int(user.get("id")),
                    chat_id=int(chat.get("id")),
                    first_name=str(user.get("first_name") or "Пользователь"),
                    username=user.get("username"),
                    text=text,
                )
            except Exception as e:
                logger.exception("bot command failed: %s", e)
        await asyncio.sleep(1)


@app.on_event("startup")
async def on_startup() -> None:
    global _worker_task, _bot_task, DB_PATH
    DB_PATH = resolve_db_path()
    init_db()
    if ENABLE_EMBEDDED_WORKERS:
        _stop_event.clear()
        _worker_task = asyncio.create_task(notifications_worker())
        _bot_task = asyncio.create_task(bot_polling_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    _stop_event.set()
    for t in (_worker_task, _bot_task):
        if t:
            t.cancel()
    await asyncio.sleep(0)


@app.get("/", response_class=HTMLResponse)
def read_root():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def api_health():
    return {
        "ok": True,
        "db": str(DB_PATH),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
        "webapp_url_configured": bool(WEBAPP_URL),
        "embedded_workers": ENABLE_EMBEDDED_WORKERS,
    }


@app.post("/api/users")
def create_or_get_user(payload: UserCreate):
    telegram_id = payload.telegram_id if payload.telegram_id and payload.telegram_id > 0 else None
    with db() as con:
        if telegram_id is not None:
            row = con.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
            if row:
                con.execute(
                    "UPDATE users SET first_name=?, username=? WHERE id=?",
                    (payload.first_name, payload.username, row["id"]),
                )
                return {"id": int(row["id"]), "telegram_id": telegram_id}
            cur = con.execute(
                "INSERT INTO users(telegram_id, first_name, username) VALUES(?,?,?)",
                (telegram_id, payload.first_name, payload.username),
            )
            return {"id": int(cur.lastrowid), "telegram_id": telegram_id}

        # fallback guest when tg user is absent
        cur = con.execute(
            "INSERT INTO users(first_name, username) VALUES(?,?)",
            (payload.first_name, payload.username),
        )
        return {"id": int(cur.lastrowid), "telegram_id": None}


@app.get("/api/focus/{user_id}")
def get_focus_stats(user_id: int):
    today_start = now_msk().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    with db() as con:
        today_row = con.execute(
            "SELECT COUNT(*) AS sessions, COALESCE(SUM(duration_min),0) AS mins FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<?",
            (user_id, today_start.isoformat(), today_end.isoformat()),
        ).fetchone()

        # streak by days with sessions
        days = con.execute(
            "SELECT substr(created_at,1,10) AS day FROM focus_sessions WHERE user_id=? GROUP BY day ORDER BY day DESC",
            (user_id,),
        ).fetchall()
        done_days = {r["day"] for r in days}
        cursor = now_msk().date()
        streak = 0
        while cursor.isoformat() in done_days:
            streak += 1
            cursor -= timedelta(days=1)

        return {
            "today_sessions": int(today_row["sessions"] or 0),
            "today_min": int(round(today_row["mins"] or 0)),
            "streak": streak,
        }


@app.post("/api/focus")
def add_focus(payload: FocusCreate):
    if payload.duration_min <= 0:
        raise HTTPException(400, "duration_min must be positive")
    with db() as con:
        con.execute(
            "INSERT INTO focus_sessions(user_id, duration_min, category, created_at) VALUES(?,?,?,?)",
            (payload.user_id, payload.duration_min, payload.category, now_msk().isoformat()),
        )
    send_focus_finished(payload.user_id, payload.duration_min, payload.category)
    return {"ok": True}


@app.get("/api/habits/{user_id}")
def get_habits(user_id: int):
    with db() as con:
        rows = con.execute(
            "SELECT id, name, icon, frequency, streak, reminder_time, weekdays FROM habits WHERE user_id=? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
        monday = now_msk().date() - timedelta(days=now_msk().date().weekday())
        today = now_msk().date().isoformat()
        result = []
        for r in rows:
            habit_id = int(r["id"])
            logs = con.execute(
                "SELECT date FROM habit_logs WHERE habit_id=? AND date>=? AND date<=?",
                (habit_id, monday.isoformat(), (monday + timedelta(days=6)).isoformat()),
            ).fetchall()
            log_set = {x["date"] for x in logs}
            days = []
            for i in range(7):
                d = (monday + timedelta(days=i)).isoformat()
                days.append(d in log_set)
            streak = streak_for_habit(con, habit_id)
            con.execute("UPDATE habits SET streak=? WHERE id=?", (streak, habit_id))
            weekdays = parse_weekdays_json(r["weekdays"])
            result.append(
                {
                    "id": habit_id,
                    "name": r["name"],
                    "icon": r["icon"] or "✅",
                    "frequency": r["frequency"] or "Каждый день",
                    "streak": streak,
                    "doneToday": today in log_set,
                    "days": days,
                    "reminder_time": r["reminder_time"],
                    "weekdays": weekdays,
                }
            )
        return result


@app.post("/api/habits")
def add_habit(payload: HabitCreate):
    weekdays = normalize_weekdays(payload.weekdays)
    with db() as con:
        cur = con.execute(
            """
            INSERT INTO habits(user_id, name, icon, frequency, streak, reminder_time, weekdays, created_at)
            VALUES(?,?,?,?,0,?,?,?)
            """,
            (
                payload.user_id,
                payload.name.strip(),
                payload.icon,
                payload.frequency,
                payload.reminder_time,
                json.dumps(weekdays, ensure_ascii=False) if weekdays else None,
                now_msk().isoformat(),
            ),
        )
        return {
            "id": int(cur.lastrowid),
            "name": payload.name.strip(),
            "icon": payload.icon,
            "frequency": payload.frequency,
            "reminder_time": payload.reminder_time,
            "weekdays": weekdays,
        }


@app.post("/api/habits/toggle")
def toggle_habit(payload: HabitToggle):
    with db() as con:
        exists = con.execute(
            "SELECT id FROM habit_logs WHERE habit_id=? AND date=?",
            (payload.habit_id, payload.date),
        ).fetchone()
        if exists:
            con.execute("DELETE FROM habit_logs WHERE habit_id=? AND date=?", (payload.habit_id, payload.date))
            done = False
        else:
            con.execute(
                "INSERT OR IGNORE INTO habit_logs(habit_id, user_id, date, created_at) VALUES(?,?,?,?)",
                (payload.habit_id, payload.user_id, payload.date, now_msk().isoformat()),
            )
            done = True
        streak = streak_for_habit(con, payload.habit_id)
        con.execute("UPDATE habits SET streak=? WHERE id=?", (streak, payload.habit_id))
        return {"done": done, "streak": streak}


@app.delete("/api/habits/{habit_id}")
def delete_habit(habit_id: int):
    with db() as con:
        con.execute("DELETE FROM habit_logs WHERE habit_id=?", (habit_id,))
        con.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    return {"ok": True}


@app.patch("/api/habits/{habit_id}")
def update_habit(habit_id: int, payload: HabitUpdate):
    weekdays = normalize_weekdays(payload.weekdays)
    with db() as con:
        row = con.execute("SELECT id FROM habits WHERE id=?", (habit_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Habit not found")
        con.execute(
            """
            UPDATE habits
            SET name=?, icon=?, frequency=?, reminder_time=?, weekdays=?
            WHERE id=?
            """,
            (
                payload.name.strip(),
                payload.icon,
                payload.frequency,
                payload.reminder_time,
                json.dumps(weekdays, ensure_ascii=False) if weekdays else None,
                habit_id,
            ),
        )
    return {
        "ok": True,
        "id": habit_id,
        "name": payload.name.strip(),
        "icon": payload.icon,
        "frequency": payload.frequency,
        "reminder_time": payload.reminder_time,
        "weekdays": weekdays,
    }


@app.get("/api/tasks/{user_id}")
def get_tasks(user_id: int):
    with db() as con:
        rows = con.execute(
            """
            SELECT id, name, section, priority, deadline, done, done_at, from_ai
            FROM tasks
            WHERE user_id=? AND deleted=0
            ORDER BY CASE WHEN done=1 THEN 1 ELSE 0 END, created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [
            {
                "id": int(r["id"]),
                "name": r["name"],
                "section": r["section"] or "work",
                "priority": r["priority"] or "mid",
                "deadline": r["deadline"],
                "done": bool(r["done"]),
                "done_at": r["done_at"],
                "from_ai": bool(r["from_ai"]),
            }
            for r in rows
        ]


@app.post("/api/tasks")
def add_task(payload: TaskCreate):
    with db() as con:
        cur = con.execute(
            """
            INSERT INTO tasks(user_id, name, section, priority, deadline, done, done_at, from_ai, created_at, deleted)
            VALUES(?,?,?,?,?,0,NULL,?,?,0)
            """,
            (
                payload.user_id,
                payload.name.strip(),
                payload.section,
                payload.priority,
                payload.deadline,
                1 if payload.from_ai else 0,
                now_msk().isoformat(),
            ),
        )
        return {
            "id": int(cur.lastrowid),
            "name": payload.name.strip(),
            "section": payload.section,
            "priority": payload.priority,
            "deadline": payload.deadline,
            "done": False,
            "done_at": None,
            "from_ai": payload.from_ai,
        }


@app.patch("/api/tasks/{task_id}")
def patch_task(task_id: int, payload: TaskPatch):
    with db() as con:
        row = con.execute("SELECT id FROM tasks WHERE id=? AND deleted=0", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")
        done_at = now_msk().isoformat() if payload.done else None
        con.execute("UPDATE tasks SET done=?, done_at=? WHERE id=?", (1 if payload.done else 0, done_at, task_id))
    return {"ok": True}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    with db() as con:
        con.execute("UPDATE tasks SET deleted=1 WHERE id=?", (task_id,))
    return {"ok": True}


@app.get("/api/stats/{user_id}")
def get_stats(user_id: int, week_offset: int = 0):
    with db() as con:
        return calc_week_stats(con, user_id, week_offset)


def get_system_prompt() -> str:
    return (
        "Ты — Life OS, дружелюбный AI-ассистент для продуктивности. Отвечай коротко и по делу, на языке пользователя.\n"
        f"Сегодня: {now_msk().strftime('%d.%m.%Y %H:%M')} (Москва).\n\n"
        "Ты умеешь:\n"
        "- Обсуждать планы, цели, мотивацию, продуктивность, привычки\n"
        "- Давать советы по организации времени и задач\n"
        "- Помогать составлять планы на день/неделю\n"
        "- Просто общаться и поддерживать\n\n"
        "Когда пользователь ЯВНО просит добавить задачу или привычку, добавь в конец ответа спец-блоки:\n"
        '<tasks>[{"name":"...","section":"work|life","priority":"high|mid|low","deadline":"YYYY-MM-DDThh:mm"|null}]</tasks>\n'
        '<habits>[{"name":"...","icon":"emoji","frequency":"Каждый день|Пн-Пт|Пн, Ср, Пт","reminder_time":"HH:MM"|null,"weekdays":[]}]</habits>\n'
        "Если задач/привычек нет — НЕ добавляй эти блоки.\n"
        "Не добавляй задачи/привычки если пользователь просто разговаривает, задаёт вопросы или обсуждает что-то."
    )


def call_openai(messages: list[dict[str, str]]) -> str:
    if not OPENAI_API_KEY:
        return "API-ключ OpenAI не настроен. Добавь OPENAI_API_KEY в .env файл."
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("OpenAI HTTP %s: %s", e.code, body[:500])
        return "Ошибка при обращении к AI. Проверь API-ключ и попробуй ещё раз."
    except Exception as e:
        logger.exception("OpenAI call failed: %s", e)
        return "Не удалось связаться с AI. Попробуй позже."


@app.post("/api/ai/chat")
def ai_chat(payload: AIChatRequest):
    messages: list[dict[str, str]] = [{"role": "system", "content": get_system_prompt()}]

    if payload.history:
        for h in payload.history[-10:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            content = re.sub(r"<tasks>[\s\S]*?</tasks>", "", content)
            content = re.sub(r"<habits>[\s\S]*?</habits>", "", content)
            content = content.strip()
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": payload.message.strip()})

    reply = call_openai(messages)

    return {"reply": reply, "actions": [], "reload_tasks": False, "reload_habits": False}
