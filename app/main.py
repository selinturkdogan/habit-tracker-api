from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict[str, str]:
    """Pings all three databases and reports status."""
    from app.db.postgres import init_engine as _init_engine

    statuses: dict[str, str] = {}

    # Postgres
    try:
        engine = _init_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        statuses["postgres"] = "ok"
    except Exception as e:  # pragma: no cover
        statuses["postgres"] = f"error: {e}"

    # Mongo
    try:
        mongo = get_mongo()
        await mongo.command("ping")
        statuses["mongo"] = "ok"
    except Exception as e:  # pragma: no cover
        statuses["mongo"] = f"error: {e}"

    # Redis
    try:
        redis = get_redis()
        await redis.ping()
        statuses["redis"] = "ok"
    except Exception as e:  # pragma: no cover
        statuses["redis"] = f"error: {e}"

    return statuses
