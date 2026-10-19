"""Тексты и статистика для команд бота."""

from datetime import datetime
from datetime import timedelta

from .config import MSK
from .database import db
from .schedule import now_msk, parse_weekdays


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
