"""Маршруты API: pages."""

import re
import urllib.parse

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .. import database
from ..config import ENABLE_EMBEDDED_WORKERS, STATIC_DIR, TELEGRAM_BOT_TOKEN, WEBAPP_URL


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def read_root():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@router.get("/alarm-redirect", response_class=HTMLResponse)
def alarm_redirect(t: str = "", name: str = "Будильник"):
    if not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", t):
        return HTMLResponse("<p>Некорректное время</p>", status_code=400)
    payload = urllib.parse.quote(f"{t}|{name}")
    shortcut_url = f"shortcuts://run-shortcut?name=LifeOS-Alarm&input={payload}"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<meta http-equiv='refresh' content='0;url={shortcut_url}'>"
        "</head><body style='font-family:sans-serif;text-align:center;padding-top:40px'>"
        f"<p>Открываю Shortcuts для будильника на {t}...</p>"
        f"<p><a href='{shortcut_url}'>Нажми, если не открылось само</a></p>"
        "</body></html>"
    )


@router.get("/api/health")
def api_health():
    return {
        "ok": True,
        "db": str(database.DB_PATH),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
        "webapp_url_configured": bool(WEBAPP_URL),
        "embedded_workers": ENABLE_EMBEDDED_WORKERS,
    }
