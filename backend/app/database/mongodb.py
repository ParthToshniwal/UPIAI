"""
MongoDB Atlas Motor Async Driver & Repository Accessor for UPIAI.
Manages connections, collections, indexes, and resilient in-memory fallback caches.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import motor.motor_asyncio
import pymongo

load_dotenv()

logger = logging.getLogger("upiai.mongodb")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/upiai_db")
DATABASE_NAME = os.getenv("DATABASE_NAME", "upiai_db")


class MongoRepository:
    """Async repository manager with index creation and fallback resilience."""

    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db = None
        self.is_connected: bool = False

    async def connect(self):
        """Initializes Motor Async connection."""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGO_URI,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000
            )
            # Test ping
            await self.client.admin.command('ping')
            self.db = self.client[DATABASE_NAME]
            self.is_connected = True
            logger.info("Connected to MongoDB Atlas: %s", DATABASE_NAME)
            await self._init_indexes()
        except Exception as err:
            logger.warning("MongoDB unavailable (%s). Running in memory mode.", err)
            self.is_connected = False

    async def _init_indexes(self):
        if not self.is_connected or self.db is None:
            return
        try:
            await self.db.products.create_index("sku", unique=True)
            await self.db.sales.create_index([("sku", 1), ("date", -1)])
            await self.db.suppliers.create_index("supplier_id", unique=True)
            await self.db.purchase_orders.create_index("po_number", unique=True)
            await self.db.feedback_logs.create_index("date")
        except Exception as e:
            logger.warning("Index notice: %s", e)

    async def close(self):
        if self.client:
            self.client.close()
            self.is_connected = False


mongo_repo = MongoRepository()


def get_mongo_db():
    if mongo_repo.is_connected and mongo_repo.db is not None:
        return mongo_repo.db
    return None
