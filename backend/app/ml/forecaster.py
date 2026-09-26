"""
Demand Forecasting and Stockout Risk Intelligence Engine.
Combines XGBoost autoregressive time-series regression with statistical fallbacks,
rolling feature pipelines, stockout probability estimation, and dynamic PO recommendations.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

try:
    from xgboost import XGBRegressor
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

from app.models.schemas import (
    ForecastHorizonPrediction,
    StockoutRiskAssessment,
    ReorderRecommendation,
    SKUForecastDetail,
    ForecastResponse
)


class DemandForecaster:
    """End-to-end multi-horizon demand forecasting and supply risk engine."""

    def __init__(self, horizon_days: int = 30):
        self.horizon_days = horizon_days

    @staticmethod
    def _create_features(series_df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineers temporal, calendar, lag, and rolling statistics from aggregated daily sales.
        """
        df = series_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        # Calendar features
        df['dayofweek'] = df['date'].dt.dayofweek
        df['day'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

        # Lag features
        for lag in [1, 2, 7, 14]:
            df[f'lag_{lag}'] = df['units_sold'].shift(lag)

        # Rolling statistics
        df['rolling_mean_7'] = df['units_sold'].shift(1).rolling(window=7, min_periods=1).mean()
        df['rolling_std_7'] = df['units_sold'].shift(1).rolling(window=7, min_periods=1).std().fillna(0)
        df['rolling_mean_14'] = df['units_sold'].shift(1).rolling(window=14, min_periods=1).mean()
        df['rolling_max_14'] = df['units_sold'].shift(1).rolling(window=14, min_periods=1).max()

        # Handle initial NaN lags via backfill/bfill
        df = df.bfill().fillna(0)
        return df

    def forecast_sku(
        self,
        sku: str,
        product_meta: Dict[str, Any],
        historical_sales_df: pd.DataFrame
    ) -> SKUForecastDetail:
        """
        Generates 7-day and 30-day forecast curves for a single SKU with risk scoring.
        """
        product_name = product_meta.get("name", sku)
        category = product_meta.get("category", "General")
        unit_cost = float(product_meta.get("unit_cost", 50.0))
        unit_price = float(product_meta.get("unit_price", 85.0))
        current_stock = int(product_meta.get("current_stock", 0))
        on_order = int(product_meta.get("on_order_stock", 0))
        lead_time_days = int(product_meta.get("lead_time_days", 14))
        supplier_id = product_meta.get("supplier_id", "SUP-DEFAULT")
        supplier_name = product_meta.get("supplier_name", "Primary Distributor")

        # Filter sales for target SKU
        sku_sales = historical_sales_df[historical_sales_df['sku'] == sku].copy()

        daily_trajectories: List[ForecastHorizonPrediction] = []
        forecast_7d_total = 0.0
        forecast_30d_total = 0.0
        daily_average_velocity = 0.0

        today = datetime.utcnow().date()

        if len(sku_sales) >= 10 and XGB_AVAILABLE:
            # Aggregate by date if multiple entries per day
            daily_agg = sku_sales.groupby('date')['units_sold'].sum().reset_index()
            daily_agg['date'] = pd.to_datetime(daily_agg['date'])
            daily_agg = daily_agg.sort_values('date').reset_index(drop=True)

            # Ensure continuous date index by reindexing
            full_idx = pd.date_range(start=daily_agg['date'].min(), end=daily_agg['date'].max(), freq='D')
            daily_agg = daily_agg.set_index('date').reindex(full_idx, fill_value=0).rename_axis('date').reset_index()

            feat_df = self._create_features(daily_agg)
            
            feature_cols = [
                'dayofweek', 'day', 'month', 'is_weekend',
                'lag_1', 'lag_2', 'lag_7', 'lag_14',
                'rolling_mean_7', 'rolling_std_7', 'rolling_mean_14', 'rolling_max_14'
            ]

            X_train = feat_df[feature_cols].values
            y_train = feat_df['units_sold'].values

            try:
                model = XGBRegressor(
                    n_estimators=60,
                    max_depth=3,
                    learning_rate=0.08,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    random_state=42,
                    verbosity=0
                )
                model.fit(X_train, y_train)
                
                # Compute residual standard deviation for confidence interval
                y_pred_train = model.predict(X_train)
                residual_std = max(1.0, float(np.std(y_train - y_pred_train)))

                # Autoregressive multi-step rollout
                history_window = list(daily_agg['units_sold'].values[-20:])
                last_date = daily_agg['date'].max()

                for step in range(1, self.horizon_days + 1):
                    fc_date = last_date + pd.Timedelta(days=step)
                    dow = fc_date.dayofweek
                    d = fc_date.day
                    m = fc_date.month
                    is_wk = 1 if dow in [5, 6] else 0

                    lag_1 = history_window[-1] if len(history_window) >= 1 else 0
                    lag_2 = history_window[-2] if len(history_window) >= 2 else 0
                    lag_7 = history_window[-7] if len(history_window) >= 7 else lag_1
                    lag_14 = history_window[-14] if len(history_window) >= 14 else lag_1

                    roll_7 = float(np.mean(history_window[-7:])) if len(history_window) >= 7 else lag_1
                    roll_std = float(np.std(history_window[-7:])) if len(history_window) >= 7 else 0.5
                    roll_14 = float(np.mean(history_window[-14:])) if len(history_window) >= 14 else roll_7
                    roll_max = float(np.max(history_window[-14:])) if len(history_window) >= 14 else roll_7

                    step_vector = np.array([[
                        dow, d, m, is_wk,
                        lag_1, lag_2, lag_7, lag_14,
                        roll_7, roll_std, roll_14, roll_max
                    ]])

                    pred_val = max(0.0, float(model.predict(step_vector)[0]))
                    # Slight organic jitter / weekend pattern adjustment
                    if is_wk:
                        pred_val *= 1.15

                    history_window.append(pred_val)

                    lower_90 = max(0.0, pred_val - (1.645 * residual_std))
                    upper_90 = pred_val + (1.645 * residual_std)

                    if step <= 7:
                        forecast_7d_total += pred_val
                    forecast_30d_total += pred_val

                    daily_trajectories.append(
                        ForecastHorizonPrediction(
                            day_offset=step,
                            forecast_date=(today + timedelta(days=step)).strftime("%Y-%m-%d"),
                            predicted_units=round(pred_val, 2),
                            lower_bound_90=round(lower_90, 2),
                            upper_bound_90=round(upper_90, 2)
                        )
                    )
            except Exception:
                # Fallback to Statistical Moving Average
                daily_trajectories, forecast_7d_total, forecast_30d_total = self._statistical_forecast_fallback(
                    sku_sales, today, self.horizon_days
                )
        else:
            # Statistical fallback
            daily_trajectories, forecast_7d_total, forecast_30d_total = self._statistical_forecast_fallback(
                sku_sales, today, self.horizon_days
            )

        daily_average_velocity = round(forecast_30d_total / max(1, self.horizon_days), 2)
        forecast_7d_total = round(forecast_7d_total, 1)
        forecast_30d_total = round(forecast_30d_total, 1)

        # -------------------------------------------------------------
        # Stockout Risk & Depletion Analytics
        # -------------------------------------------------------------
        velocity_safe = max(0.05, daily_average_velocity)
        days_of_supply = round(current_stock / velocity_safe, 1)

        # Compute projected stockout calendar date
        stockout_date = None
        if days_of_supply <= 60:
            stockout_date = (today + timedelta(days=int(days_of_supply))).strftime("%Y-%m-%d")

        # Stockout probability calculation
        if days_of_supply <= lead_time_days:
            risk_level = "CRITICAL"
            stockout_prob = min(99.0, 85.0 + (lead_time_days - days_of_supply) * 2.5)
        elif days_of_supply <= (lead_time_days * 1.5):
            risk_level = "WARNING"
            stockout_prob = round(45.0 + ((lead_time_days * 1.5 - days_of_supply) / (lead_time_days * 0.5)) * 35.0, 1)
        elif days_of_supply > 65:
            risk_level = "OVERSTOCKED"
            stockout_prob = 2.0
        else:
            risk_level = "OPTIMAL"
            stockout_prob = round(max(5.0, 25.0 - (days_of_supply - lead_time_days)), 1)

        revenue_at_risk = 0.0
        if days_of_supply < 30:
            unmet_days = 30 - days_of_supply
            revenue_at_risk = round(unmet_days * daily_average_velocity * unit_price, 2)

        risk_assessment = StockoutRiskAssessment(
            risk_level=risk_level,
            stockout_probability_pct=stockout_prob,
            estimated_days_of_supply=days_of_supply,
            projected_stockout_date=stockout_date,
            estimated_revenue_at_risk=revenue_at_risk
        )

        # -------------------------------------------------------------
        # PO Reorder Recommendation Engine
        # -------------------------------------------------------------
        # Safety Stock formula: Z * sqrt(LeadTime) * StdDev
        safety_stock = int(round(1.65 * np.sqrt(lead_time_days) * (velocity_safe * 0.35)))
        safety_stock = max(5, safety_stock)
        reorder_point = int(round((daily_average_velocity * lead_time_days) + safety_stock))

        # Target inventory covers Lead Time + 30-day replenishment cycle
        target_inventory = int(round((daily_average_velocity * (lead_time_days + 30)) + safety_stock))
        effective_inventory = current_stock + on_order

        if effective_inventory <= reorder_point:
            order_qty = max(10, target_inventory - effective_inventory)
            if days_of_supply <= lead_time_days:
                urgency = "IMMEDIATE"
                rationale = f"Stock level ({current_stock}) below lead time consumption ({int(lead_time_days * daily_average_velocity)} units). Stockout expected in {days_of_supply} days."
            else:
                urgency = "PLAN_THIS_WEEK"
                rationale = f"Inventory ({current_stock}) has breached reorder threshold ({reorder_point} units). Reorder to maintain safety buffer."
        else:
            order_qty = 0
            if days_of_supply > 60:
                urgency = "NO_ACTION"
                rationale = f"Healthy inventory depth ({days_of_supply} days of supply). Overstock alert: monitor aging capital."
            else:
                urgency = "NORMAL"
                rationale = f"Current stock is sufficient ({days_of_supply} days remaining). Above reorder trigger ({reorder_point})."

        reorder_rec = ReorderRecommendation(
            sku=sku,
            product_name=product_name,
            category=category,
            current_stock=current_stock,
            on_order=on_order,
            lead_time_days=lead_time_days,
            reorder_point=reorder_point,
            safety_stock=safety_stock,
            recommended_order_quantity=order_qty,
            estimated_order_cost=round(order_qty * unit_cost, 2),
            preferred_supplier_id=supplier_id,
            preferred_supplier_name=supplier_name,
            urgency=urgency,
            rationale=rationale
        )

        return SKUForecastDetail(
            sku=sku,
            product_name=product_name,
            category=category,
            current_stock=current_stock,
            unit_cost=unit_cost,
            unit_price=unit_price,
            forecast_7d_total=forecast_7d_total,
            forecast_30d_total=forecast_30d_total,
            daily_average_velocity=daily_average_velocity,
            risk_assessment=risk_assessment,
            reorder_recommendation=reorder_rec,
            daily_trajectory_30d=daily_trajectories
        )

    def _statistical_forecast_fallback(
        self,
        sku_sales: pd.DataFrame,
        today: Any,
        horizon_days: int
    ) -> Tuple[List[ForecastHorizonPrediction], float, float]:
        """
        Provides a smooth moving average and day-of-week seasonality forecast when history is sparse.
        """
        trajectories = []
        f7 = 0.0
        f30 = 0.0

        if not sku_sales.empty and 'units_sold' in sku_sales.columns:
            base_mean = max(1.0, float(sku_sales['units_sold'].mean()))
            base_std = max(0.5, float(sku_sales['units_sold'].std()) if len(sku_sales) > 1 else 1.0)
        else:
            base_mean = 8.5
            base_std = 2.0

        for step in range(1, horizon_days + 1):
            fc_date = today + timedelta(days=step)
            dow = fc_date.weekday()
            # Slight lift on Friday/Saturday
            multiplier = 1.25 if dow in [4, 5] else 0.95
            pred_val = round(max(0.5, base_mean * multiplier + (np.sin(step / 3.0) * 0.8)), 2)

            lower_90 = max(0.0, round(pred_val - (1.645 * base_std), 2))
            upper_90 = round(pred_val + (1.645 * base_std), 2)

            if step <= 7:
                f7 += pred_val
            f30 += pred_val

            trajectories.append(
                ForecastHorizonPrediction(
                    day_offset=step,
                    forecast_date=fc_date.strftime("%Y-%m-%d"),
                    predicted_units=pred_val,
                    lower_bound_90=lower_90,
                    upper_bound_90=upper_90
                )
            )

        return trajectories, f7, f30
