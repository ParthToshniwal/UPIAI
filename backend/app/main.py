"""
UPIAI (Universal Personalized Inventory AI) FastAPI Main Application Entrypoint.
Wires Turso (libsql) database engine, DMart CSV auto-ingestion,
Data Readiness & Provenance Auditor, XGBoost Multi-Horizon Forecaster,
and Streamlit/Vercel compatible API routers.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Ensure root workspace and backend dir are in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from app.database import turso_db
from app.routers import readiness_router, ai_router, supplier_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s : %(message)s"
)
logger = logging.getLogger("upiai.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initializes Turso database and ingests DMart datasets."""
    logger.info("🚀 Starting UPIAI Demand Intelligence Backend with Turso (libsql)...")
    await turso_db.connect_db()
    yield
    logger.info("🛑 Shutting down UPIAI Backend Engine...")


app = FastAPI(
    title="UPIAI - Universal Personalized Inventory & Demand Intelligence API",
    description=(
        "Production-grade AI demand forecasting, dataset provenance auditing, "
        "and inventory optimization system powered by XGBoost, FastAPI, and Turso (libsql)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS for Streamlit (8501), Next.js (3000), and Vercel Cloud
allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000,http://127.0.0.1:3000,https://upiai.vercel.app"
)
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
    """Adds custom telemetry header to API responses."""
    response = await call_next(request)
    response.headers["X-Powered-By"] = "UPIAI Turso Intelligence Core"
    return response


# Register Core Routers
app.include_router(readiness_router.router)
app.include_router(ai_router.router)
app.include_router(supplier_router.router)


@app.get("/", tags=["System Diagnostics"])
async def root_index():
    """Returns platform overview, Turso DB status, and registered API hubs."""
    db_status = turso_db.get_db_status()
    return {
        "system": "Universal Personalized Inventory AI (UPIAI)",
        "version": "1.0.0",
        "status": "ONLINE",
        "database": db_status,
        "documentation": "/docs",
        "endpoints": {
            "data_readiness": "/api/v1/readiness",
            "executive_kpis": "/api/v1/ai/kpis",
            "demand_forecast": "/api/v1/ai/forecast",
            "category_performance": "/api/v1/ai/categories",
            "sales_analytics": "/api/v1/ai/sales-analytics",
            "inventory_status": "/api/v1/ai/inventory",
            "supplier_intelligence": "/api/v1/suppliers/intelligence"
        }
    }


@app.get("/health", tags=["System Diagnostics"])
async def health_check():
    """System health check endpoint for monitoring probes."""
    db_status = turso_db.get_db_status()
    return {
        "status": "HEALTHY",
        "database": db_status,
        "engine_mode": "Active Autonomous XGBoost + Turso",
        "ai_core_version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
