"""Помощники для привычек: серии, частота, дни недели."""

from datetime import timedelta
import json
import sqlite3

from .timeutil import now_msk


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
