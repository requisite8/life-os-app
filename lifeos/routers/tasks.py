"""Маршруты API: tasks."""

from fastapi import APIRouter
from fastapi import HTTPException

from ..database import db
from ..schemas import TaskCreate, TaskPatch
from ..timeutil import now_msk


router = APIRouter()


@router.get("/api/tasks/{user_id}")
def get_tasks(user_id: int):
    with db() as con:
        rows = con.execute(
            """
            SELECT id, name, section, priority, deadline, done, done_at, from_ai
            FROM tasks
            WHERE user_id=? AND deleted=0
            ORDER BY CASE WHEN done=1 THEN 1 ELSE 0 END, created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [
            {
                "id": int(r["id"]),
                "name": r["name"],
                "section": r["section"] or "work",
                "priority": r["priority"] or "mid",
                "deadline": r["deadline"],
                "done": bool(r["done"]),
                "done_at": r["done_at"],
                "from_ai": bool(r["from_ai"]),
            }
            for r in rows
        ]


@router.post("/api/tasks")
def add_task(payload: TaskCreate):
    with db() as con:
        cur = con.execute(
            """
            INSERT INTO tasks(user_id, name, section, priority, deadline, done, done_at, from_ai, created_at, deleted)
            VALUES(?,?,?,?,?,0,NULL,?,?,0)
            """,
            (
                payload.user_id,
                payload.name.strip(),
                payload.section,
                payload.priority,
                payload.deadline,
                1 if payload.from_ai else 0,
                now_msk().isoformat(),
            ),
        )
        return {
            "id": int(cur.lastrowid),
            "name": payload.name.strip(),
            "section": payload.section,
            "priority": payload.priority,
            "deadline": payload.deadline,
            "done": False,
            "done_at": None,
            "from_ai": payload.from_ai,
        }


@router.patch("/api/tasks/{task_id}")
def patch_task(task_id: int, payload: TaskPatch):
    with db() as con:
        row = con.execute("SELECT id FROM tasks WHERE id=? AND deleted=0", (task_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Task not found")
        done_at = now_msk().isoformat() if payload.done else None
        con.execute("UPDATE tasks SET done=?, done_at=? WHERE id=?", (1 if payload.done else 0, done_at, task_id))
    return {"ok": True}


@router.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    with db() as con:
        con.execute("UPDATE tasks SET deleted=1 WHERE id=?", (task_id,))
    return {"ok": True}
