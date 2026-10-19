"""Свободный диалог с ИИ: задачи, привычки, еда, тренировки."""

import json

from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message

from ..ai_client import call_ai_chat, parse_ai_reply
from ..alarms import build_alarm_offer, create_pending_action
from ..config import ALARM_ENABLED
from ..database import db
from ..keyboards import kb
from ..schedule import now_msk
from ..users import ensure_user, notify_admin_new_user


router = Router()


@router.message(F.text & ~F.text.startswith("/"))
async def free_text_ai(message: Message):
    if message.text in (
        "📋 Мои задачи", "✅ Мои привычки", "❓ Помощь",
    ):
        return  # уже обработано выше по конкретному фильтру

    user = message.from_user
    uid, is_new = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
    if is_new:
        await notify_admin_new_user(message.bot, user)
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        reply = await call_ai_chat(uid, message.text)
    except Exception:
        await message.answer("Не удалось связаться с AI. Попробуй позже.", reply_markup=kb)
        return

    clean, ai_tasks, ai_habits, ai_done, ai_meals, ai_workouts = parse_ai_reply(reply)

    if not ai_tasks and not ai_habits and not ai_done and not ai_meals and not ai_workouts:
        await message.answer(clean or reply or "...", reply_markup=kb)
        return

    with db() as con:
        token = create_pending_action(
            con, uid, "ai_save",
            {"tasks": ai_tasks, "habits": ai_habits, "done": ai_done, "meals": ai_meals, "workouts": ai_workouts},
        )

    summary_parts = []
    if ai_tasks:
        summary_parts.append(f"задач: {len(ai_tasks)}")
    if ai_habits:
        summary_parts.append(f"привычек: {len(ai_habits)}")
    if ai_done:
        summary_parts.append(f"выполнено: {len(ai_done)}")
    if ai_meals:
        summary_parts.append(f"приёмов пищи: {len(ai_meals)}")
    if ai_workouts:
        summary_parts.append(f"тренировок: {len(ai_workouts)}")

    text = (clean + "\n\n" if clean else "") + "Нашёл — " + ", ".join(summary_parts) + ". Сохранить?"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✓ Сохранить", callback_data=f"ai_save_yes:{token}"),
        InlineKeyboardButton(text="✕ Отклонить", callback_data=f"ai_save_no:{token}"),
    ]])
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("ai_save_yes:") | F.data.startswith("ai_save_no:"))
async def cb_ai_save(callback: CallbackQuery):
    is_yes = callback.data.startswith("ai_save_yes:")
    token = callback.data.split(":", 1)[1]

    with db() as con:
        row = con.execute(
            "SELECT user_id, payload FROM pending_actions WHERE token=? AND kind='ai_save'",
            (token,),
        ).fetchone()
        if row:
            con.execute("DELETE FROM pending_actions WHERE token=?", (token,))

    if not row:
        await callback.answer("Уже неактуально")
        return

    if not is_yes:
        await callback.message.edit_text("Отклонено.")
        await callback.answer()
        return

    data = json.loads(row["payload"])
    user_id = row["user_id"]
    saved_tasks = 0
    saved_habits = 0
    marked_done = 0
    alarm_offers: list[tuple[int, str, InlineKeyboardMarkup]] = []
    optin_offers: list[tuple[int, str, InlineKeyboardMarkup]] = []

    with db() as con:
        urow = con.execute(
            "SELECT chat_id, alarm_optin, fitness_goal, fitness_level FROM users WHERE id=?", (user_id,)
        ).fetchone()
        chat_id = urow["chat_id"] if urow else None
        optin = urow["alarm_optin"] if urow else None
        needs_fitness_profile = bool(urow) and not urow["fitness_goal"] and not urow["fitness_level"]

        for t in data.get("tasks", []):
            name = (t.get("name") or "Новая задача").strip()
            con.execute(
                "INSERT INTO tasks(user_id, name, section, priority, deadline, done, done_at, from_ai, created_at, deleted) "
                "VALUES(?,?,?,?,?,0,NULL,1,?,0)",
                (
                    user_id, name, t.get("section") or "work", t.get("priority") or "mid",
                    t.get("deadline"), now_msk().isoformat(),
                ),
            )
            saved_tasks += 1

        for h in data.get("habits", []):
            name = (h.get("name") or "Новая привычка").strip()
            icon = h.get("icon") or "✅"
            weekdays = h.get("weekdays") if isinstance(h.get("weekdays"), list) else []
            con.execute(
                "INSERT INTO habits(user_id, name, icon, frequency, streak, reminder_time, weekdays, created_at) "
                "VALUES(?,?,?,?,0,?,?,?)",
                (
                    user_id, name, icon, h.get("frequency") or "Каждый день",
                    h.get("reminder_time"),
                    json.dumps(weekdays, ensure_ascii=False) if weekdays else None,
                    now_msk().isoformat(),
                ),
            )
            saved_habits += 1

            reminder_time = h.get("reminder_time")
            if ALARM_ENABLED and reminder_time and chat_id:
                if optin == 1:
                    text2, kb2 = build_alarm_offer(icon, name, reminder_time)
                    alarm_offers.append((chat_id, text2, kb2))
                elif optin is None:
                    con.execute("UPDATE users SET alarm_optin=0 WHERE id=?", (user_id,))
                    optin = 0
                    opt_token = create_pending_action(
                        con, user_id, "alarm_optin", {"icon": icon, "title": name, "time": reminder_time}
                    )
                    opt_text = (
                        "⏰ Хочешь, чтобы я предлагал ставить будильник на привычки с напоминанием?\n\n"
                        f"Например сейчас: {icon} {name} — {reminder_time}"
                    )
                    opt_kb = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="Да, предлагай", callback_data=f"alarm_optin_yes:{opt_token}"),
                        InlineKeyboardButton(text="Нет", callback_data=f"alarm_optin_no:{opt_token}"),
                    ]])
                    optin_offers.append((chat_id, opt_text, opt_kb))

        for d in data.get("done", []):
            dname = (d.get("name") or "").strip().lower()
            dtype = d.get("type")
            if not dname:
                continue
            if dtype == "habit":
                hrow = con.execute(
                    "SELECT id FROM habits WHERE user_id=? AND lower(name) LIKE ?",
                    (user_id, f"%{dname}%"),
                ).fetchone()
                if hrow:
                    today = now_msk().date().isoformat()
                    con.execute(
                        "INSERT OR IGNORE INTO habit_logs(habit_id, user_id, date, created_at) VALUES(?,?,?,?)",
                        (hrow["id"], user_id, today, now_msk().isoformat()),
                    )
                    marked_done += 1
            elif dtype == "task":
                trow = con.execute(
                    "SELECT id FROM tasks WHERE user_id=? AND deleted=0 AND done=0 AND lower(name) LIKE ?",
                    (user_id, f"%{dname}%"),
                ).fetchone()
                if trow:
                    con.execute(
                        "UPDATE tasks SET done=1, done_at=? WHERE id=?",
                        (now_msk().isoformat(), trow["id"]),
                    )
                    marked_done += 1

        today = now_msk().date().isoformat()
        saved_meals = 0
        for m in data.get("meals", []):
            con.execute(
                "INSERT INTO health_meals_log(user_id, date, description, calories, protein, fat, carbs, source, created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    user_id, today, (m.get("description") or "Приём пищи").strip(),
                    int(m.get("calories") or 0), int(m.get("protein") or 0),
                    int(m.get("fat") or 0), int(m.get("carbs") or 0),
                    "ai_text", now_msk().isoformat(),
                ),
            )
            saved_meals += 1

        saved_workouts = 0
        for w in data.get("workouts", []):
            con.execute(
                "INSERT INTO health_workouts(user_id, date, type, description, duration_min, calories, source, created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (
                    user_id, today, (w.get("type") or "Тренировка").strip(), (w.get("description") or "").strip(),
                    int(w.get("duration_min") or 0), int(w.get("calories") or 0),
                    "ai_text", now_msk().isoformat(),
                ),
            )
            saved_workouts += 1

    for chat_id, text, keyboard in optin_offers:
        await callback.bot.send_message(chat_id, text, reply_markup=keyboard)
    for chat_id, text, keyboard in alarm_offers:
        await callback.bot.send_message(chat_id, text, reply_markup=keyboard)

    result_parts = []
    if saved_tasks:
        result_parts.append(f"задач сохранено: {saved_tasks}")
    if saved_habits:
        result_parts.append(f"привычек сохранено: {saved_habits}")
    if marked_done:
        result_parts.append(f"отмечено выполненным: {marked_done}")
    if saved_meals:
        result_parts.append(f"приёмов пищи записано: {saved_meals}")
    if saved_workouts:
        result_parts.append(f"тренировок записано: {saved_workouts}")
    await callback.message.edit_text("Готово: " + ", ".join(result_parts) if result_parts else "Готово.")
    await callback.answer()

    if saved_workouts and needs_fitness_profile and chat_id:
        await callback.bot.send_message(
            chat_id,
            "Кстати, чтобы советы по тренировкам были под тебя — какая у тебя цель?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Похудение", callback_data="fitgoal:loss"),
                InlineKeyboardButton(text="Набор массы", callback_data="fitgoal:gain"),
                InlineKeyboardButton(text="Форма", callback_data="fitgoal:maintain"),
            ]]),
        )
