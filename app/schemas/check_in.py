import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CheckInOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    habit_id: uuid.UUID
    checked_date: date
    checked_at: datetime
