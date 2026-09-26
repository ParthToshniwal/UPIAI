"""
Data Readiness & Provenance Engine Router.
Exposes endpoints for auditing dataset integrity, calculating confidence readiness scores,
and evaluating structural risk factors before triggering ML forecasting.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
import pandas as pd
import io

from app.models.schemas import ReadinessScorecardResponse, ReadinessAuditRequest
from app.ml.readiness import DataReadinessEngine
from app.database import get_database, db_manager
from app.services.sample_data import generate_synthetic_sales_history, SAMPLE_PRODUCTS

router = APIRouter(prefix="/api/v1/readiness", tags=["Data Readiness & Provenance"])


@router.post("/audit", response_model=ReadinessScorecardResponse)
async def audit_dataset_health(payload: Optional[ReadinessAuditRequest] = None):
    """
    Audits an uploaded dataset or the active database records for ML demand forecasting readiness.
    Calculates missing columns, time continuity, and overall governance score (0-100%).
    """
    if payload and payload.dataset and len(payload.dataset) > 0:
        scorecard = DataReadinessEngine.audit_dataset(payload.dataset)
        return scorecard

    # If no payload provided, check active MongoDB or default dataset
    db = get_database()
    sales_data = []

    if db is not None:
        try:
            cursor = db.sales.find({}, {"_id": 0}).limit(5000)
            sales_data = await cursor.to_list(length=5000)
        except Exception:
            sales_data = []

    if not sales_data:
        # Fallback to local high-fidelity sales seed combined with product meta
        sales_records = generate_synthetic_sales_history(90)
        prod_lookup = {p["sku"]: p for p in SAMPLE_PRODUCTS}
        
        merged_data = []
        for s in sales_records:
            sku_meta = prod_lookup.get(s["sku"], {})
            merged_row = {
                **s,
                "current_stock": sku_meta.get("current_stock", 50),
                "unit_cost": sku_meta.get("unit_cost", 40.0),
                "lead_time_days": sku_meta.get("lead_time_days", 14),
                "supplier_id": sku_meta.get("supplier_id", "SUP-001"),
                "category": sku_meta.get("category", "General")
            }
            merged_data.append(merged_row)
        sales_data = merged_data

    scorecard = DataReadinessEngine.audit_dataset(sales_data)
    return scorecard


@router.post("/upload-csv", response_model=ReadinessScorecardResponse)
async def audit_csv_file(file: UploadFile = File(...)):
    """
    Accepts a raw CSV file upload from the client dashboard, parses headers,
    and returns a full health scorecard with provenance warnings.
    """
    if not file.filename.endswith(('.csv', '.txt')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .csv file.")

    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='replace')))
        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")
        
        scorecard = DataReadinessEngine.audit_dataset(df)
        return scorecard
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {str(exc)}")


@router.get("/sample", response_model=Dict[str, Any])
async def get_sample_test_datasets():
    """
    Returns curated sample datasets (High Health vs Imperfect) for rapid frontend testing.
    """
    high_health_sales = generate_synthetic_sales_history(60)[:30]
    
    # Imperfect dataset with missing lead time and cost columns
    imperfect_dataset = []
    for row in high_health_sales[:20]:
        imperfect_dataset.append({
            "order_date": row["date"],
            "item_id": row["sku"],
            "quantity": row["units_sold"],
            # Deliberately omitted: lead_time_days, unit_cost, current_stock
        })

    return {
        "benchmark_high_confidence": high_health_sales,
        "imperfect_raw_test_data": imperfect_dataset
    }
