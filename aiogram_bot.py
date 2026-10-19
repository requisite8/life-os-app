"""Точка входа Telegram-бота Life OS. Запуск: python aiogram_bot.py"""

import asyncio

from aiogram import Bot, Dispatcher

from lifeos_bot.config import BOT_TOKEN
from lifeos_bot.database import db, ensure_alarm_tables
from lifeos_bot.handlers import ai_chat, alarm, commands, fitness, food_photo
from lifeos_bot.reminders import reminder_loop


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")

    with db() as con:
        ensure_alarm_tables(con)

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    # Порядок важен: свободный текст (ai_chat) должен идти последним, он ловит всё остальное.
    for module in (commands, alarm, food_photo, fitness, ai_chat):
        dp.include_router(module.router)

    reminder_task = asyncio.create_task(reminder_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
