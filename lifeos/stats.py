"""Недельная статистика фокуса и задач."""

from datetime import timedelta
from typing import Any
import sqlite3

from .timeutil import week_range


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
