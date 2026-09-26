"""
Continuous Learning and Feedback Loop Manager for UPIAI.
Ingests realized ground-truth sales, audits prediction accuracy against historical forecasts,
evaluates tracking signals, and triggers automated model retraining when performance decays.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from ai.evaluation.metrics import ForecastingMetrics
from ai.monitoring.drift_detector import ModelDriftDetector, DriftStatus


class FeedbackObservation:
    """Individual forecast vs actual sales record."""
    def __init__(
        self,
        date: str,
        sku: str,
        predicted_units: float,
        actual_units: float,
        model_version: str = "XGBoost_v1.0"
    ):
        self.date = date
        self.sku = sku
        self.predicted_units = float(predicted_units)
        self.actual_units = float(actual_units)
        self.error = self.actual_units - self.predicted_units
        self.abs_error = abs(self.error)
        self.model_version = model_version
        self.logged_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "sku": self.sku,
            "predicted_units": self.predicted_units,
            "actual_units": self.actual_units,
            "error": round(self.error, 2),
            "abs_error": round(self.abs_error, 2),
            "model_version": self.model_version,
            "logged_at": self.logged_at
        }


class FeedbackLoopManager:
    """Manages the continuous evaluation and retraining trigger lifecycle."""

    def __init__(self):
        self.feedback_history: List[FeedbackObservation] = []
        self.retrain_history: List[Dict[str, Any]] = []

    def record_feedback(
        self,
        records: List[Dict[str, Any]],
        model_version: str = "XGBoost_v1.0"
    ) -> Dict[str, Any]:
        """
        Records a batch of ground-truth actual observations vs predictions.
        """
        new_obs = []
        for r in records:
            obs = FeedbackObservation(
                date=str(r.get("date")),
                sku=str(r.get("sku", "GLOBAL")),
                predicted_units=float(r.get("predicted_units", 0.0)),
                actual_units=float(r.get("actual_units", 0.0)),
                model_version=model_version
            )
            self.feedback_history.append(obs)
            new_obs.append(obs)

        # Re-evaluate drift & metrics
        return self.evaluate_current_health()

    def evaluate_current_health(self) -> Dict[str, Any]:
        """Computes comprehensive health, error metrics, and drift tracking signals."""
        if not self.feedback_history:
            return {
                "total_feedback_samples": 0,
                "metrics": {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "r2": 0.0},
                "drift_assessment": {
                    "status": DriftStatus.NORMAL,
                    "tracking_signal": 0.0,
                    "explanation": "No feedback observations recorded yet."
                },
                "retrain_recommended": False
            }

        y_pred = np.array([o.predicted_units for o in self.feedback_history])
        y_true = np.array([o.actual_units for o in self.feedback_history])

        metrics = ForecastingMetrics.calculate_all(y_true, y_pred)
        drift = ModelDriftDetector.calculate_tracking_signal(y_true, y_pred)

        retrain_needed = drift["retrain_recommended"] or (metrics["mape"] > 35.0 and len(y_true) >= 15)

        return {
            "total_feedback_samples": len(self.feedback_history),
            "metrics": metrics,
            "drift_assessment": drift,
            "retrain_recommended": retrain_needed,
            "recent_observations": [o.to_dict() for o in self.feedback_history[-10:]]
        }

    def trigger_model_retraining(self, trigger_reason: str = "SCHEDULED") -> Dict[str, Any]:
        """
        Simulates retraining execution, updates model version, and logs timestamp.
        """
        new_version = f"XGBoost_v{len(self.retrain_history) + 1}.1"
        retrain_event = {
            "retrain_event_id": f"RT-{len(self.retrain_history) + 1:03d}",
            "previous_version": "XGBoost_v1.0" if not self.retrain_history else self.retrain_history[-1]["new_version"],
            "new_version": new_version,
            "trigger_reason": trigger_reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETED_OPTIMAL",
            "samples_used": len(self.feedback_history)
        }
        self.retrain_history.append(retrain_event)
        return retrain_event


# Global singleton manager
feedback_manager = FeedbackLoopManager()
