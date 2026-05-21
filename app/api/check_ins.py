import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.db.redis import get_redis
from app.models import CheckIn, User
from app.schemas.check_in import CheckInOut
from app.services.habit_service import get_or_create_streak, get_owned_habit
from app.services.streak_service import apply_check_in, use_freeze_now
from app.services.time_utils import local_date_for

router = APIRouter(prefix="/habits", tags=["check-ins"])


@router.post("/{habit_id}/checkin", response_model=CheckInOut, status_code=status.HTTP_201_CREATED)
async def check_in(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    habit = await get_owned_habit(session, habit_id, current.id)
    today = local_date_for(current.timezone)

    existing = (
        await session.execute(
            select(CheckIn).where(CheckIn.habit_id == habit.id, CheckIn.checked_date == today)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already checked in today for this habit",
        )

    ci = CheckIn(habit_id=habit.id, user_id=current.id, checked_date=today)
    session.add(ci)
    streak = await get_or_create_streak(session, habit.id, current.id)
    await apply_check_in(session, habit, streak, today)
    await session.commit()
    await session.refresh(ci)
    # Invalidate dashboard cache so next GET reflects the new check-in
    redis = get_redis()
    async for key in redis.scan_iter(f"dashboard:{current.id}:*"):
        await redis.delete(key)
    return ci


@router.get("/{habit_id}/checkins", response_model=list[CheckInOut])
async def list_check_ins(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    habit = await get_owned_habit(session, habit_id, current.id)
    rows = (
        await session.execute(
            select(CheckIn)
            .where(CheckIn.habit_id == habit.id)
            .order_by(CheckIn.checked_date.desc())
        )
    ).scalars().all()
    return rows


@router.post("/{habit_id}/freeze", response_model=dict)
async def use_freeze(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    habit = await get_owned_habit(session, habit_id, current.id)
    streak = await get_or_create_streak(session, habit.id, current.id)
    today = local_date_for(current.timezone)
    await use_freeze_now(session, habit, streak, today)
    await session.commit()
    return {
        "freeze_tokens": streak.freeze_tokens,
        "current_streak": streak.current_streak,
    }
