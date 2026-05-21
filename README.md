# Habit Tracker API

**SFWE477 – Backend Development & DevOps Fundamentals**
Selin Türkdoğan — 2103060004

A backend API for a habit tracking application built with FastAPI, PostgreSQL, MongoDB, and Redis.


## Project Overview

This API powers a habit tracking app where users can create habits, log daily check-ins, and track streaks — including a **Streak Freeze & At-Risk Notification System** inspired by Duolingo's retention mechanics.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python) |
| Primary DB | PostgreSQL |
| Document DB | MongoDB (reminders) |
| Cache | Redis (dashboard) |
| Auth | JWT |
| Containerization | Docker Compose |
| CI | GitHub Actions |
| Deployment | Render |

## Unique Feature: Streak Freeze & At-Risk Notification

- Each user gets **1 freeze token per week**
- If a check-in is missed and a token is available, it is auto-consumed and the streak is preserved
- A `streak_at_risk` flag is exposed on habit detail endpoints (true after 9 PM local time with no check-in)
- Timezone-aware midnight boundaries using Python's `zoneinfo`

## Phase 2 — Running Locally

### Prerequisites

- Python 3.11+
- Docker Desktop (for PostgreSQL, MongoDB, Redis)

### Setup

```bash
# 1. Clone and create virtual env
git clone https://github.com/selinkbl/habit-tracker-api.git
cd habit-tracker-api
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env file
cp .env.example .env            # edit values if needed

# 4. Start databases
docker compose up -d

# 5. Run migrations
alembic upgrade head

# 6. Start API
uvicorn app.main:app --reload
```

API is available at **http://localhost:8000**
Interactive docs at **http://localhost:8000/docs**

### Endpoints (Phase 2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login → JWT |
| GET | `/api/v1/auth/me` | Current user |
| GET | `/api/v1/habits` | List active habits |
| POST | `/api/v1/habits` | Create habit |
| GET | `/api/v1/habits/{id}` | Get habit |
| PATCH | `/api/v1/habits/{id}` | Update habit |
| DELETE | `/api/v1/habits/{id}` | Soft-delete habit |
| POST | `/api/v1/habits/{id}/checkin` | Record check-in (409 if duplicate) |
| GET | `/api/v1/habits/{id}/checkins` | List check-ins |
| POST | `/api/v1/habits/{id}/freeze` | Use a freeze token |
| GET | `/api/v1/habits/{id}/streak` | Get streak details |
| GET | `/api/v1/streaks/summary` | All streaks for user |
| GET | `/api/v1/habits/{id}/reminder` | Get reminder (MongoDB) |
| POST | `/api/v1/habits/{id}/reminder` | Create/replace reminder |
| PATCH | `/api/v1/habits/{id}/reminder` | Partial update reminder |
| DELETE | `/api/v1/habits/{id}/reminder` | Delete reminder |
| GET | `/api/v1/dashboard` | Today's dashboard (Redis cache 5 min) |
| GET | `/health` | App health |
| GET | `/health/db` | DB connectivity check |

### Database Health Check

```bash
curl http://localhost:8000/health/db
# {"postgres":"ok","mongo":"ok","redis":"ok"}
```

## Design Documents (Phase 1)

- [`design/api_contract.md`](design/api_contract.md) — Full API endpoint specification
- [`DECISIONS.md`](DECISIONS.md) — Architecture and logic decisions
- [`design/erd.png`](design/erd.png) — Entity Relationship Diagram

