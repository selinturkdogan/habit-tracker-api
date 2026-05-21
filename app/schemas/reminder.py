import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ReminderIn(BaseModel):
    times: list[str] = Field(min_length=1, max_length=5)
    message: str = Field(default="", max_length=140)
    enabled: bool = True

    @field_validator("times")
    @classmethod
    def validate_times(cls, v: list[str]) -> list[str]:
        for t in v:
            if not TIME_RE.match(t):
                raise ValueError(f"Invalid time '{t}', expected HH:MM 24h")
        return sorted(set(v))


class ReminderUpdate(BaseModel):
    times: list[str] | None = Field(default=None, max_length=5)
    message: str | None = Field(default=None, max_length=140)
    enabled: bool | None = None

    @field_validator("times")
    @classmethod
    def validate_times(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        for t in v:
            if not TIME_RE.match(t):
                raise ValueError(f"Invalid time '{t}', expected HH:MM 24h")
        return sorted(set(v))


class ReminderOut(BaseModel):
    habit_id: str
    times: list[str]
    message: str
    enabled: bool
    updated_at: datetime
