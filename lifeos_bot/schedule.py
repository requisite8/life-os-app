"""Время и расписание привычек."""

from datetime import datetime

from .config import MSK


def now_msk() -> datetime:
    return datetime.now(MSK)


def parse_weekdays(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        import json
        v = json.loads(raw)
        if isinstance(v, list):
            return sorted({int(x) for x in v if isinstance(x, int) or str(x).isdigit()})
    except Exception:
        return []
    return []


def is_habit_active_today(frequency: str | None, weekdays: list[int]) -> bool:
    dow = now_msk().weekday()
    if weekdays:
        return dow in weekdays
    if not frequency or frequency == "Каждый день":
        return True
    if frequency == "Пн-Пт":
        return dow <= 4
    if frequency == "Пн, Ср, Пт":
        return dow in (0, 2, 4)
    return True
