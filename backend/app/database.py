"""
Database Connection and Client Lifecycle Handler for MongoDB Atlas.
Provides Async Motor client connections and synchronous PyMongo support.
Includes resilient fallback mock store if MongoDB connection is unreachable.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import motor.motor_asyncio
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

load_dotenv()

logger = logging.getLogger("upiai.database")

MONGO_URI = os.getenv(
    "MONGO_URI", 
    "mongodb+srv://admin:password@cluster0.mongodb.net/upiai_db?retryWrites=true&w=majority"
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "upiai_db")

class DatabaseManager:
    """Manages Async Motor and Synchronous PyMongo clients with fallback resilience."""
    
    def __init__(self):
        self.async_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.sync_client: Optional[pymongo.MongoClient] = None
        self.async_db = None
        self.sync_db = None
        self.is_connected: bool = False
        
        # In-memory storage cache for instant dev/offline testing & fallback
        self.memory_store: Dict[str, List[Dict[str, Any]]] = {
            "products": [],
            "sales": [],
            "inventory": [],
            "suppliers": [],
            "forecast_audits": []
        }

    async def connect_db(self):
        """Initializes asynchronous MongoDB Atlas connection with timeout guard."""
        try:
            logger.info("Connecting to MongoDB Atlas at %s...", MONGO_URI.split("@")[-1] if "@" in MONGO_URI else "localhost")
            self.async_client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGO_URI,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000
            )
            # Test connection with ping
            await self.async_client.admin.command('ping')
            self.async_db = self.async_client[DATABASE_NAME]
            self.is_connected = True
            logger.info("✅ Successfully connected to MongoDB Atlas database '%s'", DATABASE_NAME)
            await self._create_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as exc:
            logger.warning(
                "⚠️ MongoDB connection unavailable (%s). Running in Resilient Fallback Memory Mode.",
                str(exc)
            )
            self.is_connected = False

    def get_sync_db(self):
        """Returns a synchronous PyMongo database handle for batch ML processing."""
        if self.sync_db is not None:
            return self.sync_db
        try:
            self.sync_client = pymongo.MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000
            )
            self.sync_client.admin.command('ping')
            self.sync_db = self.sync_client[DATABASE_NAME]
            return self.sync_db
        except Exception as exc:
            logger.warning("Synchronous MongoDB client failed (%s). Using in-memory fallback.", exc)
            return None

    async def _create_indexes(self):
        """Sets up high-performance indexes on collections."""
        if not self.is_connected or self.async_db is None:
            return
        try:
            await self.async_db.products.create_index("sku", unique=True)
            await self.async_db.sales.create_index([("sku", 1), ("date", -1)])
            await self.async_db.suppliers.create_index("supplier_id", unique=True)
            await self.async_db.inventory.create_index("sku", unique=True)
            logger.info("MongoDB indexes verified.")
        except Exception as err:
            logger.warning("Index creation notice: %s", err)

    async def close_db(self):
        """Closes all active database connections."""
        if self.async_client:
            self.async_client.close()
            logger.info("Motor async connection closed.")
        if self.sync_client:
            self.sync_client.close()
            logger.info("PyMongo sync connection closed.")
        self.is_connected = False


db_manager = DatabaseManager()

def get_database():
    """Dependency / accessor for async database handle."""
    if db_manager.is_connected and db_manager.async_db is not None:
        return db_manager.async_db
    return None

def get_db_status() -> Dict[str, Any]:
    """Returns the current database connection health and target database name."""
    return {
        "connected": db_manager.is_connected,
        "database": DATABASE_NAME,
        "mode": "MongoDB Atlas" if db_manager.is_connected else "Resilient In-Memory Mode"
    }
