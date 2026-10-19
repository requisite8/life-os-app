"""Маршруты API: pages."""

import re
import urllib.parse

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .. import database
from ..config import ENABLE_EMBEDDED_WORKERS, STATIC_DIR, TELEGRAM_BOT_TOKEN, WEBAPP_URL


router = APIRouter()

NO_CACHE = {"Cache-Control": "no-cache"}
_ASSET_RE = re.compile(r'(?P<attr>(?:src|href)=")(?P<url>[^":?#]+\.(?:css|js|png|jpg|jpeg|webp|svg))(?P<end>")')


def add_asset_versions(html: str, base_dir) -> str:
    """Дописывает ?v=<время правки файла> к локальным css/js/картинкам в HTML,
    чтобы Telegram и браузеры не показывали устаревшие копии."""

    def repl(m):
        path = base_dir / m.group("url")
        if not path.is_file():
            return m.group(0)
        return f'{m.group("attr")}{m.group("url")}?v={int(path.stat().st_mtime)}{m.group("end")}'

    return _ASSET_RE.sub(repl, html)


@router.get("/", response_class=HTMLResponse)
def read_root():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"), headers=NO_CACHE)


@router.get("/health/", response_class=HTMLResponse)
def read_health_app():
    health_dir = STATIC_DIR / "health"
    html = (health_dir / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(add_asset_versions(html, health_dir), headers=NO_CACHE)


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
