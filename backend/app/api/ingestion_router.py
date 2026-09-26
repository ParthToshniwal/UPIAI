"""
Data Ingestion and Provenance Auditing API Router for UPIAI.
Accepts raw tabular files, executes automated profiling, maps schemas to canonical representations,
and returns data readiness scorecard with explicit capability disclosures.
"""

from typing import Optional, List, Dict, Any
import io
import os
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File

from ai.data.loader import DataLoader, DatasetProvenance
from ai.data.profiler import DataProfiler
from ai.schema.schema_mapper import UniversalSchemaMapper
from ai.schema.data_readiness import DataReadinessAuditor
from ai.decision_engine import UPIDecisionEngine
from backend.app.database.mongodb import get_mongo_db

router = APIRouter(prefix="/api/v1/ingest", tags=["Data Ingestion & Profiling"])


@router.post("/upload")
async def upload_and_audit_dataset(file: UploadFile = File(...)):
    """
    Ingests an uploaded CSV/JSON file, profiles distributions, maps columns,
    and returns a pre-flight data readiness audit scorecard.
    """
    filename = file.filename or "uploaded_file.csv"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ['.csv', '.txt', '.json', '.xlsx']:
        raise HTTPException(status_code=400, detail="Supported file formats: .csv, .json, .xlsx")

    contents = await file.read()
    try:
        if ext in ['.csv', '.txt']:
            df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='replace')))
        elif ext == '.json':
            df = pd.read_json(io.BytesIO(contents))
        elif ext == '.xlsx':
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise ValueError("Unsupported extension")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse tabular file: {str(exc)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded dataset contains zero records.")

    # Save to uploads directory
    os.makedirs("data/uploads", exist_ok=True)
    saved_path = os.path.join("data/uploads", filename)
    with open(saved_path, "wb") as f:
        f.write(contents)

    # 1. Profile Dataset
    profile = DataProfiler.profile(df, dataset_name=filename, save_to_disk=True)

    # 2. Universal Schema Mapping
    mapped_df, mapping_summary = UniversalSchemaMapper.map_schema(df)

    # 3. Data Readiness & Governance Audit
    readiness_scorecard = DataReadinessAuditor.audit(mapped_df)

    # 4. Optional MongoDB persistence
    db = get_mongo_db()
    if db is not None:
        try:
            records = mapped_df.head(1000).to_dict(orient="records")
            await db.sales.insert_many(records)
        except Exception:
            pass

    return {
        "filename": filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns_detected": list(df.columns),
        "profile_summary": {
            "possible_target_columns": profile.get("possible_target_columns", []),
            "duplicate_count": profile.get("duplicate_count", 0),
            "date_ranges": profile.get("date_ranges", {})
        },
        "schema_mappings": mapping_summary,
        "readiness_scorecard": readiness_scorecard
    }


@router.get("/sample-benchmark")
async def get_sample_benchmark_datasets():
    """Returns metadata on built-in DMart sample files and reference datasets."""
    dmart_path = "data/raw/DMart_sample_data.csv"
    exists = os.path.exists(dmart_path)
    return {
        "available_datasets": [
            {
                "name": "DMart_sample_data.csv",
                "path": dmart_path,
                "exists": exists,
                "provenance": DatasetProvenance.OBSERVED_REAL_DATA,
                "description": "Observed retail transaction log with Date, ProductCategory, UnitPrice, Quantity, Total, FullName."
            },
            {
                "name": "Synthetic_Retail_Simulation_180d",
                "provenance": DatasetProvenance.SIMULATED,
                "description": "180-day multi-store synthetic retail environment with price changes, promotions, and weekend lifts."
            }
        ]
    }
