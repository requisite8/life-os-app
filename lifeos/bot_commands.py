"""Тексты и команды встроенного бота (запасной вариант)."""

import sqlite3

from .config import WEBAPP_URL
from .database import db
from .stats import calc_week_stats
from .telegram import send_tg
from .timeutil import parse_client_dt


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
