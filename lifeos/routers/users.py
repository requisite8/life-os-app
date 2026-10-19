"""Маршруты API: users."""

from fastapi import APIRouter

from ..config import ADMIN_CHAT_ID
from ..database import db
from ..schemas import HealthProfilePatch, UserCreate, UserSettingsPatch
from ..telegram import send_tg


router = APIRouter()


@router.post("/api/users")
def create_or_get_user(payload: UserCreate):
    telegram_id = payload.telegram_id if payload.telegram_id and payload.telegram_id > 0 else None
    is_new = False
    with db() as con:
        if telegram_id is not None:
            row = con.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
            if row:
                con.execute(
                    "UPDATE users SET first_name=?, username=? WHERE id=?",
                    (payload.first_name, payload.username, row["id"]),
                )
                result = {"id": int(row["id"]), "telegram_id": telegram_id}
            else:
                cur = con.execute(
                    "INSERT INTO users(telegram_id, first_name, username) VALUES(?,?,?)",
                    (telegram_id, payload.first_name, payload.username),
                )
                is_new = True
                result = {"id": int(cur.lastrowid), "telegram_id": telegram_id}
        else:
            # fallback guest when tg user is absent
            cur = con.execute(
                "INSERT INTO users(first_name, username) VALUES(?,?)",
                (payload.first_name, payload.username),
            )
            result = {"id": int(cur.lastrowid), "telegram_id": None}

    if is_new:
        uname = f"@{payload.username}" if payload.username else "без username"
        with db() as con:
            total = con.execute("SELECT COUNT(*) c FROM users WHERE telegram_id IS NOT NULL").fetchone()["c"]
        send_tg(
            ADMIN_CHAT_ID,
            f"🆕 Новый пользователь мини-аппа: {payload.first_name} ({uname}, id {telegram_id})\n"
            f"Всего пользователей: {total}",
        )

    return result


@router.get("/api/users/{user_id}/settings")
def get_user_settings(user_id: int):
    with db() as con:
        row = con.execute("SELECT alarm_optin FROM users WHERE id=?", (user_id,)).fetchone()
    return {"alarm_optin": (row["alarm_optin"] if row else None)}


@router.patch("/api/users/{user_id}/settings")
def patch_user_settings(user_id: int, payload: UserSettingsPatch):
    with db() as con:
        con.execute("UPDATE users SET alarm_optin=? WHERE id=?", (1 if payload.alarm_optin else 0, user_id))
    return {"ok": True}


@router.get("/api/users/{user_id}/health-profile")
def get_health_profile(user_id: int):
    with db() as con:
        row = con.execute(
            "SELECT fitness_goal, fitness_level FROM users WHERE id=?", (user_id,)
        ).fetchone()
    return {"fitness_goal": row["fitness_goal"] if row else None, "fitness_level": row["fitness_level"] if row else None}


@router.patch("/api/users/{user_id}/health-profile")
def patch_health_profile(user_id: int, payload: HealthProfilePatch):
    with db() as con:
        con.execute(
            "UPDATE users SET fitness_goal=COALESCE(?, fitness_goal), fitness_level=COALESCE(?, fitness_level) WHERE id=?",
            (payload.fitness_goal, payload.fitness_level, user_id),
        )
    return {"ok": True}
