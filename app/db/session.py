from motor.motor_asyncio import AsyncIOMotorClient
from app.db.mongo import MongoDBClient


async def get_db() -> AsyncIOMotorClient:
    """Dependency to get MongoDB client instance"""
    return MongoDBClient.get_client()
