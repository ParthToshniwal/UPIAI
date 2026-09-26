"""
Model Evaluation Metrics for UPIAI.
Computes mathematically verified metrics for regression & demand forecasting models:
MAE, RMSE, MAPE, SMAPE, and R2 with zero-division guards.
"""

from typing import Dict, Any
import numpy as np


class ForecastingMetrics:
    """Calculates standard regression and time-series evaluation metrics."""

    @staticmethod
    def calculate_all(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calculates MAE, RMSE, MAPE, SMAPE, and R2 on numpy arrays.
        """
        y_true = np.asarray(y_true, dtype=float).ravel()
        y_pred = np.asarray(y_pred, dtype=float).ravel()

        if len(y_true) == 0 or len(y_pred) == 0:
            return {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "smape": 0.0, "r2": 0.0}

        # Prevent negative predictions in demand forecasting
        y_pred_clipped = np.clip(y_pred, 0, None)

        # MAE
        mae = float(np.mean(np.abs(y_true - y_pred_clipped)))

        # RMSE
        rmse = float(np.sqrt(np.mean((y_true - y_pred_clipped) ** 2)))

        # MAPE (guarding against divide-by-zero)
        mask = y_true > 0
        if np.any(mask):
            mape = float(np.mean(np.abs((y_true[mask] - y_pred_clipped[mask]) / y_true[mask])) * 100.0)
        else:
            mape = 0.0

        # SMAPE: 100 * mean( 2 * |y_true - y_pred| / (|y_true| + |y_pred| + eps) )
        denominator = (np.abs(y_true) + np.abs(y_pred_clipped)) / 2.0 + 1e-6
        smape = float(np.mean(np.abs(y_true - y_pred_clipped) / denominator) * 100.0)

        # R2
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        ss_res = np.sum((y_true - y_pred_clipped) ** 2)
        if ss_tot > 1e-6:
            r2 = float(1.0 - (ss_res / ss_tot))
        else:
            r2 = 1.0 if ss_res < 1e-6 else 0.0

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": round(mape, 2),
            "smape": round(smape, 2),
            "r2": round(r2, 4)
        }
