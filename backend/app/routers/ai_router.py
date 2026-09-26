"""
AI Demand Forecasting and Inventory Intelligence Router.
Provides multi-horizon 7-day & 30-day demand predictions, stockout probability scoring,
reorder recommendations, and executive KPI aggregations.
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
from app.ml.forecaster import DemandForecaster, XGB_AVAILABLE
from app.ml.readiness import DataReadinessEngine
from app.database import get_database, db_manager
from app.services.sample_data import (
    SAMPLE_PRODUCTS,
    SAMPLE_SUPPLIERS,
    generate_synthetic_sales_history
)

router = APIRouter(prefix="/api/v1/ai", tags=["AI Demand Intelligence & Forecasting"])


async def _get_active_catalog_and_sales(custom_sales: Optional[List[Dict[str, Any]]] = None):
    """Helper to fetch products and sales from MongoDB or high-fidelity sample data."""
    db = get_database()
    products = list(SAMPLE_PRODUCTS)
    sales = []

    if custom_sales and len(custom_sales) > 0:
        sales = custom_sales
    elif db is not None:
        try:
            p_cursor = db.products.find({}, {"_id": 0})
            db_prods = await p_cursor.to_list(length=100)
            if db_prods:
                products = db_prods

            s_cursor = db.sales.find({}, {"_id": 0}).limit(10000)
            db_sales = await s_cursor.to_list(length=10000)
            if db_sales:
                sales = db_sales
        except Exception:
            pass

    if not sales:
        sales = generate_synthetic_sales_history(90)

    return products, sales


@router.post("/forecast", response_model=ForecastResponse)
async def generate_demand_forecast(payload: Optional[ForecastRequest] = None):
    """
    Executes XGBoost and time-series rolling ML models across catalog SKUs.
    Returns 7-day & 30-day demand trajectories, stockout probability risk, and reorder POs.
    """
    custom_sales = payload.custom_sales_data if payload else None
    skus_filter = payload.skus if payload else None
    horizon_days = payload.forecast_horizon_days if payload else 30

    products, sales = await _get_active_catalog_and_sales(custom_sales)
    sales_df = pd.DataFrame(sales)

    # Standardize column names if needed
    if 'order_date' in sales_df.columns and 'date' not in sales_df.columns:
        sales_df['date'] = sales_df['order_date']
    if 'item_id' in sales_df.columns and 'sku' not in sales_df.columns:
        sales_df['sku'] = sales_df['item_id']
    if 'quantity' in sales_df.columns and 'units_sold' not in sales_df.columns:
        sales_df['units_sold'] = sales_df['quantity']

    forecaster = DemandForecaster(horizon_days=horizon_days)
    sku_forecasts: List[SKUForecastDetail] = []

    total_inventory_val = 0.0
    total_capital_risk = 0.0
    total_reorder_cost = 0.0
    critical_count = 0
    warning_count = 0

    target_products = products
    if skus_filter:
        target_products = [p for p in products if p["sku"] in skus_filter]

    for p in target_products:
        sku = p["sku"]
        detail = forecaster.forecast_sku(sku, p, sales_df)
        sku_forecasts.append(detail)

        total_inventory_val += (detail.current_stock * detail.unit_cost)
        total_capital_risk += detail.risk_assessment.estimated_revenue_at_risk
        total_reorder_cost += detail.reorder_recommendation.estimated_order_cost

        if detail.risk_assessment.risk_level == "CRITICAL":
            critical_count += 1
        elif detail.risk_assessment.risk_level == "WARNING":
            warning_count += 1

    return ForecastResponse(
        generated_at=datetime.utcnow().isoformat(),
        model_type_used="XGBoost Regressor + Multi-lag Rolling Engine" if XGB_AVAILABLE else "Moving Average Seasonality",
        total_skus_analyzed=len(sku_forecasts),
        critical_stockout_count=critical_count,
        warning_count=warning_count,
        total_inventory_value=round(total_inventory_val, 2),
        total_capital_at_risk=round(total_capital_risk, 2),
        total_recommended_reorder_cost=round(total_reorder_cost, 2),
        sku_forecasts=sku_forecasts
    )


@router.get("/kpis", response_model=ExecutiveKPIResponse)
async def get_executive_kpis():
    """
    Returns top-level executive metrics for dashboard scorecards and risk meters.
    """
    products, sales = await _get_active_catalog_and_sales()
    sales_df = pd.DataFrame(sales)

    forecaster = DemandForecaster(horizon_days=30)
    total_revenue_30d = 0.0
    total_inv_val = 0.0
    excess_capital = 0.0
    critical_skus = 0
    total_reorder_budget = 0.0

    for p in products:
        detail = forecaster.forecast_sku(p["sku"], p, sales_df)
        total_revenue_30d += (detail.forecast_30d_total * detail.unit_price)
        total_inv_val += (detail.current_stock * detail.unit_cost)
        total_reorder_budget += detail.reorder_recommendation.estimated_order_cost

        if detail.risk_assessment.risk_level == "CRITICAL":
            critical_skus += 1
        elif detail.risk_assessment.risk_level == "OVERSTOCKED":
            excess_capital += ((detail.current_stock - 50) * detail.unit_cost)

    # Calculate audit health
    readiness = DataReadinessEngine.audit_dataset(sales)

    # Supplier reliability average
    avg_rel = sum(s["on_time_delivery_rate"] for s in SAMPLE_SUPPLIERS) / len(SAMPLE_SUPPLIERS)

    stockout_risk_pct = round((critical_skus / max(1, len(products))) * 100.0, 1)

    return ExecutiveKPIResponse(
        total_revenue_30d_projected=round(total_revenue_30d, 2),
        total_inventory_value=round(total_inv_val, 2),
        capital_tied_up_excess=round(max(0.0, excess_capital), 2),
        stockout_risk_percentage=stockout_risk_pct,
        critical_skus_count=critical_skus,
        supplier_reliability_index=round(avg_rel * 100.0, 1),
        system_readiness_score=readiness.overall_readiness_score,
        dataset_health_label=readiness.operational_tier,
        pending_reorder_budget=round(total_reorder_budget, 2)
    )


@router.get("/recommendations", response_model=List[ReorderRecommendation])
async def get_reorder_recommendations(urgency: Optional[str] = None):
    """
    Returns ranked actionable purchase order reorder recommendations.
    """
    products, sales = await _get_active_catalog_and_sales()
    sales_df = pd.DataFrame(sales)

    forecaster = DemandForecaster(horizon_days=30)
    recs = []

    for p in products:
        detail = forecaster.forecast_sku(p["sku"], p, sales_df)
        rec = detail.reorder_recommendation
        if urgency is None or rec.urgency.upper() == urgency.upper():
            recs.append(rec)

    # Sort so IMMEDIATE comes first
    urgency_priority = {"IMMEDIATE": 0, "PLAN_THIS_WEEK": 1, "NORMAL": 2, "NO_ACTION": 3}
    recs.sort(key=lambda r: urgency_priority.get(r.urgency, 99))

    return recs


@router.post("/reorder-action")
async def execute_simulated_reorder(payload: Dict[str, Any]):
    """
    Simulates placing an official Purchase Order to a supplier,
    updating on_order balances in memory or MongoDB.
    """
    sku = payload.get("sku")
    quantity = int(payload.get("quantity", 0))
    supplier_id = payload.get("supplier_id")

    if not sku or quantity <= 0:
        raise HTTPException(status_code=400, detail="Valid SKU and quantity > 0 required.")

    # Update in memory SAMPLE_PRODUCTS
    for p in SAMPLE_PRODUCTS:
        if p["sku"] == sku:
            p["on_order_stock"] = p.get("on_order_stock", 0) + quantity
            return {
                "success": True,
                "message": f"PO successfully dispatched to {p.get('supplier_name', supplier_id)} for {quantity} units of {sku}.",
                "updated_sku": p["sku"],
                "new_on_order_stock": p["on_order_stock"],
                "po_reference": f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M')}-{sku}"
            }

    return {
        "success": True,
        "message": f"Simulated PO processed for SKU {sku} ({quantity} units).",
        "po_reference": f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M')}-{sku}"
    }
