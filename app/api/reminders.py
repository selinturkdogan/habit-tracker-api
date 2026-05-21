import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.mongo import get_mongo
from app.db.postgres import get_session
from app.models import User
from app.schemas.reminder import ReminderIn, ReminderOut, ReminderUpdate
from app.services.habit_service import get_owned_habit

router = APIRouter(prefix="/habits", tags=["reminders"])


def _doc_to_out(doc: dict) -> ReminderOut:
    return ReminderOut(
        habit_id=doc["habit_id"],
        times=doc.get("times", []),
        message=doc.get("message", ""),
        enabled=doc.get("enabled", True),
        updated_at=doc["updated_at"],
    )


@router.get("/{habit_id}/reminder", response_model=ReminderOut)
async def get_reminder(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await get_owned_habit(session, habit_id, current.id)
    db = get_mongo()
    doc = await db.reminders.find_one({"habit_id": str(habit_id)})
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not configured")
    return _doc_to_out(doc)


@router.post("/{habit_id}/reminder", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def set_reminder(
    habit_id: uuid.UUID,
    data: ReminderIn,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await get_owned_habit(session, habit_id, current.id)
    db = get_mongo()
    now = datetime.now(timezone.utc)
    doc = {
        "habit_id": str(habit_id),
        "user_id": str(current.id),
        "times": data.times,
        "message": data.message,
        "enabled": data.enabled,
        "updated_at": now,
    }
    await db.reminders.replace_one({"habit_id": str(habit_id)}, doc, upsert=True)
    return _doc_to_out(doc)


@router.patch("/{habit_id}/reminder", response_model=ReminderOut)
async def update_reminder(
    habit_id: uuid.UUID,
    data: ReminderUpdate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await get_owned_habit(session, habit_id, current.id)
    db = get_mongo()
    existing = await db.reminders.find_one({"habit_id": str(habit_id)})
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not configured")
    patch = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if not patch:
        return _doc_to_out(existing)
    patch["updated_at"] = datetime.now(timezone.utc)
    await db.reminders.update_one({"habit_id": str(habit_id)}, {"$set": patch})
    updated = await db.reminders.find_one({"habit_id": str(habit_id)})
    assert updated is not None
    return _doc_to_out(updated)


@router.delete("/{habit_id}/reminder", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await get_owned_habit(session, habit_id, current.id)
    db = get_mongo()
    await db.reminders.delete_one({"habit_id": str(habit_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
