"""Предложение будильников для привычек (временно выключено)."""

from typing import Any
import json
import secrets
import sqlite3
import urllib.parse

from .config import ALARM_ENABLED, WEBAPP_URL, WEEKDAY_NAMES
from .database import db
from .telegram import send_tg, user_chat_id
from .timeutil import now_msk


def create_pending_action(con: sqlite3.Connection, user_id: int, kind: str, payload: dict[str, Any]) -> str:
    token = secrets.token_urlsafe(8)
    con.execute(
        "INSERT INTO pending_actions(token, user_id, kind, payload) VALUES(?,?,?,?)",
        (token, user_id, kind, json.dumps(payload, ensure_ascii=False)),
    )
    return token


def build_alarm_offer(icon: str, title: str, time_str: str) -> tuple[str, dict[str, Any]]:
    weekday = WEEKDAY_NAMES[now_msk().weekday()]
    alarm_label = f"Life OS: {title} ({weekday} {time_str})"
    link = f"{WEBAPP_URL or 'https://requisite.hopto.org'}/alarm-redirect?t={time_str}&name={urllib.parse.quote(alarm_label)}"
    text = f"⏰ Поставить будильник?\n\n{icon} {title} — {time_str}"
    keyboard = {"inline_keyboard": [[{"text": "Создать будильник", "url": link}]]}
    return text, keyboard


def offer_alarm(user_id: int, icon: str, title: str, time_str: str) -> None:
    if not ALARM_ENABLED or not time_str:
        return
    with db() as con:
        chat_id = user_chat_id(con, user_id)
        if not chat_id:
            return
        row = con.execute("SELECT alarm_optin FROM users WHERE id=?", (user_id,)).fetchone()
        optin = row["alarm_optin"] if row else None
        if optin == 0:
            return
        if optin is None:
            con.execute("UPDATE users SET alarm_optin=0 WHERE id=?", (user_id,))
            token = create_pending_action(
                con, user_id, "alarm_optin", {"icon": icon, "title": title, "time": time_str}
            )
            text = (
                "⏰ Хочешь, чтобы я предлагал ставить будильник на привычки с напоминанием?\n\n"
                f"Например сейчас: {icon} {title} — {time_str}"
            )
            keyboard = {
                "inline_keyboard": [[
                    {"text": "Да, предлагай", "callback_data": f"alarm_optin_yes:{token}"},
                    {"text": "Нет", "callback_data": f"alarm_optin_no:{token}"},
                ]]
            }
            send_tg(chat_id, text, reply_markup=keyboard)
            return

    text, keyboard = build_alarm_offer(icon, title, time_str)
    send_tg(chat_id, text, reply_markup=keyboard)
