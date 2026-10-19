"""Фоновые задачи: напоминания и встроенный polling бота."""

from datetime import timedelta
import asyncio

from .bot_commands import handle_bot_text
from .config import TELEGRAM_BOT_TOKEN, logger
from .database import db
from .habit_utils import is_frequency_active, parse_weekdays_json
from .stats import calc_week_stats
from .telegram import send_tg, tg_request
from .timeutil import now_msk, parse_client_dt, utc_now_iso


stop_event = asyncio.Event()
_bot_offset = 0
_tasks: list[asyncio.Task] = []


async def notifications_worker() -> None:
    while not stop_event.is_set():
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
    while not stop_event.is_set():
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


def start() -> None:
    stop_event.clear()
    _tasks[:] = [asyncio.create_task(notifications_worker()), asyncio.create_task(bot_polling_loop())]


async def stop() -> None:
    stop_event.set()
    for t in _tasks:
        t.cancel()
    await asyncio.sleep(0)
