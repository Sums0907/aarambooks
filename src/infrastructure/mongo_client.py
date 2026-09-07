import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Manages the lifecycle of the MongoDB connection for unstructured data storage."""
    client: Optional[AsyncIOMotorClient] = None

    @classmethod
    async def connect(cls, uri: str = "mongodb://localhost:27017"):
        if cls.client is None:
            logger.info(f"Connecting to MongoDB at {uri}...")
            cls.client = AsyncIOMotorClient(uri)
            # Verify connection
            try:
                await cls.client.admin.command('ping')
                logger.info("MongoDB connection established successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                cls.client = None
                raise

    @classmethod
    async def disconnect(cls):
        if cls.client is not None:
            cls.client.close()
            logger.info("MongoDB connection closed.")
            cls.client = None

    @classmethod
    def get_database(cls, db_name: str):
        if cls.client is None:
            raise RuntimeError("MongoDB client is not initialized. Call connect() first.")
        return cls.client[db_name]

# Dependency for FastAPI
async def get_mongo_db():
    if MongoDBManager.client is None:
        await MongoDBManager.connect()
    return MongoDBManager.get_database("aarambooks_ndr_communications")
