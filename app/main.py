from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.check_ins import router as check_ins_router
from app.api.dashboard import router as dashboard_router
from app.api.habits import router as habits_router
from app.api.reminders import router as reminders_router
from app.api.streaks import router as streaks_router
from app.db.mongo import close_mongo, get_mongo, init_mongo
from app.db.postgres import dispose_engine, init_engine
from app.db.redis import close_redis, get_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    init_mongo()
    init_redis()
    yield
    await dispose_engine()
    await close_mongo()
    await close_redis()


app = FastAPI(
    title="Habit Tracker API",
    description="Backend for the Habit Tracker app — SFWE477 final project.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — Phase 3 will lock this down to specific origins / methods.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development (Vite)
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        # Production frontend on Render
        "https://habit-tracker-frontend-g7s7.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1 = "/api/v1"
app.include_router(auth_router, prefix=API_V1)
app.include_router(habits_router, prefix=API_V1)
app.include_router(check_ins_router, prefix=API_V1)
app.include_router(streaks_router, prefix=API_V1)
app.include_router(reminders_router, prefix=API_V1)
app.include_router(dashboard_router, prefix=API_V1)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict[str, str]:
    """Pings all three databases and reports status."""
    from app.db.postgres import init_engine as _init_engine

    statuses: dict[str, str] = {}

    try:
        engine = _init_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        statuses["postgres"] = "ok"
    except Exception as e:  # pragma: no cover
        statuses["postgres"] = f"error: {e}"

    try:
        mongo = get_mongo()
        await mongo.command("ping")
        statuses["mongo"] = "ok"
    except Exception as e:  # pragma: no cover
        statuses["mongo"] = f"error: {e}"

    try:
        redis = get_redis()
        await redis.ping()
        statuses["redis"] = "ok"
    except Exception as e:  # pragma: no cover
        statuses["redis"] = f"error: {e}"

    return statuses
