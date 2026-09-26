"""
Model Monitoring and Continuous Feedback Loop API Router for UPIAI.
Tracks prediction accuracy drift, Tracking Signal (TS), Mean Absolute Deviation (MAD),
and manages automated retraining triggers.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from ai.monitoring.feedback_loop import feedback_manager

router = APIRouter(prefix="/api/v1/monitoring", tags=["Model Monitoring & Feedback Loop"])


class FeedbackSubmissionItem(BaseModel):
    date: str = Field(..., example="2026-09-20")
    sku: str = Field(..., example="TECH-4090-GPU")
    predicted_units: float = Field(..., ge=0.0)
    actual_units: float = Field(..., ge=0.0)


class FeedbackBatchRequest(BaseModel):
    observations: List[FeedbackSubmissionItem]
    model_version: Optional[str] = "XGBoost_v1.0"


class RetrainTriggerRequest(BaseModel):
    trigger_reason: Optional[str] = "MANUAL_DASHBOARD_TRIGGER"


@router.get("/health")
async def get_model_health_and_drift():
    """
    Returns current model accuracy, error metrics (MAE, RMSE, MAPE),
    Tracking Signal (TS), bias direction, and retraining recommendations.
    """
    health = feedback_manager.evaluate_current_health()
    return health


@router.post("/feedback")
async def submit_actual_sales_feedback(payload: FeedbackBatchRequest):
    """
    Submits realized sales observations to audit historical forecast accuracy.
    Updates rolling tracking signal and flags systematic drift.
    """
    obs_dicts = [item.model_dump() for item in payload.observations]
    evaluation = feedback_manager.record_feedback(obs_dicts, model_version=payload.model_version or "XGBoost_v1.0")
    return {
        "status": "FEEDBACK_LOGGED",
        "new_observations_count": len(obs_dicts),
        "updated_health_evaluation": evaluation
    }


@router.post("/retrain")
async def trigger_retraining(payload: RetrainTriggerRequest):
    """
    Triggers an automated retraining event, updating the active model version.
    """
    event = feedback_manager.trigger_model_retraining(trigger_reason=payload.trigger_reason or "MANUAL_TRIGGER")
    return {
        "status": "RETRAINING_SUCCESSFUL",
        "retrain_event": event
    }
