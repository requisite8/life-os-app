"""Команда /alarm и выбор «предлагать ли будильники»."""

import json

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message

from ..alarms import build_alarm_offer
from ..config import ALARM_ENABLED, WEBAPP_URL
from ..database import db


router = Router()


@router.message(Command("alarm"))
async def cmd_alarm(message: Message):
    if not ALARM_ENABLED:
        await message.answer("Функция будильника временно отключена.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Укажи время: /alarm 07:00")
        return

    time_str = parts[1].strip()

    try:
        h, m = time_str.split(":")
        h, m = int(h), int(m)
        assert 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        await message.answer("Неверный формат. Пример: /alarm 07:00")
        return

    time_str = f"{h:02d}:{m:02d}"
    base_url = WEBAPP_URL or "https://requisite.hopto.org"
    link = f"{base_url}/alarm-redirect?t={time_str}"

    await message.answer(
        f"⏰ Будильник на {time_str}\n\nНажми кнопку — откроется Shortcuts:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⏰ Создать будильник", url=link)
        ]])
    )


@router.callback_query(F.data.startswith("alarm_optin_yes:") | F.data.startswith("alarm_optin_no:"))
async def cb_alarm_optin(callback: CallbackQuery):
    is_yes = callback.data.startswith("alarm_optin_yes:")
    token = callback.data.split(":", 1)[1]
    with db() as con:
        row = con.execute(
            "SELECT user_id, payload FROM pending_actions WHERE token=? AND kind='alarm_optin'",
            (token,),
        ).fetchone()
        if row:
            con.execute("DELETE FROM pending_actions WHERE token=?", (token,))
            con.execute(
                "UPDATE users SET alarm_optin=? WHERE id=?",
                (1 if is_yes else 0, row["user_id"]),
            )

    if not row:
        await callback.answer("Уже неактуально")
        return

    if is_yes:
        info = json.loads(row["payload"])
        await callback.message.edit_text("Хорошо, буду предлагать будильник 👍")
        text, keyboard = build_alarm_offer(info["icon"], info["title"], info["time"])
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text("Хорошо, не буду предлагать будильник.")

    await callback.answer()
