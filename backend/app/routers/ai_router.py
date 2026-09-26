"""
AI Demand Forecasting and Inventory Intelligence Router for DMart Retail Analytics.
Provides multi-horizon 7-day & 30-day demand predictions, stockout probability scoring,
reorder recommendations, executive KPI aggregations, and customer segmentation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from app.models.schemas import (
    ForecastRequest,
    ForecastResponse,
    SKUForecastDetail,
    ExecutiveKPIResponse,
    ReorderRecommendation
)
from app.ml.forecaster import DMartDemandForecaster, XGB_AVAILABLE
from app.ml.readiness import DataReadinessEngine
from app.database import turso_db

router = APIRouter(prefix="/api/v1/ai", tags=["AI Demand Intelligence & Forecasting"])


@router.get("/kpis", response_model=Dict[str, Any])
async def get_executive_kpis():
    """
    Returns executive KPI metrics calculated directly from the DMart datasets in Turso.
    """
    kpis = turso_db.get_kpis()
    inv_items = turso_db.get_inventory_items()
    
    total_inv_val = sum(i["current_stock"] * i["unit_cost"] for i in inv_items)
    
    # Run rapid forecaster for forward-looking risk totals
    cat_summary = turso_db.get_category_summary()
    daily_sales = turso_db.get_daily_sales_series()
    forecaster = DMartDemandForecaster(horizon_days=30)
    forecast_summary = forecaster.forecast_all_categories(cat_summary, inv_items, daily_sales)

    return {
        "total_revenue": kpis["total_revenue"],
        "total_profit": kpis["total_profit"],
        "avg_margin_pct": kpis["avg_margin_pct"],
        "total_units_sold": kpis["total_units_sold"],
        "total_transactions": kpis["total_transactions"],
        "avg_order_value": kpis["avg_order_value"],
        "total_categories": kpis["total_categories"],
        "unique_customers": kpis["unique_customers"],
        "total_inventory_value": round(total_inv_val, 2),
        "critical_stockouts": forecast_summary.critical_stockout_count,
        "warning_stockouts": forecast_summary.warning_count,
        "capital_at_risk": forecast_summary.total_capital_at_risk,
        "recommended_reorder_budget": forecast_summary.total_recommended_reorder_cost,
        "model_engine": forecast_summary.model_type_used
    }


@router.get("/forecast", response_model=ForecastResponse)
async def get_all_category_forecasts(horizon_days: int = Query(default=30, ge=7, le=90)):
    """
    Computes XGBoost 7-day and 30-day demand forecast and stockout risk for all DMart categories.
    """
    cat_summary = turso_db.get_category_summary()
    inv_items = turso_db.get_inventory_items()
    daily_sales = turso_db.get_daily_sales_series()

    forecaster = DMartDemandForecaster(horizon_days=horizon_days)
    return forecaster.forecast_all_categories(cat_summary, inv_items, daily_sales)


@router.post("/forecast", response_model=ForecastResponse)
async def generate_custom_forecast(payload: Optional[ForecastRequest] = None):
    """
    Handles customizable demand forecast requests with horizon parameters and optional SKU filters.
    """
    horizon = payload.forecast_horizon_days if payload else 30
    cat_summary = turso_db.get_category_summary()
    inv_items = turso_db.get_inventory_items()

    if payload and payload.custom_sales_data:
        daily_sales = pd.DataFrame(payload.custom_sales_data)
    else:
        daily_sales = turso_db.get_daily_sales_series()

    if payload and payload.skus:
        inv_items = [i for i in inv_items if i.get("sku") in payload.skus or i.get("category") in payload.skus]

    forecaster = DMartDemandForecaster(horizon_days=horizon)
    return forecaster.forecast_all_categories(cat_summary, inv_items, daily_sales)


@router.get("/forecast/{category}", response_model=SKUForecastDetail)
async def get_single_category_forecast(category: str, horizon_days: int = Query(default=30, ge=7, le=90)):
    """
    Returns high-granularity forecast trajectory curves and stockout assessment for a specific DMart category.
    """
    inv_items = turso_db.get_inventory_items()
    matched_inv = next((i for i in inv_items if i["category"].lower() == category.lower()), None)
    
    if not matched_inv:
        matched_inv = {
            "sku": f"DMART-{category[:3].upper()}-001",
            "product_name": f"DMart {category}",
            "category": category,
            "current_stock": 140,
            "unit_cost": 70.0,
            "unit_price": 100.0,
            "lead_time_days": 7,
            "supplier_id": "SUP-DMART-01"
        }

    daily_sales = turso_db.get_daily_sales_series(category=category)
    forecaster = DMartDemandForecaster(horizon_days=horizon_days)
    return forecaster.forecast_category(category, matched_inv, daily_sales)


@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_categories_performance():
    """
    Returns revenue, unit sales volume, average price, and margin percentages per DMart category.
    """
    return turso_db.get_category_summary()


@router.get("/sales-analytics", response_model=Dict[str, Any])
async def get_sales_analytics():
    """
    Provides multi-dimensional sales analytics: time-series, customer segments, and hourly store footfall.
    """
    daily_df = turso_db.get_daily_sales_series()
    daily_series = daily_df.to_dict(orient="records") if not daily_df.empty else []
    cust_dist = turso_db.get_customer_type_distribution()
    hourly_traffic = turso_db.get_hourly_traffic()

    return {
        "daily_trends": daily_series,
        "customer_segments": cust_dist,
        "hourly_traffic": hourly_traffic
    }


@router.get("/inventory", response_model=List[Dict[str, Any]])
async def get_inventory_status():
    """
    Returns inventory state, warehouse stock levels, and replenishment thresholds.
    """
    return turso_db.get_inventory_items()
