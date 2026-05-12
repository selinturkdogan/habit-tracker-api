# API Contract

**Base URL:** `http://localhost:8000/api/v1`

All endpoints return JSON. Dates in ISO 8601. Timestamps in UTC.
Endpoints marked **Auth: yes** require `Authorization: Bearer <token>`.

---

## Auth

| Method | Endpoint | Description | Auth | Response |
|---|---|---|---|---|
| POST | `/auth/register` | Create account | No | 201 |
| POST | `/auth/login` | Returns JWT | No | 200 + token |
| GET | `/auth/me` | My profile | Yes | 200 |

---

## Habits

| Method | Endpoint | Description | Auth | Response |
|---|---|---|---|---|
| GET | `/habits` | List my habits | Yes | 200 |
| POST | `/habits` | Create a habit | Yes | 201 |
| GET | `/habits/{id}` | Habit + streak info + `streak_at_risk` flag | Yes | 200 |
| PATCH | `/habits/{id}` | Update habit | Yes | 200 |
| DELETE | `/habits/{id}` | Soft delete (`is_active = false`) | Yes | 204 |

### GET /habits/{id} — Response Example

```json
{
  "id": "uuid",
  "title": "Morning run",
  "frequency": "daily",
  "is_active": true,
  "streak": {
    "current_streak": 5,
    "longest_streak": 12,
    "last_completed_date": "2025-01-10",
    "freeze_tokens": 1
  },
  "streak_at_risk": false
}
```

---

## Check-ins

| Method | Endpoint | Description | Auth | Response |
|---|---|---|---|---|
| POST | `/habits/{id}/checkin` | Log check-in for today | Yes | 201 |
| GET | `/habits/{id}/checkins` | Check-in history | Yes | 200 |

---

## Streaks

| Method | Endpoint | Description | Auth | Response |
|---|---|---|---|---|
| GET | `/habits/{id}/streak` | Streak details for one habit | Yes | 200 |
| GET | `/streaks/summary` | All habits streak overview | Yes | 200 |

---

## Reminders

| Method | Endpoint | Description | Auth | Response |
|---|---|---|---|---|
| GET | `/habits/{id}/reminder` | Get reminder config | Yes | 200 |
| POST | `/habits/{id}/reminder` | Set reminder | Yes | 201 |
| PATCH | `/habits/{id}/reminder` | Update reminder | Yes | 200 |
| DELETE | `/habits/{id}/reminder` | Remove reminder | Yes | 204 |

### Reminder document shape (MongoDB)

```json
{
  "_id": "ObjectId",
  "habit_id": "uuid",
  "user_id": "uuid",
  "times": ["08:00", "20:00"],
  "message": "don't forget!",
  "enabled": true,
  "updated_at": "ISODate"
}
```

---

## Dashboard

| Method | Endpoint | Description | Auth | Response |
|---|---|---|---|---|
| GET | `/dashboard` | Today's habits + completion rate (Redis, 5 min cache) | Yes | 200 |

---

## Error Codes

| Code | Meaning |
|---|---|
| 400 | Bad request / missing field |
| 401 | Not logged in or token expired |
| 403 | You don't own this resource |
| 404 | Not found |
| 409 | Already checked in today for this habit |
| 500 | Server error |
