"""Точка входа Life OS: собирает FastAPI-приложение из модулей пакета lifeos.

Запуск: uvicorn main:app
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from lifeos import database, workers
from lifeos.config import ENABLE_EMBEDDED_WORKERS, STATIC_DIR
from lifeos.routers import ai_chat, focus, habits, health, pages, tasks, users

class RevalidatedStaticFiles(StaticFiles):
    """Статика с `Cache-Control: no-cache`: браузер/Telegram каждый раз спрашивает сервер,
    не изменился ли файл (ответ 304 дешёвый), и не показывает устаревшую версию."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app = FastAPI(title="Life OS API")

# Маршруты подключаются раньше статики: страница /health/ отдаётся маршрутом (с версиями файлов),
# а остальное под /health — файлами из static/health.
for module in (pages, users, health, focus, habits, tasks, ai_chat):
    app.include_router(module.router)

app.mount("/static", RevalidatedStaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/health", RevalidatedStaticFiles(directory=str(STATIC_DIR / "health"), html=True), name="health")


@app.on_event("startup")
async def on_startup() -> None:
    database.configure_db_path()
    database.init_db()
    if ENABLE_EMBEDDED_WORKERS:
        workers.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await workers.stop()
