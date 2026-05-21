from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def local_date_for(tz_name: str) -> date:
    """Return today's calendar date in the user's local timezone."""
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date()


def local_now(tz_name: str) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


def dow_mon0(d: date) -> int:
    """0=Mon ... 6=Sun."""
    return d.weekday()


def is_scheduled_on(frequency: str, custom_days: list[int] | None, day: date) -> bool:
    dow = dow_mon0(day)
    if frequency == "daily":
        return True
    if frequency == "weekdays":
        return dow < 5
    if frequency == "custom":
        return dow in (custom_days or [])
    return False


def monday_of(d: date) -> date:
    from datetime import timedelta

    return d - timedelta(days=d.weekday())
