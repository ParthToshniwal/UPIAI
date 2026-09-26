"""
UPIAI (Universal Personalized Inventory AI) FastAPI Main Application Entrypoint.
Wires all AI engines, data readiness auditors, multi-horizon forecasters,
supplier loggers, and continuous feedback monitoring routers.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Ensure root workspace is on PYTHONPATH for AI core submodules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.database.mongodb import mongo_repo
from backend.app.database import db_manager, get_db_status
from backend.app.routers import readiness_router, ai_router, supplier_router
from backend.app.api import ingestion_router, forecast_router, monitoring_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s : %(message)s"
)
logger = logging.getLogger("upiai.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: connects database on startup and tears down on shutdown."""
    logger.info("🚀 Starting UPIAI Demand Intelligence Backend Engine...")
    await db_manager.connect_db()
    await mongo_repo.connect()
    yield
    logger.info("🛑 Shutting down UPIAI Backend Engine...")
    await db_manager.close_db()
    await mongo_repo.close()


app = FastAPI(
    title="UPIAI - Universal Personalized Inventory & Demand Intelligence API",
    description=(
        "Production-grade AI demand forecasting, dataset provenance auditing, "
        "and inventory optimization system powered by XGBoost, FastAPI, and MongoDB."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS with Vercel wildcard regex support
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,https://upiai.vercel.app")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Adds processing header and logs requests."""
    response = await call_next(request)
    response.headers["X-Powered-By"] = "UPIAI Intelligence Core"
    return response


# Register Feature Routers
app.include_router(ingestion_router.router)
app.include_router(readiness_router.router)
app.include_router(forecast_router.router)
app.include_router(ai_router.router)
app.include_router(supplier_router.router)
app.include_router(monitoring_router.router)


@app.get("/", tags=["System Diagnostics"])
async def root_index():
    """Returns system status and available API route hubs."""
    return {
        "system": "Universal Personalized Inventory AI (UPIAI)",
        "version": "1.0.0",
        "status": "ONLINE",
        "documentation": "/docs",
        "endpoints": {
            "data_ingestion": "/api/v1/ingest/upload",
            "data_readiness": "/api/v1/readiness/audit",
            "demand_forecast": "/api/v1/forecast/predict",
            "what_if_simulation": "/api/v1/forecast/simulate",
            "model_benchmarks": "/api/v1/forecast/benchmark",
            "executive_kpis": "/api/v1/ai/kpis",
            "reorder_queue": "/api/v1/ai/recommendations",
            "supplier_intelligence": "/api/v1/suppliers/intelligence",
            "model_monitoring": "/api/v1/monitoring/health"
        }
    }


@app.get("/health", tags=["System Diagnostics"])
async def health_check():
    """System health check endpoint for container probes and Vercel/Render monitors."""
    db_health = get_db_status()
    return {
        "status": "HEALTHY",
        "database": db_health,
        "engine_mode": "Active Autonomous",
        "ai_core_version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)
