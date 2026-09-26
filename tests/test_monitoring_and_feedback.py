"""
Unit tests for Model Drift Detection, Tracking Signal, and Feedback Loop Manager.
"""

import pytest
import numpy as np
from ai.monitoring.drift_detector import ModelDriftDetector, DriftStatus
from ai.monitoring.feedback_loop import FeedbackLoopManager


def test_tracking_signal_unbiased():
    y_true = np.array([10.0, 12.0, 15.0, 11.0, 14.0, 13.0, 12.0])
    y_pred = np.array([10.2, 11.8, 14.9, 11.2, 13.8, 13.1, 12.1])

    ts_res = ModelDriftDetector.calculate_tracking_signal(y_true, y_pred)
    assert ts_res["status"] == DriftStatus.NORMAL
    assert abs(ts_res["tracking_signal"]) < 3.0
    assert ts_res["retrain_recommended"] is False


def test_tracking_signal_critical_under_forecasting():
    # Model consistently under-predicts actual demand
    y_true = np.array([25.0, 30.0, 28.0, 35.0, 40.0, 38.0, 42.0])
    y_pred = np.array([10.0, 12.0, 11.0, 14.0, 15.0, 13.0, 12.0])

    ts_res = ModelDriftDetector.calculate_tracking_signal(y_true, y_pred)
    assert ts_res["status"] == DriftStatus.CRITICAL_DRIFT
    assert ts_res["bias_direction"] == "UNDER_FORECASTING"
    assert ts_res["retrain_recommended"] is True


def test_psi_distribution_shift():
    expected = np.random.normal(50, 10, 500)
    actual_drifted = np.random.normal(90, 25, 500)

    psi_res = ModelDriftDetector.calculate_psi(expected, actual_drifted)
    assert psi_res["status"] == DriftStatus.CRITICAL_DRIFT
    assert psi_res["psi"] >= 0.20


def test_feedback_loop_manager():
    mgr = FeedbackLoopManager()
    records = [
        {"date": "2026-09-01", "sku": "SKU-001", "predicted_units": 10.0, "actual_units": 11.0},
        {"date": "2026-09-02", "sku": "SKU-001", "predicted_units": 12.0, "actual_units": 12.5}
    ]
    eval_res = mgr.record_feedback(records)
    assert eval_res["total_feedback_samples"] == 2
    assert "metrics" in eval_res

    retrain_event = mgr.trigger_model_retraining(trigger_reason="TEST_TRIGGER")
    assert retrain_event["status"] == "COMPLETED_OPTIMAL"
    assert "new_version" in retrain_event
