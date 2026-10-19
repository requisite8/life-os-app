"""Клавиатуры бота."""

from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import WebAppInfo

from .config import WEBAPP_URL

HEALTH_BUTTON = "🩺 Health OS"
FOCUS_BUTTON = "🎯 Фокус"


def _base_url() -> str:
    return (WEBAPP_URL or "https://requisite.hopto.org").rstrip("/")


def main_keyboard() -> ReplyKeyboardMarkup:
    # Приложения открываются через inline-кнопку с web_app (см. open_app_keyboard):
    # мини-апп, запущенный кнопкой обычной клавиатуры, не получает данные пользователя Telegram.
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text=HEALTH_BUTTON)],
            [KeyboardButton(text=FOCUS_BUTTON)],
        ],
        resize_keyboard=True,
    )


def open_app_keyboard(title: str, path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=title, web_app=WebAppInfo(url=f"{_base_url()}{path}"))
    ]])


kb = main_keyboard()
