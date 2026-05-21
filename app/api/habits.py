import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.db.redis import get_redis
from app.models import Habit, Streak, User
from app.schemas.habit import HabitCreate, HabitOut, HabitUpdate, HabitWithStreakOut, StreakOut
from app.services.habit_service import get_or_create_streak, get_owned_habit
from app.services.streak_service import compute_streak_at_risk, maybe_reset_weekly_token
from app.services.time_utils import local_date_for

router = APIRouter(prefix="/habits", tags=["habits"])


async def _bust_dashboard_cache(user_id) -> None:
    """Delete any cached dashboard entries for this user (all dates)."""
    redis = get_redis()
    pattern = f"dashboard:{user_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)


def _ensure_custom_days(frequency: str, custom_days: list[int] | None) -> None:
    if frequency == "custom" and not custom_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="custom_days is required when frequency is 'custom'",
        )


def _streak_out(habit: Habit, streak: Streak, tz: str) -> StreakOut:
    return StreakOut(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_completed_date=streak.last_completed_date,
        freeze_tokens=streak.freeze_tokens,
        streak_at_risk=compute_streak_at_risk(habit, streak, tz),
    )


@router.get("", response_model=list[HabitWithStreakOut])
async def list_habits(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(Habit)
            .where(Habit.user_id == current.id, Habit.is_active.is_(True))
            .order_by(Habit.created_at.desc())
        )
    ).scalars().all()
    today = local_date_for(current.timezone)
    result: list[HabitWithStreakOut] = []
    for h in rows:
        streak = await get_or_create_streak(session, h.id, current.id)
        maybe_reset_weekly_token(streak, today)
        result.append(
            HabitWithStreakOut(
                **HabitOut.model_validate(h).model_dump(),
                streak=_streak_out(h, streak, current.timezone),
            )
        )
    await session.commit()
    return result


@router.post("", response_model=HabitOut, status_code=status.HTTP_201_CREATED)
async def create_habit(
    data: HabitCreate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _ensure_custom_days(data.frequency, data.custom_days)
    habit = Habit(
        user_id=current.id,
        title=data.title,
        description=data.description,
        frequency=data.frequency,
        custom_days=data.custom_days,
    )
    session.add(habit)
    await session.flush()
    session.add(Streak(habit_id=habit.id, user_id=current.id))
    await session.commit()
    await session.refresh(habit)
    await _bust_dashboard_cache(current.id)
    return habit


@router.get("/{habit_id}", response_model=HabitWithStreakOut)
async def get_habit(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    habit = await get_owned_habit(session, habit_id, current.id)
    streak = await get_or_create_streak(session, habit.id, current.id)
    today = local_date_for(current.timezone)
    maybe_reset_weekly_token(streak, today)
    await session.commit()
    return HabitWithStreakOut(
        **HabitOut.model_validate(habit).model_dump(),
        streak=_streak_out(habit, streak, current.timezone),
    )


@router.patch("/{habit_id}", response_model=HabitOut)
async def update_habit(
    habit_id: uuid.UUID,
    data: HabitUpdate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    habit = await get_owned_habit(session, habit_id, current.id)
    patch = data.model_dump(exclude_unset=True)
    new_freq = patch.get("frequency", habit.frequency)
    new_custom = patch.get("custom_days", habit.custom_days)
    _ensure_custom_days(new_freq, new_custom)
    for k, v in patch.items():
        setattr(habit, k, v)
    await session.commit()
    await session.refresh(habit)
    await _bust_dashboard_cache(current.id)
    return habit


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    habit = await get_owned_habit(session, habit_id, current.id)
    habit.is_active = False
    await session.commit()
    await _bust_dashboard_cache(current.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
