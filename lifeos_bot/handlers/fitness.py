"""Опрос о цели и уровне подготовки."""

from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from ..database import db


router = Router()


@router.callback_query(F.data.startswith("fitgoal:"))
async def cb_fitgoal(callback: CallbackQuery):
    code = callback.data.split(":", 1)[1]
    labels = {"loss": "похудение", "gain": "набор массы", "maintain": "поддержание формы"}
    label = labels.get(code, code)
    with db() as con:
        con.execute(
            "UPDATE users SET fitness_goal=? WHERE telegram_id=?", (label, callback.from_user.id)
        )
    await callback.message.edit_text(f"Цель: {label} ✅")
    await callback.message.answer(
        "И какой у тебя уровень подготовки?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Новичок", callback_data="fitlevel:beginner"),
            InlineKeyboardButton(text="Средний", callback_data="fitlevel:medium"),
            InlineKeyboardButton(text="Продвинутый", callback_data="fitlevel:advanced"),
        ]]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fitlevel:"))
async def cb_fitlevel(callback: CallbackQuery):
    code = callback.data.split(":", 1)[1]
    labels = {"beginner": "новичок", "medium": "средний", "advanced": "продвинутый"}
    label = labels.get(code, code)
    with db() as con:
        con.execute(
            "UPDATE users SET fitness_level=? WHERE telegram_id=?", (label, callback.from_user.id)
        )
    await callback.message.edit_text(
        f"Уровень: {label} ✅\nТеперь буду учитывать это в советах по тренировкам и питанию."
    )
    await callback.answer()
