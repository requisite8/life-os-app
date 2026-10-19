"""Вызовы ИИ и разбор ответов."""

import aiohttp
import json
import re

from .config import INTERNAL_API_URL, OPENAI_API_KEY


async def call_ai_chat(user_id: int, message: str) -> str:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.post(
            f"{INTERNAL_API_URL}/api/ai/chat",
            json={"user_id": user_id, "message": message, "history": []},
        ) as resp:
            data = await resp.json()
            return str(data.get("reply") or "")


async def call_openai_vision(image_b64: str) -> str:
    if not OPENAI_API_KEY:
        return ""
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты оцениваешь калорийность и БЖУ еды по фотографии. Определи, что на фото, "
                    "и оцени примерные калории, белки, жиры, углеводы по типичным порциям (приблизительно, "
                    "не отказывайся оценивать из-за неточности). Ответь ТОЛЬКО одним блоком, без лишнего текста:\n"
                    '<meal>[{"description":"...","calories":число,"protein":число,"fat":число,"carbs":число}]</meal>'
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Что это за еда и сколько в ней калорий и БЖУ?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            },
        ],
        "max_tokens": 400,
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        ) as resp:
            data = await resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                return ""


def parse_ai_reply(text: str) -> tuple[str, list, list, list, list, list]:
    task_match = re.search(r"<tasks>([\s\S]*?)</tasks>", text, re.I)
    habit_match = re.search(r"<habits>([\s\S]*?)</habits>", text, re.I)
    done_match = re.search(r"<done>([\s\S]*?)</done>", text, re.I)
    meal_match = re.search(r"<meal>([\s\S]*?)</meal>", text, re.I)
    workout_match = re.search(r"<workout>([\s\S]*?)</workout>", text, re.I)

    clean = re.sub(r"<tasks>[\s\S]*?</tasks>", "", text, flags=re.I)
    clean = re.sub(r"<habits>[\s\S]*?</habits>", "", clean, flags=re.I)
    clean = re.sub(r"<done>[\s\S]*?</done>", "", clean, flags=re.I)
    clean = re.sub(r"<meal>[\s\S]*?</meal>", "", clean, flags=re.I)
    clean = re.sub(r"<workout>[\s\S]*?</workout>", "", clean, flags=re.I)
    clean = clean.strip()

    def _load(m: re.Match | None) -> list:
        if not m:
            return []
        try:
            value = json.loads(m.group(1).strip())
            return value if isinstance(value, list) else []
        except Exception:
            return []

    return clean, _load(task_match), _load(habit_match), _load(done_match), _load(meal_match), _load(workout_match)
