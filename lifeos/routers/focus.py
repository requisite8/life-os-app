"""Маршруты API: focus."""

from datetime import timedelta

from fastapi import APIRouter
from fastapi import HTTPException

from ..database import db
from ..schemas import FocusCreate
from ..stats import calc_week_stats
from ..telegram import send_focus_finished
from ..timeutil import now_msk


router = APIRouter()


@router.get("/api/focus/{user_id}")
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


@router.post("/api/focus")
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


@router.get("/api/stats/{user_id}")
def get_stats(user_id: int, week_offset: int = 0):
    with db() as con:
        return calc_week_stats(con, user_id, week_offset)
