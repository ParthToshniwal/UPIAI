"""
Multi-Horizon Demand Forecaster for UPIAI.
Implements iterative multi-step autoregressive 7-day and 30-day demand forecasting,
residual uncertainty estimation, and seasonal decomposition.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ai.features.demand_features import DemandFeatureEngineer, FESTIVAL_CALENDAR
from ai.evaluation.metrics import ForecastingMetrics


class DemandForecasterModel:
    """Production Multi-Horizon Forecaster powered by XGBoost with autoregressive rollout."""

    def __init__(self, horizon_days: int = 7):
        self.horizon_days = horizon_days
        self.model: Optional[XGBRegressor] = None
        self.feature_cols: List[str] = []
        self.residual_std: float = 1.0
        self.is_trained: bool = False

    def train(self, df_features: pd.DataFrame, target_col: str = "units_sold") -> Dict[str, Any]:
        """Trains the primary XGBoost forecaster and computes residual variance for confidence bounds."""
        self.feature_cols = [
            'day_of_week', 'week_of_year', 'month', 'quarter', 'is_weekend', 'is_festival',
            'sales_lag_1', 'sales_lag_7', 'sales_lag_14', 'sales_lag_28',
            'rolling_mean_7', 'rolling_mean_14', 'rolling_mean_30',
            'rolling_std_7', 'rolling_std_30', 'sales_growth', 'price_change', 'is_promotion'
        ]
        self.feature_cols = [c for c in self.feature_cols if c in df_features.columns]

        X = df_features[self.feature_cols].values
        y = df_features[target_col].values

        self.model = XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.07,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            verbosity=0
        )
        self.model.fit(X, y)
        self.is_trained = True

        y_pred = np.clip(self.model.predict(X), 0, None)
        self.residual_std = max(0.5, float(np.std(y - y_pred)))
        metrics = ForecastingMetrics.calculate_all(y, y_pred)

        return {
            "training_metrics": metrics,
            "residual_std": round(self.residual_std, 4),
            "samples_trained": len(X),
            "features_used": self.feature_cols
        }

    def forecast_horizon(
        self, 
        recent_history_df: pd.DataFrame, 
        entity_name: str,
        horizon_days: int = 7,
        unit_price: float = 100.0
    ) -> Dict[str, Any]:
        """
        Rolls out an autoregressive prediction trajectory for `horizon_days` into the future.
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model must be trained before forecasting.")

        recent_df = recent_history_df.sort_values('date_dt').copy()
        if recent_df.empty:
            raise ValueError(f"No historical records provided for entity '{entity_name}'.")

        last_date = pd.to_datetime(recent_df['date_dt'].max())
        history_sales = list(recent_df['units_sold'].values)

        daily_predictions = []
        total_forecast_units = 0.0

        for step in range(1, horizon_days + 1):
            fc_dt = last_date + pd.Timedelta(days=step)
            dow = fc_dt.dayofweek
            woy = fc_dt.isocalendar().week
            m = fc_dt.month
            q = (m - 1) // 3 + 1
            is_wk = 1 if dow in [5, 6] else 0

            # Festival check
            is_fest = 0
            for _, (fm, fd) in FESTIVAL_CALENDAR.items():
                if m == fm and abs(fc_dt.day - fd) <= 4:
                    is_fest = 1
                    break

            lag_1 = history_sales[-1] if len(history_sales) >= 1 else 0.0
            lag_7 = history_sales[-7] if len(history_sales) >= 7 else lag_1
            lag_14 = history_sales[-14] if len(history_sales) >= 14 else lag_1
            lag_28 = history_sales[-28] if len(history_sales) >= 28 else lag_1

            roll_7 = float(np.mean(history_sales[-7:])) if len(history_sales) >= 7 else lag_1
            roll_14 = float(np.mean(history_sales[-14:])) if len(history_sales) >= 14 else roll_7
            roll_30 = float(np.mean(history_sales[-30:])) if len(history_sales) >= 30 else roll_14
            roll_std_7 = float(np.std(history_sales[-7:])) if len(history_sales) >= 7 else 0.5
            roll_std_30 = float(np.std(history_sales[-30:])) if len(history_sales) >= 30 else 1.0

            growth = (roll_7 - roll_14) / (roll_14 + 1e-4)

            feature_dict = {
                'day_of_week': dow,
                'week_of_year': int(woy),
                'month': m,
                'quarter': q,
                'is_weekend': is_wk,
                'is_festival': is_fest,
                'sales_lag_1': lag_1,
                'sales_lag_7': lag_7,
                'sales_lag_14': lag_14,
                'sales_lag_28': lag_28,
                'rolling_mean_7': roll_7,
                'rolling_mean_14': roll_14,
                'rolling_mean_30': roll_30,
                'rolling_std_7': roll_std_7,
                'rolling_std_30': roll_std_30,
                'sales_growth': growth,
                'price_change': 0.0,
                'is_promotion': 0
            }

            step_vector = np.array([[feature_dict[col] for col in self.feature_cols]])
            pred_units = float(np.clip(self.model.predict(step_vector)[0], 0, None))

            # Apply slight weekend organic lift if detected
            if is_wk:
                pred_units *= 1.12

            history_sales.append(pred_units)
            total_forecast_units += pred_units

            lower_90 = max(0.0, pred_units - (1.645 * self.residual_std))
            upper_90 = pred_units + (1.645 * self.residual_std)

            daily_predictions.append({
                "day_offset": step,
                "date": fc_dt.strftime("%Y-%m-%d"),
                "predicted_units": round(pred_units, 2),
                "lower_bound_90": round(lower_90, 2),
                "upper_bound_90": round(upper_90, 2)
            })

        return {
            "entity": entity_name,
            "horizon_days": horizon_days,
            "total_predicted_units": round(total_forecast_units, 2),
            "projected_revenue": round(total_forecast_units * unit_price, 2),
            "daily_velocity": round(total_forecast_units / max(1, horizon_days), 2),
            "daily_trajectories": daily_predictions
        }
