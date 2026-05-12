# DECISIONS.md

**Project:** Habit Tracker API
**Student:** Selin Türkdoğan — 2103060004
**Course:** SFWE477 – Backend Development & DevOps Fundamentals

---

## Why MongoDB for Reminders?

I originally thought to add a reminders table in PostgreSQL but the problem is that the reminder config per user can vary a lot. Someone might set two notification times, someone else just one, some with a custom message, some without. In PostgreSQL I'd need nullable columns or a separate table just for times which felt messy.

MongoDB lets me store whatever shape makes sense for each user. It also makes sense for this course since we're supposed to use both databases.

The downside is I now have two separate databases running and I can't do a transaction across both. My plan is to always verify the habit exists in PostgreSQL before saving anything to MongoDB, and return a 404 if it doesn't.

---

## How I'm Calculating Streaks

The streak updates every time a check-in is logged. Basic flow:

1. Get today's date in the user's local timezone (stored in `users.timezone`)
2. Find the last scheduled day for this habit before today
3. Check if there is a check-in recorded for that day
4. If yes → increment `current_streak`
5. If no → check if `freeze_tokens > 0`
   - If a freeze is available → consume it, write to `freeze_events`, keep the streak
   - If no freeze → reset `current_streak` to 1 (this check-in is a fresh start)
6. Update `longest_streak` if current is now higher

**Weekly freeze token reset:** I looked at how Duolingo handles this and they use a server-side scheduled job. For now I'm going to do a lazy check instead — when any streak endpoint is called, I compare the current Monday (start of week) against a `last_token_reset_date` stored in the `streaks` table. If the stored date is before this Monday, I reset `freeze_tokens` to 1 and update the date. No background scheduler needed for Phase 2, and I can swap it out later if it causes problems.

I'm storing streak values in the `streaks` table instead of recalculating from all `check_ins` each time because that would get slow as the data grows.

---

## Timezone Handling and streak_at_risk

The tricky part here was making sure a check-in at 11:59 PM and one at 12:01 AM go to different calendar days. I'm using Python's `zoneinfo` to convert UTC to the user's local time and just storing the local date as a `DATE` field.

```python
from zoneinfo import ZoneInfo
from datetime import datetime

def get_local_date(timezone: str):
    return datetime.now(ZoneInfo(timezone)).date()
```

For `streak_at_risk`: it's `true` if the habit is scheduled today, the user hasn't checked in yet, and local time is past 9 PM. I compute this on the fly per request — nothing stored.

---

## Why a Separate streaks Table Instead of Calculating On-the-Fly?

Recalculating streaks by scanning all `check_ins` rows every time would get slow as data grows. Storing `current_streak`, `longest_streak`, and `last_completed_date` directly in the `streaks` table means streak reads are O(1). The tradeoff is that writes (check-ins) are slightly more expensive, but check-in frequency is low compared to read frequency on dashboards.

---

## Unique Constraint on check_ins

```sql
UNIQUE (habit_id, checked_date)
```

This prevents double check-ins at the database level — no application-level guard needed. If a user tries to check in twice on the same day for the same habit, the DB returns a conflict and the API responds with `409 Conflict`.
