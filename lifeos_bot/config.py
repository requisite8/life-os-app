"""Настройки бота: пути, переменные окружения, флаги."""

import os
import tempfile
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

APP_DIR = Path(__file__).resolve().parent.parent
DB_PRIMARY = APP_DIR / "lifeOS.db"
DB_FALLBACK = Path(tempfile.gettempdir()) / "lifeOS_local.db"

try:
    MSK = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MSK = timezone(timedelta(hours=3))


def load_local_env() -> dict[str, str]:
    env_path = APP_DIR / ".env"
    if not env_path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("﻿")
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip().lstrip("﻿")] = v.strip().strip("\"'")
    return out


_env = load_local_env()


def _setting(name: str, default: str = "") -> str:
    return (os.getenv(name) or _env.get(name, default)).strip()


BOT_TOKEN = _setting("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = _setting("WEBAPP_URL")
INTERNAL_API_URL = _setting("INTERNAL_API_URL") or "http://127.0.0.1:8000"
OPENAI_API_KEY = _setting("OPENAI_API_KEY")
STEPS_SHORTCUT_URL = _setting("STEPS_SHORTCUT_URL")  # iCloud-ссылка на готовую команду «Life OS Steps»

ALARM_ENABLED = False  # временно отключено
WEEKLY_STATS_ENABLED = False  # временно отключено
ADMIN_CHAT_ID = 5598605297
WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
