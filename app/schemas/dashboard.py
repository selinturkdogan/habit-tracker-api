from datetime import date

from pydantic import BaseModel

from app.schemas.habit import HabitOut, StreakOut


class DashboardItem(BaseModel):
    habit: HabitOut
    streak: StreakOut
    checked_today: bool


class DashboardOut(BaseModel):
    date: date
    completion_rate: float
    habits_today: list[DashboardItem]
