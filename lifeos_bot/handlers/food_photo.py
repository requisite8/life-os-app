"""Фото еды: оценка калорий через ИИ."""

import base64

from aiogram import F
from aiogram import Router
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message

from ..ai_client import call_openai_vision, parse_ai_reply
from ..alarms import create_pending_action
from ..config import OPENAI_API_KEY
from ..database import db
from ..keyboards import kb
from ..users import ensure_user, notify_admin_new_user


router = Router()


@router.message(F.photo)
async def handle_food_photo(message: Message):
    user = message.from_user
    uid, is_new = ensure_user(user.id, user.first_name or "Пользователь", user.username, message.chat.id)
    if is_new:
        await notify_admin_new_user(message.bot, user)

    if not OPENAI_API_KEY:
        await message.answer("Распознавание фото недоступно: не настроен OPENAI_API_KEY.", reply_markup=kb)
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file_info.file_path)
    image_b64 = base64.b64encode(file_bytes.read()).decode()

    try:
        reply = await call_openai_vision(image_b64)
    except Exception:
        await message.answer("Не удалось распознать фото. Попробуй позже.", reply_markup=kb)
        return

    _, _, _, _, ai_meals, _ = parse_ai_reply(reply)

    if not ai_meals:
        await message.answer("Не смог распознать еду на фото. Опиши текстом, что это было?", reply_markup=kb)
        return

    with db() as con:
        token = create_pending_action(
            con, uid, "ai_save", {"tasks": [], "habits": [], "done": [], "meals": ai_meals, "workouts": []}
        )

    meal = ai_meals[0]
    text = (
        f"🍽 Похоже на: {meal.get('description', 'еда')}\n"
        f"≈ {meal.get('calories', 0)} ккал · Б {meal.get('protein', 0)} Ж {meal.get('fat', 0)} У {meal.get('carbs', 0)}\n\n"
        "Записать?"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✓ Сохранить", callback_data=f"ai_save_yes:{token}"),
        InlineKeyboardButton(text="✕ Отклонить", callback_data=f"ai_save_no:{token}"),
    ]])
    await message.answer(text, reply_markup=keyboard)
