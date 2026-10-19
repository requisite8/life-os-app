"""Время и недели (часовой пояс Москвы)."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from .config import MSK


def now_msk() -> datetime:
    return datetime.now(MSK)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_client_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=MSK)
        return dt.astimezone(MSK)
    except ValueError:
        return None


def week_range(week_offset: int) -> tuple[datetime, datetime]:
    now = now_msk()
    monday = now - timedelta(days=now.weekday())
    monday = datetime(monday.year, monday.month, monday.day, tzinfo=MSK) + timedelta(
        weeks=week_offset
    )
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday
