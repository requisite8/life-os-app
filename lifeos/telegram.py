"""Отправка сообщений через Telegram Bot API."""

from typing import Any
import json
import sqlite3
import urllib.error
import urllib.request

from .config import TG_API, logger
from .database import db


def user_chat_id(con: sqlite3.Connection, user_id: int) -> int | None:
    row = con.execute("SELECT chat_id FROM users WHERE id=?", (user_id,)).fetchone()
    return int(row["chat_id"]) if row and row["chat_id"] else None


def tg_request(method: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not TG_API:
        return None
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{TG_API}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        logger.warning("telegram %s failed: %s", method, e)
        return None


def send_tg(chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    tg_request("sendMessage", payload)


def send_focus_finished(user_id: int, duration: float, category: str | None) -> None:
    with db() as con:
        chat_id = user_chat_id(con, user_id)
    if not chat_id:
        return
    cat = category or "Фокус"
    send_tg(chat_id, f"Фокус-сессия завершена: {int(duration)} мин.\nКатегория: {cat}")
