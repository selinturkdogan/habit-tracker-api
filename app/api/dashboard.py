import json
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.db.redis import get_redis
from app.models import CheckIn, Habit, User
from app.schemas.dashboard import DashboardItem, DashboardOut
from app.schemas.habit import HabitOut, StreakOut
from app.services.habit_service import get_or_create_streak
from app.services.streak_service import compute_streak_at_risk, maybe_reset_weekly_token
from app.services.time_utils import is_scheduled_on, local_date_for

CACHE_TTL_SECONDS = 5 * 60


def _cache_key(user_id, today: date) -> str:
    return f"dashboard:{user_id}:{today.isoformat()}"


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    today = local_date_for(current.timezone)
    redis = get_redis()
    key = _cache_key(current.id, today)
    cached = await redis.get(key)
    if cached:
        # Pydantic will re-validate the cached payload to ensure shape stability.
        return DashboardOut.model_validate(json.loads(cached))

    habits = (
        await session.execute(
            select(Habit).where(Habit.user_id == current.id, Habit.is_active.is_(True))
        )
    ).scalars().all()

    scheduled = [h for h in habits if is_scheduled_on(h.frequency, h.custom_days, today)]
    items: list[DashboardItem] = []
    for h in scheduled:
        streak = await get_or_create_streak(session, h.id, current.id)
        maybe_reset_weekly_token(streak, today)
        ci = (
            await session.execute(
                select(CheckIn).where(CheckIn.habit_id == h.id, CheckIn.checked_date == today)
            )
        ).scalar_one_or_none()
        items.append(
            DashboardItem(
                habit=HabitOut.model_validate(h),
                streak=StreakOut(
                    current_streak=streak.current_streak,
                    longest_streak=streak.longest_streak,
                    last_completed_date=streak.last_completed_date,
                    freeze_tokens=streak.freeze_tokens,
                    streak_at_risk=compute_streak_at_risk(h, streak, current.timezone),
                ),
                checked_today=ci is not None,
            )
        )
    await session.commit()

    done = sum(1 for x in items if x.checked_today)
    rate = (done / len(items)) if items else 0.0
    payload = DashboardOut(date=today, completion_rate=rate, habits_today=items)
    await redis.setex(key, CACHE_TTL_SECONDS, payload.model_dump_json())
    return payload
