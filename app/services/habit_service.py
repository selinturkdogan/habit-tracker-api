import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Habit, Streak


async def get_owned_habit(session: AsyncSession, habit_id: uuid.UUID, user_id: uuid.UUID) -> Habit:
    habit = (await session.execute(select(Habit).where(Habit.id == habit_id))).scalar_one_or_none()
    if habit is None or not habit.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    if habit.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't own this habit")
    return habit


async def get_or_create_streak(session: AsyncSession, habit_id: uuid.UUID, user_id: uuid.UUID) -> Streak:
    streak = (
        await session.execute(select(Streak).where(Streak.habit_id == habit_id))
    ).scalar_one_or_none()
    if streak is None:
        streak = Streak(habit_id=habit_id, user_id=user_id)
        session.add(streak)
        await session.flush()
    return streak
