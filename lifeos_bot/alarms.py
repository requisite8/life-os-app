"""Будильники: отложенные действия и предложение (временно выключено)."""

import json
import secrets
import sqlite3
import urllib.parse

from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from .config import WEBAPP_URL, WEEKDAY_NAMES
from .schedule import now_msk


def create_pending_action(con: sqlite3.Connection, user_id: int, kind: str, payload: dict) -> str:
    token = secrets.token_urlsafe(8)
    con.execute(
        "INSERT INTO pending_actions(token, user_id, kind, payload) VALUES(?,?,?,?)",
        (token, user_id, kind, json.dumps(payload, ensure_ascii=False)),
    )
    return token


def build_alarm_offer(icon: str, title: str, time_str: str) -> tuple[str, InlineKeyboardMarkup]:
    weekday = WEEKDAY_NAMES[now_msk().weekday()]
    alarm_label = f"Life OS: {title} ({weekday} {time_str})"
    base_url = WEBAPP_URL or "https://requisite.hopto.org"
    link = f"{base_url}/alarm-redirect?t={time_str}&name={urllib.parse.quote(alarm_label)}"
    text = f"⏰ Поставить будильник?\n\n{icon} {title} — {time_str}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Создать будильник", url=link)]])
    return text, keyboard
