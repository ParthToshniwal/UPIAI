"""
Integration test for Feature Engineering, Model Training, Metrics, and Multi-Horizon 7-Day Forecasting.
"""

import pytest
import pandas as pd
from ai.data.loader import DataLoader
from ai.features.demand_features import DemandFeatureEngineer
from ai.models.baselines import BaselineComparator, TimeSeriesSplitter
from ai.forecasting.forecaster import DemandForecasterModel
from ai.evaluation.metrics import ForecastingMetrics
from ai.decision_engine import UPIDecisionEngine
from simulation.retail_environment import SyntheticRetailSimulator


def test_feature_engineering_and_forecasting_pipeline():
    # 1. Generate 90-day retail environment
    df_sim = SyntheticRetailSimulator.generate_environment(days=90, store_count=1)
    assert len(df_sim) > 0

    # 2. Engineer features
    features_df, meta = DemandFeatureEngineer.create_features(
        df_sim, 
        entity_key="product_category",
        date_col="date"
    )
    assert "sales_lag_1" in features_df.columns
    assert "rolling_mean_7" in features_df.columns
    assert "day_of_week" in features_df.columns

    # 3. Model Benchmark comparison
    benchmark = BaselineComparator.evaluate_all_models(features_df)
    assert "XGBoost_Universal" in benchmark["detailed_metrics"]
    assert benchmark["train_samples"] > 0
    assert benchmark["test_samples"] > 0

    # 4. Train 7-day Multi-Horizon Forecaster
    forecaster = DemandForecasterModel(horizon_days=7)
    train_res = forecaster.train(features_df)
    assert train_res["training_metrics"]["mae"] >= 0.0

    # 5. Forecast 7 days for a specific category
    sample_cat = features_df["product_category"].iloc[0]
    cat_df = features_df[features_df["product_category"] == sample_cat]
    fc = forecaster.forecast_horizon(cat_df, entity_name=sample_cat, horizon_days=7)

    assert fc["horizon_days"] == 7
    assert len(fc["daily_trajectories"]) == 7
    assert fc["total_predicted_units"] > 0.0
    assert fc["daily_velocity"] > 0.0


def test_master_decision_engine():
    df_sim = SyntheticRetailSimulator.generate_environment(days=60, store_count=1)
    result = UPIDecisionEngine.process_business_dataset(
        df_raw=df_sim,
        dataset_name="Retail Simulation Test",
        forecast_horizon_days=7
    )

    assert result["readiness_scorecard"]["can_proceed_to_forecast"] is True
    assert len(result["demand_forecasts"]) > 0
    assert len(result["inventory_recommendations"]) > 0
    assert result["executive_kpis"]["total_projected_units"] > 0
