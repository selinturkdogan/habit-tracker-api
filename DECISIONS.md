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

## Two-Factor Authentication

### Why TOTP over SMS-based OTP?

I chose TOTP (Time-Based One-Time Password) over SMS for three reasons:

1. **Cost** — SMS-based OTP requires a third-party provider (Twilio, AWS SNS) with per-message fees. TOTP is entirely free; the shared secret is established once at setup and all future code generation happens locally on the user's device and server.
2. **SIM-swapping attacks** — SMS OTP is vulnerable to SIM-swapping, where an attacker convinces the carrier to transfer the victim's phone number to a new SIM. TOTP is immune because the secret is tied to the authenticator app, not a phone number.
3. **No phone number required** — Users don't have to hand over their phone number. This is better for privacy and for users who may not have a mobile number.

### How I store the TOTP secret

The `otp_secret` field in the `users` table stores the Base32-encoded secret as plaintext. For a Phase 2 academic project this is acceptable, but in production I would encrypt it at rest using AES-256 (with the key stored in an environment variable or a secrets manager like AWS Secrets Manager). The tradeoff is implementation complexity vs. security depth — the secret is already protected by the application-layer authentication, but encrypting it adds defence-in-depth against a direct database dump.

### What happens if a user loses their phone?

In the current implementation, losing access to the authenticator app means the user is locked out of their account if 2FA is active. In a production version I would implement:

- **Backup codes** — generate 8–10 single-use recovery codes at setup time (hashed in the DB), displayed once to the user. Any one code can be used instead of the TOTP code to log in and then disable 2FA.
- **Admin reset endpoint** — an authenticated admin endpoint that can clear `otp_enabled` after identity verification through another channel (e.g. email confirmation link).

### What is `valid_window=1` in pyotp?

TOTP codes are valid for 30-second windows. `valid_window=1` means pyotp accepts codes from the **previous** and **next** 30-second window in addition to the current one — a total window of 90 seconds. This is necessary because the user's phone clock and the server clock may not be perfectly synchronised. Without this tolerance, a user whose phone is even a few seconds behind would be rejected on every login attempt. Most production TOTP implementations use `valid_window=1` as the standard value.

---

## Unique Constraint on check_ins

```sql
UNIQUE (habit_id, checked_date)
```

This prevents double check-ins at the database level — no application-level guard needed. If a user tries to check in twice on the same day for the same habit, the DB returns a conflict and the API responds with `409 Conflict`.
