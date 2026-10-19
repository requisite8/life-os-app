"""Фоновый цикл напоминаний."""

from datetime import datetime
from datetime import timedelta
import asyncio

from aiogram import Bot

from .config import MSK, WEEKLY_STATS_ENABLED
from .database import db
from .queries import week_stats
from .schedule import is_habit_active_today, now_msk, parse_weekdays


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
                if WEEKLY_STATS_ENABLED and now.weekday() == 0 and now.hour == 9 and now.minute == 0:
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
                        con.commit()
        except Exception:
            pass
        await asyncio.sleep(60)
