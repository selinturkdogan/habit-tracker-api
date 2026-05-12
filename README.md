# Habit Tracker API

**SFWE477 – Backend Development & DevOps Fundamentals**
**Student:** Selin Türkdoğan — 2103060004

A backend API for a habit tracking application built with FastAPI, PostgreSQL, MongoDB, and Redis.

---

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

## Project Phases

| Phase | Status | Description |
|---|---|---|
| Phase 1 – Design | ✅ Complete | ERD, API Contract, DECISIONS.md |
| Phase 2 – Build | 🔜 Pending approval | FastAPI implementation |
| Phase 3 – Secure | 🔜 Pending | JWT, rate limiting, validation |
| Phase 4 – Deploy | 🔜 Pending | Docker Compose, CI/CD, Render |

## Unique Feature: Streak Freeze & At-Risk Notification

- Each user gets **1 freeze token per week**
- If a check-in is missed and a token is available, it is auto-consumed and the streak is preserved
- A `streak_at_risk` flag is exposed on habit detail endpoints (true after 9 PM local time with no check-in)
- Timezone-aware midnight boundaries using Python's `zoneinfo`

## Design Documents (Phase 1)

- [`design/api_contract.md`](design/api_contract.md) — Full API endpoint specification
- [`DECISIONS.md`](DECISIONS.md) — Architecture and logic decisions
- [`design/erd.png`](design/erd.png) — Entity Relationship Diagram

## Base URL

```
http://localhost:8000/api/v1
```
