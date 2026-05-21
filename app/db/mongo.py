from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def init_mongo() -> AsyncIOMotorDatabase:
    global _client, _db
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongo_uri)
        _db = _client[settings.mongo_db]
    assert _db is not None
    return _db


async def close_mongo() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


def get_mongo() -> AsyncIOMotorDatabase:
    if _db is None:
        init_mongo()
    assert _db is not None
    return _db
