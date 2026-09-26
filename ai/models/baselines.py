"""
Baseline and Machine Learning Models for UPIAI Demand Forecasting.
Provides chronological time-series splitting, Naive, Moving Average, Linear Regression,
Random Forest, and XGBoost training with cross-model metric comparison.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

from ai.evaluation.metrics import ForecastingMetrics


class TimeSeriesSplitter:
    """Performs strict chronological splitting without data leakage or random shuffling."""

    @staticmethod
    def chronological_split(
        df: pd.DataFrame, 
        train_ratio: float = 0.70, 
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        date_col: str = "date_dt"
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Splits time series into Train (70%), Validation (15%), and Test (15%) splits."""
        if date_col in df.columns:
            sorted_df = df.sort_values(date_col).reset_index(drop=True)
        else:
            sorted_df = df.copy()

        n = len(sorted_df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train_df = sorted_df.iloc[:train_end].copy()
        val_df = sorted_df.iloc[train_end:val_end].copy()
        test_df = sorted_df.iloc[val_end:].copy()

        return train_df, val_df, test_df


class BaselineComparator:
    """Trains and compares multiple baseline and ML forecasting models on chronological test splits."""

    FEATURE_COLS = [
        'day_of_week', 'week_of_year', 'month', 'quarter', 'is_weekend', 'is_festival',
        'sales_lag_1', 'sales_lag_7', 'sales_lag_14', 'sales_lag_28',
        'rolling_mean_7', 'rolling_mean_14', 'rolling_mean_30',
        'rolling_std_7', 'rolling_std_30', 'sales_growth', 'price_change', 'is_promotion'
    ]

    @classmethod
    def evaluate_all_models(
        cls, 
        df_features: pd.DataFrame, 
        target_col: str = "units_sold"
    ) -> Dict[str, Any]:
        """
        Runs full benchmark suite across all models on the test set.
        """
        train_df, val_df, test_df = TimeSeriesSplitter.chronological_split(df_features)

        if len(train_df) < 5 or len(test_df) == 0:
            raise ValueError("Insufficient rows for train/val/test chronological partition.")

        available_features = [c for c in cls.FEATURE_COLS if c in df_features.columns]

        X_train = train_df[available_features].values
        y_train = train_df[target_col].values

        X_val = val_df[available_features].values
        y_val = val_df[target_col].values

        X_test = test_df[available_features].values
        y_test = test_df[target_col].values

        results = {}

        # -------------------------------------------------------------
        # 1. Naive Model (Lag-1 Prediction)
        # -------------------------------------------------------------
        if 'sales_lag_1' in test_df.columns:
            y_pred_naive = test_df['sales_lag_1'].values
        else:
            y_pred_naive = np.full_like(y_test, np.mean(y_train))
        results["Naive_Lag1"] = ForecastingMetrics.calculate_all(y_test, y_pred_naive)

        # -------------------------------------------------------------
        # 2. Moving Average (7-Day Rolling Mean)
        # -------------------------------------------------------------
        if 'rolling_mean_7' in test_df.columns:
            y_pred_ma7 = test_df['rolling_mean_7'].values
        else:
            y_pred_ma7 = np.full_like(y_test, np.mean(y_train))
        results["Moving_Average_7d"] = ForecastingMetrics.calculate_all(y_test, y_pred_ma7)

        # -------------------------------------------------------------
        # 3. Linear Regression
        # -------------------------------------------------------------
        try:
            lr = LinearRegression()
            lr.fit(X_train, y_train)
            y_pred_lr = np.clip(lr.predict(X_test), 0, None)
            results["Linear_Regression"] = ForecastingMetrics.calculate_all(y_test, y_pred_lr)
        except Exception as e:
            results["Linear_Regression"] = {"error": str(e)}

        # -------------------------------------------------------------
        # 4. Random Forest Regressor
        # -------------------------------------------------------------
        try:
            rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
            rf.fit(X_train, y_train)
            y_pred_rf = np.clip(rf.predict(X_test), 0, None)
            results["Random_Forest"] = ForecastingMetrics.calculate_all(y_test, y_pred_rf)
        except Exception as e:
            results["Random_Forest"] = {"error": str(e)}

        # -------------------------------------------------------------
        # 5. XGBoost Regressor
        # -------------------------------------------------------------
        try:
            xgb = XGBRegressor(
                n_estimators=120,
                max_depth=4,
                learning_rate=0.06,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
                verbosity=0
            )
            xgb.fit(X_train, y_train)
            y_pred_xgb = np.clip(xgb.predict(X_test), 0, None)
            results["XGBoost_Universal"] = ForecastingMetrics.calculate_all(y_test, y_pred_xgb)
        except Exception as e:
            results["XGBoost_Universal"] = {"error": str(e)}

        # Rank models by test RMSE
        ranked = sorted(
            [{"model": k, **v} for k, v in results.items() if "rmse" in v],
            key=lambda x: x["rmse"]
        )

        return {
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "features_used": available_features,
            "best_model": ranked[0]["model"] if ranked else "None",
            "model_rankings": ranked,
            "detailed_metrics": results
        }
