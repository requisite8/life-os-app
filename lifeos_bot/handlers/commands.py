"""Команды и кнопки: /start, /help, /tasks, /habits, /steps, /stepsetup."""

import secrets

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import STEPS_SHORTCUT_URL, WEBAPP_URL
from ..database import db
from ..keyboards import FOCUS_BUTTON, HEALTH_BUTTON, kb, open_app_keyboard
from ..queries import list_habits, list_tasks
from ..schedule import now_msk
from ..users import ensure_user, notify_admin_new_user


router = Router()


@router.message(Command("health"))
@router.message(F.text == HEALTH_BUTTON)
async def open_health_app(message: Message):
    await message.answer("Открыть Health OS:", reply_markup=open_app_keyboard("🩺 Открыть Health OS", "/health/"))


@router.message(Command("focus"))
@router.message(F.text == FOCUS_BUTTON)
async def open_focus_app(message: Message):
    await message.answer("Открыть Фокус:", reply_markup=open_app_keyboard("🎯 Открыть Фокус", "/"))


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    _, is_new = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
    if is_new:
        await notify_admin_new_user(message.bot, user)
    name = user.first_name or "друг"
    text = (
        f"Привет, {name}! 👋 Я — Life OS.\n"
        "Помогаю держать в порядке фокус, задачи и привычки.\n\n"
        "🎯 Фокус-таймер — трекай рабочие сессии\n"
        "📋 Задачи — с напоминанием за час до дедлайна\n"
        "✅ Привычки — с ежедневным временем напоминания\n\n"
        "💬 Можешь просто написать мне текстом, что планируешь — сам разберу и предложу добавить в трекер.\n\n"
        "Открой мини-приложение кнопкой меню слева от поля ввода 👇\n\n"
        "Команды: /tasks /habits /help"
    )
    await message.answer(text, reply_markup=kb)


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Вот что я умею:\n\n"
        "/tasks — список активных задач\n"
        "/habits — список привычек\n"
        "/stepsetup — автоматические шаги с iPhone через Команды\n\n"
        "А ещё можно просто написать мне обычным сообщением — расскажи, что сделал или что планируешь, "
        "и я предложу добавить задачу/привычку или отмечу выполненное."
    )
    await message.answer(text, reply_markup=kb)


@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    user = message.from_user
    uid, is_new = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
    if is_new:
        await notify_admin_new_user(message.bot, user)
    await message.answer(list_tasks(uid), reply_markup=kb)


@router.message(Command("habits"))
async def cmd_habits(message: Message):
    user = message.from_user
    uid, is_new = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
    if is_new:
        await notify_admin_new_user(message.bot, user)
    await message.answer(list_habits(uid), reply_markup=kb)


@router.message(Command("stepsetup"))
async def cmd_stepsetup(message: Message):
    user = message.from_user
    uid, is_new = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
    if is_new:
        await notify_admin_new_user(message.bot, user)
    with db() as con:
        row = con.execute("SELECT steps_token FROM users WHERE id=?", (uid,)).fetchone()
        token = row["steps_token"] if row and row["steps_token"] else None
        if not token:
            token = secrets.token_urlsafe(18)
            con.execute("UPDATE users SET steps_token=? WHERE id=?", (token, uid))
    automation = (
        "Автоматизация, чтобы шаги обновлялись сами:\n"
        "«Команды» → «Автоматизация» → «+» → «Приложение» → Telegram → «Открыто» → "
        "«Выполнять сразу» → действие «Выполнить команду» → Life OS Steps.\n"
        "Теперь шаги отправляются каждый раз, когда ты открываешь Telegram. "
        "Если хочешь ещё и по времени — добавь вторую автоматизацию «Время суток» (например, 22:00) с той же командой."
    )

    if STEPS_SHORTCUT_URL:
        await message.answer(
            "👣 Автоматические шаги (iPhone)\n\n"
            f"1. Открой ссылку и нажми «Добавить команду»:\n{STEPS_SHORTCUT_URL}\n"
            "2. Когда команда спросит токен — вставь токен из следующего сообщения. "
            "При первом запуске разреши доступ к «Шагам».\n"
            "3. " + automation + "\n\n"
            "Android пока не поддерживаю — там вручную: /steps 8432",
            reply_markup=kb,
        )
        await message.answer(
            f"Твой личный токен (никому не показывай, нажми, чтобы скопировать):\n<code>{token}</code>",
            parse_mode="HTML",
        )
        return

    base_url = (WEBAPP_URL or "https://requisite.hopto.org").rstrip("/")
    link = f"{base_url}/api/health/steps-hook?token={token}&steps="
    await message.answer(
        "👣 Автоматические шаги (iPhone)\n\n"
        "Создай в «Командах» команду «Life OS Steps» из трёх действий:\n"
        "1. «Найти образцы здоровья»: тип — Шаги, дата начала — сегодня. "
        "При первом запуске разреши доступ к «Шагам».\n"
        "2. «Вычислить статистику» → Сумма.\n"
        "3. «Получить содержимое URL» — вставь ссылку из следующего сообщения, а после «steps=» подставь результат шага 2.\n\n"
        + automation + "\n\n"
        "Android пока не поддерживаю — там вручную: /steps 8432",
        reply_markup=kb,
    )
    await message.answer(f"Твоя личная ссылка (никому не показывай):\n{link}")


@router.message(Command("steps"))
async def cmd_steps(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Укажи число шагов: /steps 8432")
        return
    try:
        steps = int(parts[1])
        assert steps >= 0
    except Exception:
        await message.answer("Нужно целое число шагов, например: /steps 8432")
        return

    user = message.from_user
    uid, is_new = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
    if is_new:
        await notify_admin_new_user(message.bot, user)

    today = now_msk().date().isoformat()
    with db() as con:
        con.execute(
            """
            INSERT INTO health_steps(user_id, date, steps, updated_at) VALUES(?,?,?,?)
            ON CONFLICT(user_id, date) DO UPDATE SET steps=excluded.steps, updated_at=excluded.updated_at
            """,
            (uid, today, steps, now_msk().isoformat()),
        )
    await message.answer(f"Записал: {steps} шагов за сегодня ✅")


@router.message(F.text == "📋 Мои задачи")
async def btn_tasks(message: Message):
    await cmd_tasks(message)


@router.message(F.text == "✅ Мои привычки")
async def btn_habits(message: Message):
    await cmd_habits(message)


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message):
    await cmd_help(message)
