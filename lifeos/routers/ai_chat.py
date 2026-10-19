"""Маршруты API: ai_chat."""

import re

from fastapi import APIRouter

from ..ai import call_openai, get_system_prompt
from ..database import db
from ..schemas import AIChatRequest


router = APIRouter()


@router.post("/api/ai/chat")
def ai_chat(payload: AIChatRequest):
    with db() as con:
        prow = con.execute(
            "SELECT fitness_goal, fitness_level FROM users WHERE id=?", (payload.user_id,)
        ).fetchone()
    profile = dict(prow) if prow else None

    messages: list[dict[str, str]] = [{"role": "system", "content": get_system_prompt(profile)}]

    if payload.history:
        for h in payload.history[-10:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            content = re.sub(r"<tasks>[\s\S]*?</tasks>", "", content)
            content = re.sub(r"<habits>[\s\S]*?</habits>", "", content)
            content = re.sub(r"<done>[\s\S]*?</done>", "", content)
            content = re.sub(r"<meal>[\s\S]*?</meal>", "", content)
            content = re.sub(r"<workout>[\s\S]*?</workout>", "", content)
            content = content.strip()
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": payload.message.strip()})

    reply = call_openai(messages)

    return {"reply": reply, "actions": [], "reload_tasks": False, "reload_habits": False}
