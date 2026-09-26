"""
Model Drift and Data Distribution Monitoring Engine for UPIAI.
Computes Tracking Signal (TS), Mean Absolute Deviation (MAD), Forecast Bias (MPE),
and statistical distribution drift (Population Stability Index / PSI) across feature inputs and target residuals.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


class DriftStatus:
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL_DRIFT = "CRITICAL_DRIFT"


class ModelDriftDetector:
    """Detects concept drift, covariate shift, and systematic forecast biases."""

    @classmethod
    def calculate_tracking_signal(
        cls, 
        y_true: np.ndarray, 
        y_pred: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calculates Tracking Signal (TS) = Cumulative Forecast Error (CFE) / Mean Absolute Deviation (MAD).
        A healthy forecast maintains TS within [-4.0, +4.0].
        TS > +4 indicates severe systematic under-forecasting (stockout risk).
        TS < -4 indicates severe systematic over-forecasting (overstock risk).
        """
        y_true = np.asarray(y_true, dtype=float).ravel()
        y_pred = np.asarray(y_pred, dtype=float).ravel()

        if len(y_true) == 0 or len(y_pred) == 0:
            return {
                "tracking_signal": 0.0,
                "status": DriftStatus.NORMAL,
                "bias_direction": "NONE",
                "mad": 0.0,
                "cfe": 0.0,
                "mpe_pct": 0.0,
                "explanation": "Insufficient feedback observations."
            }

        errors = y_true - y_pred
        cfe = float(np.sum(errors))
        abs_errors = np.abs(errors)
        mad = float(np.mean(abs_errors))

        # Mean Percentage Error (Bias)
        non_zero_mask = y_true > 0
        if np.any(non_zero_mask):
            mpe = float(np.mean(errors[non_zero_mask] / y_true[non_zero_mask]) * 100.0)
        else:
            mpe = 0.0

        if mad > 1e-5:
            tracking_signal = float(cfe / mad)
        else:
            tracking_signal = 0.0

        # Assess drift status
        if abs(tracking_signal) > 4.5 or abs(mpe) > 35.0:
            status = DriftStatus.CRITICAL_DRIFT
            if tracking_signal > 0:
                bias_dir = "UNDER_FORECASTING"
                expl = f"CRITICAL: Model is consistently under-forecasting demand (TS={tracking_signal:.2f}, Bias={mpe:.1f}%). High risk of stockouts. Automated retraining required."
            else:
                bias_dir = "OVER_FORECASTING"
                expl = f"CRITICAL: Model is consistently over-forecasting demand (TS={tracking_signal:.2f}, Bias={mpe:.1f}%). High risk of excess inventory. Automated retraining required."
        elif abs(tracking_signal) > 3.0 or abs(mpe) > 20.0:
            status = DriftStatus.WARNING
            bias_dir = "MODERATE_BIAS"
            expl = f"WARNING: Forecast tracking signal has reached {tracking_signal:.2f}. Model calibration recommended."
        else:
            status = DriftStatus.NORMAL
            bias_dir = "UNBIASED"
            expl = f"NORMAL: Forecast is well-calibrated (TS={tracking_signal:.2f}, MAD={mad:.2f}, MPE={mpe:.1f}%)."

        return {
            "tracking_signal": round(tracking_signal, 2),
            "status": status,
            "bias_direction": bias_dir,
            "mad": round(mad, 3),
            "cfe": round(cfe, 3),
            "mpe_percentage": round(mpe, 2),
            "sample_count": len(y_true),
            "explanation": expl,
            "retrain_recommended": status == DriftStatus.CRITICAL_DRIFT
        }

    @classmethod
    def calculate_psi(
        cls, 
        expected: np.ndarray, 
        actual: np.ndarray, 
        num_buckets: int = 10
    ) -> Dict[str, Any]:
        """
        Calculates Population Stability Index (PSI) to detect covariate distribution shift.
        PSI < 0.1: No significant change.
        0.1 <= PSI < 0.2: Moderate shift.
        PSI >= 0.2: Significant distribution drift.
        """
        expected = np.asarray(expected, dtype=float).ravel()
        actual = np.asarray(actual, dtype=float).ravel()

        if len(expected) < 10 or len(actual) < 10:
            return {"psi": 0.0, "status": DriftStatus.NORMAL, "explanation": "Insufficient sample size for PSI."}

        # Determine quantiles on expected distribution
        percentiles = np.linspace(0, 100, num_buckets + 1)
        bins = np.percentile(expected, percentiles)
        bins[0] = -np.inf
        bins[-1] = np.inf

        # Calculate frequency in each bin
        expected_counts, _ = np.histogram(expected, bins=bins)
        actual_counts, _ = np.histogram(actual, bins=bins)

        expected_pct = (expected_counts + 1e-4) / len(expected)
        actual_pct = (actual_counts + 1e-4) / len(actual)

        # PSI formula: sum( (actual_pct - expected_pct) * ln(actual_pct / expected_pct) )
        psi_value = float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))

        if psi_value >= 0.20:
            status = DriftStatus.CRITICAL_DRIFT
            expl = f"Significant feature distribution drift detected (PSI={psi_value:.4f} >= 0.20). Input data patterns have changed substantially."
        elif psi_value >= 0.10:
            status = DriftStatus.WARNING
            expl = f"Moderate distribution shift detected (PSI={psi_value:.4f}). Monitor model accuracy closely."
        else:
            status = DriftStatus.NORMAL
            expl = f"Feature distribution is stable (PSI={psi_value:.4f} < 0.10)."

        return {
            "psi": round(psi_value, 4),
            "status": status,
            "explanation": expl
        }
