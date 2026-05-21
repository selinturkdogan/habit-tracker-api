import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.models import Habit, User
from app.schemas.habit import StreakOut
from app.services.habit_service import get_or_create_streak, get_owned_habit
from app.services.streak_service import compute_streak_at_risk, maybe_reset_weekly_token
from app.services.time_utils import local_date_for

router = APIRouter(tags=["streaks"])


@router.get("/habits/{habit_id}/streak", response_model=StreakOut)
async def get_streak(
    habit_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    habit = await get_owned_habit(session, habit_id, current.id)
    streak = await get_or_create_streak(session, habit.id, current.id)
    today = local_date_for(current.timezone)
    maybe_reset_weekly_token(streak, today)
    await session.commit()
    return StreakOut(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_completed_date=streak.last_completed_date,
        freeze_tokens=streak.freeze_tokens,
        streak_at_risk=compute_streak_at_risk(habit, streak, current.timezone),
    )


@router.get("/streaks/summary", response_model=list[dict])
async def summary(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(Habit).where(Habit.user_id == current.id, Habit.is_active.is_(True))
        )
    ).scalars().all()
    today = local_date_for(current.timezone)
    out: list[dict] = []
    for h in rows:
        streak = await get_or_create_streak(session, h.id, current.id)
        maybe_reset_weekly_token(streak, today)
        out.append(
            {
                "habit_id": str(h.id),
                "title": h.title,
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
                "last_completed_date": streak.last_completed_date.isoformat()
                if streak.last_completed_date
                else None,
                "freeze_tokens": streak.freeze_tokens,
                "streak_at_risk": compute_streak_at_risk(h, streak, current.timezone),
            }
        )
    await session.commit()
    return out
