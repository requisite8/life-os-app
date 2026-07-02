import asyncio
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup


APP_DIR = Path(__file__).resolve().parent
DB_PRIMARY = APP_DIR / "lifeOS.db"
DB_FALLBACK = Path(tempfile.gettempdir()) / "lifeOS_local.db"

try:
    MSK = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MSK = timezone(timedelta(hours=3))


def load_local_env() -> dict[str, str]:
    env_path = APP_DIR / ".env"
    if not env_path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip().lstrip("\ufeff")] = v.strip().strip("\"'")
    return out


_env = load_local_env()
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or _env.get("TELEGRAM_BOT_TOKEN", "")).strip()
WEBAPP_URL = (os.getenv("WEBAPP_URL") or _env.get("WEBAPP_URL", "")).strip()


def db_path() -> Path:
    if DB_PRIMARY.exists():
        return DB_PRIMARY
    return DB_FALLBACK


@contextmanager
def db():
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def now_msk() -> datetime:
    return datetime.now(MSK)


def parse_weekdays(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        import json
        v = json.loads(raw)
        if isinstance(v, list):
            return sorted({int(x) for x in v if isinstance(x, int) or str(x).isdigit()})
    except Exception:
        return []
    return []


def is_habit_active_today(frequency: str | None, weekdays: list[int]) -> bool:
    dow = now_msk().weekday()
    if weekdays:
        return dow in weekdays
    if not frequency or frequency == "Каждый день":
        return True
    if frequency == "Пн-Пт":
        return dow <= 4
    if frequency == "Пн, Ср, Пт":
        return dow in (0, 2, 4)
    return True


def ensure_user(telegram_id: int, first_name: str, username: str | None, chat_id: int) -> int:
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
            return int(row["id"])
        cur = con.execute(
            "INSERT INTO users(telegram_id, first_name, username, chat_id) VALUES(?,?,?,?)",
            (telegram_id, first_name, username, chat_id),
        )
        return int(cur.lastrowid)


def week_stats(user_id: int, offset: int = 0) -> dict:
    now = now_msk()
    monday = now - timedelta(days=now.weekday()) + timedelta(weeks=offset)
    monday = datetime(monday.year, monday.month, monday.day, tzinfo=MSK)
    sunday = monday + timedelta(days=7)
    with db() as con:
        focus = con.execute(
            "SELECT COALESCE(SUM(duration_min),0) v FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<?",
            (user_id, monday.isoformat(), sunday.isoformat()),
        ).fetchone()["v"]
        sessions = con.execute(
            "SELECT COUNT(*) c FROM focus_sessions WHERE user_id=? AND created_at>=? AND created_at<?",
            (user_id, monday.isoformat(), sunday.isoformat()),
        ).fetchone()["c"]
        tasks_done = con.execute(
            "SELECT COUNT(*) c FROM tasks WHERE user_id=? AND deleted=0 AND done=1 AND done_at>=? AND done_at<?",
            (user_id, monday.isoformat(), sunday.isoformat()),
        ).fetchone()["c"]
    return {"focus": int(round(focus or 0)), "sessions": int(sessions or 0), "tasks_done": int(tasks_done or 0)}


def list_tasks(user_id: int) -> str:
    with db() as con:
        rows = con.execute(
            """
            SELECT name, section, priority, deadline
            FROM tasks
            WHERE user_id=? AND deleted=0 AND done=0
            ORDER BY CASE WHEN deadline IS NULL THEN 1 ELSE 0 END, deadline
            LIMIT 15
            """,
            (user_id,),
        ).fetchall()
    if not rows:
        return "Активных задач нет."
    out = ["Текущие задачи:"]
    for i, r in enumerate(rows, start=1):
        dl = f" · {r['deadline']}" if r["deadline"] else ""
        out.append(f"{i}. {r['name']} ({r['section']}/{r['priority']}){dl}")
    return "\n".join(out)


def list_habits(user_id: int) -> str:
    with db() as con:
        rows = con.execute(
            "SELECT icon, name, frequency, reminder_time, weekdays FROM habits WHERE user_id=? ORDER BY id DESC LIMIT 15",
            (user_id,),
        ).fetchall()
    if not rows:
        return "Привычек пока нет."
    out = ["Текущие привычки:"]
    for i, r in enumerate(rows, start=1):
        time_part = f" · ⏰ {r['reminder_time']}" if r["reminder_time"] else ""
        days = parse_weekdays(r["weekdays"])
        day_part = ""
        if days:
            names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            day_part = " · " + ", ".join(names[d] for d in days if 0 <= d <= 6)
        out.append(f"{i}. {r['icon']} {r['name']} ({r['frequency']}){day_part}{time_part}")
    return "\n".join(out)


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="✅ Мои привычки")],
            [KeyboardButton(text="📊 Моя неделя"), KeyboardButton(text="🚀 Открыть мини-приложение")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )


async def reminder_loop(bot: Bot):
    while True:
        try:
            now = now_msk()
            now_hm = now.strftime("%H:%M")
            today = now.date().isoformat()
            with db() as con:
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

                # task reminders (1 hour before)
                tasks = con.execute(
                    """
                    SELECT t.id, t.user_id, t.name, t.deadline, u.chat_id
                    FROM tasks t
                    JOIN users u ON u.id=t.user_id
                    WHERE t.deleted=0 AND t.done=0 AND t.deadline IS NOT NULL AND u.chat_id IS NOT NULL
                    """
                ).fetchall()
                for t in tasks:
                    try:
                        dl = datetime.fromisoformat(t["deadline"])
                    except Exception:
                        continue
                    if dl.tzinfo is None:
                        dl = dl.replace(tzinfo=MSK)
                    remind_at = dl - timedelta(hours=1)
                    if remind_at <= now <= dl + timedelta(minutes=5):
                        k = f"{today}:{t['id']}"
                        exists = con.execute(
                            "SELECT 1 FROM reminder_logs WHERE user_id=? AND kind='task' AND ref_id=? AND date_key=?",
                            (t["user_id"], t["id"], k),
                        ).fetchone()
                        if exists:
                            continue
                        await bot.send_message(int(t["chat_id"]), f"Через 1 час дедлайн задачи:\n{t['name']}\n⏰ {dl.strftime('%d.%m %H:%M')}")
                        con.execute(
                            "INSERT OR IGNORE INTO reminder_logs(user_id, kind, ref_id, date_key) VALUES(?,?,?,?)",
                            (t["user_id"], "task", t["id"], k),
                        )

                # habit reminders
                habits = con.execute(
                    """
                    SELECT h.id, h.user_id, h.name, h.icon, h.reminder_time, h.frequency, h.weekdays, u.chat_id
                    FROM habits h
                    JOIN users u ON u.id=h.user_id
                    WHERE h.reminder_time IS NOT NULL AND h.reminder_time!='' AND u.chat_id IS NOT NULL
                    """
                ).fetchall()
                for h in habits:
                    if h["reminder_time"] != now_hm:
                        continue
                    if not is_habit_active_today(h["frequency"], parse_weekdays(h["weekdays"])):
                        continue
                    k = today
                    exists = con.execute(
                        "SELECT 1 FROM reminder_logs WHERE user_id=? AND kind='habit' AND ref_id=? AND date_key=?",
                        (h["user_id"], h["id"], k),
                    ).fetchone()
                    if exists:
                        continue
                    await bot.send_message(int(h["chat_id"]), f"Напоминание по привычке:\n{h['icon']} {h['name']}\n⏰ {h['reminder_time']}")
                    con.execute(
                        "INSERT OR IGNORE INTO reminder_logs(user_id, kind, ref_id, date_key) VALUES(?,?,?,?)",
                        (h["user_id"], "habit", h["id"], k),
                    )

                # focus finished notifications
                sessions = con.execute(
                    """
                    SELECT f.id, f.user_id, f.duration_min, f.category, u.chat_id
                    FROM focus_sessions f
                    JOIN users u ON u.id=f.user_id
                    WHERE u.chat_id IS NOT NULL
                    ORDER BY f.id DESC LIMIT 50
                    """
                ).fetchall()
                for s in sessions:
                    k = str(s["id"])
                    exists = con.execute(
                        "SELECT 1 FROM reminder_logs WHERE user_id=? AND kind='focus_done' AND ref_id=? AND date_key=?",
                        (s["user_id"], s["id"], k),
                    ).fetchone()
                    if exists:
                        continue
                    await bot.send_message(int(s["chat_id"]), f"Фокус завершён: {int(s['duration_min'])} мин.\nКатегория: {s['category'] or 'Фокус'}")
                    con.execute(
                        "INSERT OR IGNORE INTO reminder_logs(user_id, kind, ref_id, date_key) VALUES(?,?,?,?)",
                        (s["user_id"], "focus_done", s["id"], k),
                    )

                # weekly digest monday 09:00
                if now.weekday() == 0 and now.hour == 9:
                    users = con.execute("SELECT id, chat_id, weekly_last_sent FROM users WHERE chat_id IS NOT NULL").fetchall()
                    monday_key = today
                    for u in users:
                        if u["weekly_last_sent"] == monday_key:
                            continue
                        st = week_stats(int(u["id"]), -1)
                        await bot.send_message(
                            int(u["chat_id"]),
                            "Недельная статистика (прошлая неделя):\n"
                            f"Фокус: {st['focus']} мин\n"
                            f"Сессии: {st['sessions']}\n"
                            f"Выполнено задач: {st['tasks_done']}",
                        )
                        con.execute("UPDATE users SET weekly_last_sent=? WHERE id=?", (monday_key, u["id"]))
        except Exception:
            pass
        await asyncio.sleep(60)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    kb = main_keyboard()

    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        user = message.from_user
        ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
        text = (
            "Life OS mini app:\n"
            "1) Фокус-таймер\n"
            "2) Задачи с напоминанием за 1 час\n"
            "3) Привычки с временем напоминания\n"
            "4) Недельная статистика\n\n"
            "Команды: /tasks /habits /week /help"
        )
        if WEBAPP_URL:
            text += f"\n\nОткрыть мини-приложение:\n{WEBAPP_URL}"
        await message.answer(text, reply_markup=kb)

    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        await message.answer("/start /tasks /habits /week", reply_markup=kb)

    @dp.message(Command("tasks"))
    async def cmd_tasks(message: Message):
        user = message.from_user
        uid = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
        await message.answer(list_tasks(uid), reply_markup=kb)

    @dp.message(Command("habits"))
    async def cmd_habits(message: Message):
        user = message.from_user
        uid = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
        await message.answer(list_habits(uid), reply_markup=kb)

    @dp.message(Command("week"))
    async def cmd_week(message: Message):
        user = message.from_user
        uid = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
        st = week_stats(uid, 0)
        await message.answer(
            f"Текущая неделя:\nФокус: {st['focus']} мин\nСессии: {st['sessions']}\nЗадач выполнено: {st['tasks_done']}",
            reply_markup=kb,
        )

    @dp.message(F.text == "📋 Мои задачи")
    async def btn_tasks(message: Message):
        await cmd_tasks(message)

    @dp.message(F.text == "✅ Мои привычки")
    async def btn_habits(message: Message):
        await cmd_habits(message)

    @dp.message(F.text == "📊 Моя неделя")
    async def btn_week(message: Message):
        await cmd_week(message)

    @dp.message(F.text == "🚀 Открыть мини-приложение")
    async def btn_open(message: Message):
        text = WEBAPP_URL if WEBAPP_URL else "WEBAPP_URL пока не задан в .env"
        await message.answer(text, reply_markup=kb)

    @dp.message(F.text == "❓ Помощь")
    async def btn_help(message: Message):
        await cmd_help(message)

    reminder_task = asyncio.create_task(reminder_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
