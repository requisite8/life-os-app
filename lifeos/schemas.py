"""Pydantic-модели запросов API."""

from typing import Any

from pydantic import BaseModel


class UserCreate(BaseModel):
    telegram_id: int | None = None
    first_name: str = "Пользователь"
    username: str | None = None


class UserSettingsPatch(BaseModel):
    alarm_optin: bool


class StepsSet(BaseModel):
    user_id: int
    steps: int


class WaterSet(BaseModel):
    user_id: int
    ml: int


class SleepSet(BaseModel):
    user_id: int
    hours: float
    bedtime: str | None = None
    waketime: str | None = None
    quality: str | None = None


class NutritionSet(BaseModel):
    user_id: int
    calories: int
    protein: int = 0
    fat: int = 0
    carbs: int = 0


class MealCreate(BaseModel):
    user_id: int
    description: str = "Приём пищи"
    calories: int
    protein: int = 0
    fat: int = 0
    carbs: int = 0
    source: str = "manual"


class WorkoutCreate(BaseModel):
    user_id: int
    type: str = "Тренировка"
    description: str = ""
    duration_min: int = 0
    calories: int = 0
    source: str = "manual"


class HealthProfilePatch(BaseModel):
    fitness_goal: str | None = None
    fitness_level: str | None = None


class FocusCreate(BaseModel):
    user_id: int
    duration_min: float
    category: str | None = None


class HabitCreate(BaseModel):
    user_id: int
    name: str
    icon: str = "✅"
    frequency: str = "Каждый день"
    reminder_time: str | None = None
    weekdays: list[int] | None = None


class HabitUpdate(BaseModel):
    name: str
    icon: str = "✅"
    frequency: str = "Каждый день"
    reminder_time: str | None = None
    weekdays: list[int] | None = None


class HabitToggle(BaseModel):
    habit_id: int
    user_id: int
    date: str


class TaskCreate(BaseModel):
    user_id: int
    name: str
    section: str = "work"
    priority: str = "mid"
    deadline: str | None = None
    from_ai: bool = False


class TaskPatch(BaseModel):
    done: bool


class AIChatRequest(BaseModel):
    user_id: int
    message: str
    history: list[dict[str, Any]] | None = None
