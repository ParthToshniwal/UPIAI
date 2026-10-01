"""
Data Readiness & Provenance Engine Router.
Exposes endpoints for auditing dataset integrity, calculating confidence readiness scores,
and evaluating structural risk factors for DMart datasets before triggering ML forecasting.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File
import pandas as pd
import io

try:
    from app.models.schemas import ReadinessScorecardResponse, ReadinessAuditRequest
    from app.ml.readiness import DataReadinessEngine
    from app.database import turso_db
except ImportError:
    from backend.app.models.schemas import ReadinessScorecardResponse, ReadinessAuditRequest
    from backend.app.ml.readiness import DataReadinessEngine
    from backend.app.database import turso_db

router = APIRouter(prefix="/api/v1/readiness", tags=["Data Readiness & Provenance"])


@router.get("", response_model=ReadinessScorecardResponse)
@router.get("/", response_model=ReadinessScorecardResponse)
async def get_active_data_readiness():
    """
    Audits active DMart database records and returns a full governance & readiness scorecard.
    """
    txns = turso_db.get_all_transactions(limit=5000)
    if not txns:
        return DataReadinessEngine._generate_empty_scorecard("No DMart records found in Turso database.")
    scorecard = DataReadinessEngine.audit_dataset(txns)
    return scorecard


@router.post("/audit", response_model=ReadinessScorecardResponse)
async def audit_dataset_health(payload: Optional[ReadinessAuditRequest] = None):
    """
    Audits a provided payload dataset or the active DMart database records.
    """
    if payload and payload.dataset and len(payload.dataset) > 0:
        scorecard = DataReadinessEngine.audit_dataset(payload.dataset)
        return scorecard

    txns = turso_db.get_all_transactions(limit=5000)
    scorecard = DataReadinessEngine.audit_dataset(txns)
    return scorecard


@router.post("/upload-csv", response_model=ReadinessScorecardResponse)
async def audit_csv_file(file: UploadFile = File(...)):
    """
    Accepts a raw CSV file upload from the client dashboard, parses headers,
    and returns a full health scorecard with provenance disclosures.
    """
    if not file.filename.endswith(('.csv', '.txt')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .csv file.")

    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='replace')))
        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")
        
        scorecard = DataReadinessEngine.audit_dataset(df)
        return scorecard
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse CSV file: {str(exc)}")
