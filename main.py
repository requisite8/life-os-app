"""Точка входа Life OS: собирает FastAPI-приложение из модулей пакета lifeos.

Запуск: uvicorn main:app
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from lifeos import database, workers
from lifeos.config import ENABLE_EMBEDDED_WORKERS, STATIC_DIR
from lifeos.routers import ai_chat, focus, habits, health, pages, tasks, users

app = FastAPI(title="Life OS API")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/health", StaticFiles(directory=str(STATIC_DIR / "health"), html=True), name="health")

for module in (pages, users, health, focus, habits, tasks, ai_chat):
    app.include_router(module.router)


@app.on_event("startup")
async def on_startup() -> None:
    database.configure_db_path()
    database.init_db()
    if ENABLE_EMBEDDED_WORKERS:
        workers.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await workers.stop()
