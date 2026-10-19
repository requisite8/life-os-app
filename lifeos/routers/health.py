"""Маршруты API: health."""

from datetime import timedelta

from fastapi import APIRouter
from fastapi import HTTPException

from ..database import db
from ..schemas import MealCreate, NutritionSet, SleepSet, StepsSet, WaterSet, WorkoutCreate
from ..timeutil import now_msk


router = APIRouter()


@router.get("/api/health/steps/{user_id}")
def get_steps(user_id: int):
    today = now_msk().date().isoformat()
    with db() as con:
        row = con.execute(
            "SELECT steps FROM health_steps WHERE user_id=? AND date=?", (user_id, today)
        ).fetchone()
    return {"steps": int(row["steps"]) if row else 0, "date": today}


@router.post("/api/health/steps")
def set_steps(payload: StepsSet):
    if payload.steps < 0:
        raise HTTPException(400, "steps must be >= 0")
    today = now_msk().date().isoformat()
    with db() as con:
        con.execute(
            """
            INSERT INTO health_steps(user_id, date, steps, updated_at) VALUES(?,?,?,?)
            ON CONFLICT(user_id, date) DO UPDATE SET steps=excluded.steps, updated_at=excluded.updated_at
            """,
            (payload.user_id, today, payload.steps, now_msk().isoformat()),
        )
    return {"ok": True, "steps": payload.steps, "date": today}


@router.get("/api/health/steps-hook")
def steps_hook(token: str = "", steps: float = -1):
    if not token or steps < 0 or steps > 200000:
        raise HTTPException(400, "bad token or steps")
    value = int(round(steps))
    today = now_msk().date().isoformat()
    with db() as con:
        row = con.execute("SELECT id FROM users WHERE steps_token=?", (token,)).fetchone()
        if not row:
            raise HTTPException(403, "unknown token")
        con.execute(
            """
            INSERT INTO health_steps(user_id, date, steps, updated_at) VALUES(?,?,?,?)
            ON CONFLICT(user_id, date) DO UPDATE SET steps=excluded.steps, updated_at=excluded.updated_at
            """,
            (row["id"], today, value, now_msk().isoformat()),
        )
    return {"ok": True, "steps": value, "date": today}


@router.get("/api/health/water/{user_id}")
def get_water(user_id: int):
    today = now_msk().date().isoformat()
    with db() as con:
        row = con.execute(
            "SELECT ml FROM health_water WHERE user_id=? AND date=?", (user_id, today)
        ).fetchone()
    return {"ml": int(row["ml"]) if row else 0, "date": today}


@router.post("/api/health/water")
def set_water(payload: WaterSet):
    if payload.ml < 0:
        raise HTTPException(400, "ml must be >= 0")
    today = now_msk().date().isoformat()
    with db() as con:
        con.execute(
            """
            INSERT INTO health_water(user_id, date, ml, updated_at) VALUES(?,?,?,?)
            ON CONFLICT(user_id, date) DO UPDATE SET ml=excluded.ml, updated_at=excluded.updated_at
            """,
            (payload.user_id, today, payload.ml, now_msk().isoformat()),
        )
    return {"ok": True, "ml": payload.ml, "date": today}


@router.get("/api/health/sleep/{user_id}")
def get_sleep(user_id: int):
    today = now_msk().date().isoformat()
    with db() as con:
        row = con.execute(
            "SELECT hours, bedtime, waketime, quality FROM health_sleep WHERE user_id=? AND date=?",
            (user_id, today),
        ).fetchone()
    if not row:
        return {"hours": 0, "bedtime": None, "waketime": None, "quality": None, "date": today}
    return {
        "hours": row["hours"],
        "bedtime": row["bedtime"],
        "waketime": row["waketime"],
        "quality": row["quality"],
        "date": today,
    }


@router.post("/api/health/sleep")
def set_sleep(payload: SleepSet):
    if payload.hours < 0:
        raise HTTPException(400, "hours must be >= 0")
    today = now_msk().date().isoformat()
    with db() as con:
        con.execute(
            """
            INSERT INTO health_sleep(user_id, date, hours, bedtime, waketime, quality, updated_at)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                hours=excluded.hours, bedtime=excluded.bedtime,
                waketime=excluded.waketime, quality=excluded.quality,
                updated_at=excluded.updated_at
            """,
            (payload.user_id, today, payload.hours, payload.bedtime, payload.waketime, payload.quality, now_msk().isoformat()),
        )
    return {"ok": True, "date": today}


@router.get("/api/health/nutrition/{user_id}")
def get_nutrition(user_id: int):
    today = now_msk().date().isoformat()
    with db() as con:
        row = con.execute(
            """
            SELECT COALESCE(SUM(calories),0) c, COALESCE(SUM(protein),0) p,
                   COALESCE(SUM(fat),0) f, COALESCE(SUM(carbs),0) cb
            FROM health_meals_log WHERE user_id=? AND date=?
            """,
            (user_id, today),
        ).fetchone()
    return {
        "calories": int(row["c"]), "protein": int(row["p"]),
        "fat": int(row["f"]), "carbs": int(row["cb"]), "date": today,
    }


@router.post("/api/health/nutrition")
def set_nutrition(payload: NutritionSet):
    if payload.calories < 0:
        raise HTTPException(400, "calories must be >= 0")
    today = now_msk().date().isoformat()
    with db() as con:
        con.execute(
            "INSERT INTO health_meals_log(user_id, date, description, calories, protein, fat, carbs, source, created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (payload.user_id, today, "Быстрый ввод", payload.calories, payload.protein, payload.fat, payload.carbs,
             "manual", now_msk().isoformat()),
        )
    return {"ok": True, "date": today}


@router.post("/api/health/meals")
def add_meal_log(payload: MealCreate):
    if payload.calories < 0:
        raise HTTPException(400, "calories must be >= 0")
    today = now_msk().date().isoformat()
    with db() as con:
        cur = con.execute(
            "INSERT INTO health_meals_log(user_id, date, description, calories, protein, fat, carbs, source, created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (payload.user_id, today, payload.description.strip(), payload.calories, payload.protein,
             payload.fat, payload.carbs, payload.source, now_msk().isoformat()),
        )
    return {"id": int(cur.lastrowid), "date": today}


@router.get("/api/health/meals/{user_id}")
def list_meals(user_id: int):
    today = now_msk().date().isoformat()
    with db() as con:
        rows = con.execute(
            "SELECT id, description, calories, protein, fat, carbs, source, created_at "
            "FROM health_meals_log WHERE user_id=? AND date=? ORDER BY id DESC",
            (user_id, today),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/health/workouts")
def add_workout(payload: WorkoutCreate):
    today = now_msk().date().isoformat()
    with db() as con:
        cur = con.execute(
            "INSERT INTO health_workouts(user_id, date, type, description, duration_min, calories, source, created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (payload.user_id, today, payload.type.strip(), payload.description.strip(),
             payload.duration_min, payload.calories, payload.source, now_msk().isoformat()),
        )
    return {"id": int(cur.lastrowid), "date": today}


@router.get("/api/health/workouts/{user_id}")
def list_workouts(user_id: int):
    today = now_msk().date().isoformat()
    with db() as con:
        rows = con.execute(
            "SELECT id, type, description, duration_min, calories, source, created_at "
            "FROM health_workouts WHERE user_id=? AND date=? ORDER BY id DESC",
            (user_id, today),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/health/stats/{user_id}")
def get_health_stats(user_id: int, days: int = 7):
    days = max(1, min(30, days))
    today = now_msk().date()
    result = []
    with db() as con:
        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            steps = con.execute(
                "SELECT steps FROM health_steps WHERE user_id=? AND date=?", (user_id, d)
            ).fetchone()
            water = con.execute(
                "SELECT ml FROM health_water WHERE user_id=? AND date=?", (user_id, d)
            ).fetchone()
            sleep = con.execute(
                "SELECT hours FROM health_sleep WHERE user_id=? AND date=?", (user_id, d)
            ).fetchone()
            cal = con.execute(
                "SELECT COALESCE(SUM(calories),0) c FROM health_meals_log WHERE user_id=? AND date=?", (user_id, d)
            ).fetchone()
            workouts = con.execute(
                "SELECT COUNT(*) c, COALESCE(SUM(duration_min),0) m FROM health_workouts WHERE user_id=? AND date=?",
                (user_id, d),
            ).fetchone()
            result.append({
                "date": d,
                "steps": int(steps["steps"]) if steps else 0,
                "water_ml": int(water["ml"]) if water else 0,
                "sleep_hours": sleep["hours"] if sleep else 0,
                "calories": int(cal["c"]),
                "workouts_count": int(workouts["c"]),
                "workouts_min": int(workouts["m"]),
            })
    return result
