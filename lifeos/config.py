"""Настройки приложения: пути, переменные окружения, флаги."""

import logging
import os
from datetime import timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

APP_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = APP_DIR / "static"

try:
    MSK = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MSK = timezone(timedelta(hours=3))


def load_local_env() -> dict[str, str]:
    env_path = APP_DIR / ".env"
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        result[key.strip().lstrip("\ufeff")] = val.strip().strip("\"'")
    return result


_LOCAL_ENV = load_local_env()


def _setting(name: str, default: str = "") -> str:
    return (os.getenv(name) or _LOCAL_ENV.get(name, default)).strip()


TELEGRAM_BOT_TOKEN = _setting("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = _setting("WEBAPP_URL")
OPENAI_API_KEY = _setting("OPENAI_API_KEY")
TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else ""
ENABLE_EMBEDDED_WORKERS = _setting("ENABLE_EMBEDDED_WORKERS", "0").lower() in {"1", "true", "yes", "on"}

ALARM_ENABLED = False  # временно отключено
ADMIN_CHAT_ID = 5598605297
WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

logger = logging.getLogger("lifeos")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
