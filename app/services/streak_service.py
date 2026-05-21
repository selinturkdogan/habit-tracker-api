"""Streak engine — current/longest streak, freeze tokens, weekly reset, at-risk flag.

This is the heart of the Phase 1 unique feature. See DECISIONS.md for the design.
"""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FreezeEvent, Habit, Streak
from app.services.time_utils import (
    is_scheduled_on,
    local_now,
    monday_of,
)

AT_RISK_HOUR = 21  # 9 PM local time


def maybe_reset_weekly_token(streak: Streak, today: date) -> None:
    """Lazy weekly reset — grant 1 freeze token if a new Mon-Sun week has begun."""
    this_monday = monday_of(today)
    if streak.last_token_reset_date is None or streak.last_token_reset_date < this_monday:
        streak.freeze_tokens = max(streak.freeze_tokens, 1)
        streak.last_token_reset_date = this_monday


def previous_scheduled_day(habit: Habit, today: date) -> date | None:
    """Walks backwards from yesterday until it finds the most recent day the
    habit was scheduled. Returns None if no scheduled day in the last 30 days."""
    for delta in range(1, 31):
        candidate = today - timedelta(days=delta)
        if is_scheduled_on(habit.frequency, habit.custom_days, candidate):
            return candidate
    return None


async def apply_check_in(session: AsyncSession, habit: Habit, streak: Streak, today: date) -> None:
    """Update streak state after a check-in lands for `today`.

    Logic per DECISIONS.md:
      1. If last_completed_date is today already — no-op (the unique constraint
         already prevented a duplicate insert).
      2. Find the previous scheduled day. If there is a check-in there (i.e.
         last_completed_date matches it) — increment streak.
      3. Otherwise, if freeze tokens are available — consume one, log a
         freeze_event for the missed day, and increment streak.
      4. Otherwise — reset current_streak to 1 (today is a fresh start).
      5. Always update longest_streak if current_streak surpasses it.
    """
    maybe_reset_weekly_token(streak, today)

    if streak.last_completed_date == today:
        return

    prev = previous_scheduled_day(habit, today)
    last = streak.last_completed_date

    if prev is None or last == prev:
        # Continuous: previous scheduled day was satisfied (or this is the first
        # check-in ever and there's no prior schedule)
        streak.current_streak += 1
    elif streak.freeze_tokens > 0 and last is not None and prev is not None and last < prev:
        # We have a gap and a freeze token — consume it for the most recent
        # missed scheduled day.
        streak.freeze_tokens -= 1
        session.add(FreezeEvent(habit_id=habit.id, user_id=habit.user_id, frozen_date=prev))
        streak.current_streak += 1
    else:
        # No freeze available, or no prior streak — fresh start.
        streak.current_streak = 1

    streak.last_completed_date = today
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak


def compute_streak_at_risk(habit: Habit, streak: Streak, tz_name: str) -> bool:
    """True iff the habit is scheduled today, not yet checked in, and local
    time has passed the AT_RISK_HOUR threshold."""
    now = local_now(tz_name)
    today = now.date()
    if not is_scheduled_on(habit.frequency, habit.custom_days, today):
        return False
    if streak.last_completed_date == today:
        return False
    return now.hour >= AT_RISK_HOUR


async def use_freeze_now(session: AsyncSession, habit: Habit, streak: Streak, today: date) -> None:
    """Manually consume a freeze token to save today's streak (when the user
    knows they'll miss the day and explicitly opts in)."""
    if streak.freeze_tokens <= 0:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No freeze tokens available")
    maybe_reset_weekly_token(streak, today)
    streak.freeze_tokens -= 1
    session.add(FreezeEvent(habit_id=habit.id, user_id=habit.user_id, frozen_date=today))
    streak.last_completed_date = today
    streak.current_streak += 1
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak
