from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import Settings


class MongoDBClient:
    """MongoDB connection manager"""

    _instance: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    async def connect(cls, settings: Settings) -> None:
        """Initialize MongoDB connection"""
        cls._instance = AsyncIOMotorClient(settings.mongodb_url)
        cls._db = cls._instance[settings.mongodb_db_name]

    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            cls._db = None

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get the database instance"""
        if cls._db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return cls._db

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """Get the MongoDB client"""
        if cls._instance is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return cls._instance
