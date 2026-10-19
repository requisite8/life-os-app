"""Маршруты API: habits."""

from datetime import timedelta
import json

from fastapi import APIRouter
from fastapi import HTTPException

from ..alarms import offer_alarm
from ..database import db
from ..habit_utils import normalize_weekdays, parse_weekdays_json, streak_for_habit
from ..schemas import HabitCreate, HabitToggle, HabitUpdate
from ..timeutil import now_msk


router = APIRouter()


@router.get("/api/habits/{user_id}")
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


@router.post("/api/habits")
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
        new_id = int(cur.lastrowid)

    if payload.reminder_time:
        offer_alarm(payload.user_id, payload.icon, payload.name.strip(), payload.reminder_time)

    return {
        "id": new_id,
        "name": payload.name.strip(),
        "icon": payload.icon,
        "frequency": payload.frequency,
        "reminder_time": payload.reminder_time,
        "weekdays": weekdays,
    }


@router.post("/api/habits/toggle")
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


@router.delete("/api/habits/{habit_id}")
def delete_habit(habit_id: int):
    with db() as con:
        con.execute("DELETE FROM habit_logs WHERE habit_id=?", (habit_id,))
        con.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    return {"ok": True}


@router.patch("/api/habits/{habit_id}")
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
