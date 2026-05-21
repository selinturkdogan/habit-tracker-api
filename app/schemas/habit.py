import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Frequency = Literal["daily", "weekdays", "custom"]


class HabitBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    frequency: Frequency
    custom_days: list[int] | None = None

    @field_validator("custom_days")
    @classmethod
    def validate_custom_days(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        for d in v:
            if d < 0 or d > 6:
                raise ValueError("custom_days values must be 0..6 (0=Mon, 6=Sun)")
        return sorted(set(v))


class HabitCreate(HabitBase):
    pass


class HabitUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    frequency: Frequency | None = None
    custom_days: list[int] | None = None
    is_active: bool | None = None

    @field_validator("custom_days")
    @classmethod
    def validate_custom_days(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        for d in v:
            if d < 0 or d > 6:
                raise ValueError("custom_days values must be 0..6 (0=Mon, 6=Sun)")
        return sorted(set(v))


class StreakOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_streak: int
    longest_streak: int
    last_completed_date: date | None
    freeze_tokens: int
    streak_at_risk: bool = False


class HabitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    frequency: Frequency
    custom_days: list[int] | None
    is_active: bool
    created_at: datetime


class HabitWithStreakOut(HabitOut):
    streak: StreakOut
