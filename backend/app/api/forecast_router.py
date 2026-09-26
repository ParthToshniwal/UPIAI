"""
Demand Forecasting & What-If Simulation API Router for UPIAI.
Exposes multi-horizon (7d, 30d, 90d) predictions, model benchmarks,
and price elasticity scenario simulations.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import pandas as pd
import numpy as np

from ai.data.loader import DataLoader
from ai.features.demand_features import DemandFeatureEngineer
from ai.forecasting.forecaster import DemandForecasterModel
from ai.models.baselines import BaselineComparator
from simulation.retail_environment import SyntheticRetailSimulator

router = APIRouter(prefix="/api/v1/forecast", tags=["Demand Forecasting & Simulation"])


class ForecastPredictionRequest(BaseModel):
    horizon_days: int = Field(default=7, ge=1, le=90, description="Forecast horizon in days")
    entity_filter: Optional[str] = Field(default=None, description="Filter forecast for specific product category or SKU")
    sector_key: str = Field(default="GROCERY_SUPERMARKET")
    use_simulation_data: bool = Field(default=False)


class WhatIfSimulationRequest(BaseModel):
    price_adjustment_pct: float = Field(default=0.0, ge=-50.0, le=100.0, description="Price change percentage e.g. +10 or -15")
    marketing_lift_pct: float = Field(default=0.0, ge=0.0, le=150.0, description="Expected marketing traffic volume lift %")
    lead_time_delay_days: int = Field(default=0, ge=0, le=60, description="Supplier disruption delay days")


@router.post("/predict")
async def predict_demand(payload: ForecastPredictionRequest):
    """
    Trains XGBoost on historical sales data and rolls out multi-horizon autoregressive forecast.
    """
    if payload.use_simulation_data:
        df = SyntheticRetailSimulator.generate_environment(days=120, store_count=1)
    else:
        dmart_path = "data/raw/DMart_sample_data.csv"
        if not pd.io.common.file_exists(dmart_path):
            df = SyntheticRetailSimulator.generate_environment(days=90, store_count=1)
        else:
            df, _ = DataLoader.load(dmart_path)

    # 1. Feature Engineering
    features_df, meta = DemandFeatureEngineer.create_features(
        df,
        entity_key="product_category" if "product_category" in df.columns or "ProductCategory" in df.columns else "product_id"
    )

    # 2. Train Forecaster
    forecaster = DemandForecasterModel(horizon_days=payload.horizon_days)
    training_summary = forecaster.train(features_df)

    # 3. Predict Trajectories
    entity_col = meta["entity_key"]
    unique_entities = features_df[entity_col].unique()

    if payload.entity_filter:
        unique_entities = [e for e in unique_entities if str(e).lower() == payload.entity_filter.lower()]

    results = []
    for ent in unique_entities:
        ent_history = features_df[features_df[entity_col] == ent]
        fc = forecaster.forecast_horizon(
            recent_history_df=ent_history,
            entity_name=str(ent),
            horizon_days=payload.horizon_days
        )
        results.append(fc)

    return {
        "horizon_days": payload.horizon_days,
        "total_entities_forecasted": len(results),
        "model_training_metrics": training_summary["training_metrics"],
        "residual_std": training_summary["residual_std"],
        "forecasts": results
    }


@router.post("/simulate")
async def run_what_if_simulation(payload: WhatIfSimulationRequest):
    """
    Simulates price elasticity demand shifts, marketing campaign lifts, and supplier delay impacts.
    """
    df = SyntheticRetailSimulator.generate_environment(days=60, store_count=1)
    simulation_result = SyntheticRetailSimulator.simulate_what_if_scenario(
        base_df=df,
        price_adjustment_pct=payload.price_adjustment_pct,
        marketing_lift_pct=payload.marketing_lift_pct,
        supplier_lead_time_delay_days=payload.lead_time_delay_days
    )
    return simulation_result


@router.get("/benchmark")
async def run_model_benchmarks():
    """
    Evaluates chronological test set performance across Naive, Moving Average,
    Linear Regression, Random Forest, and XGBoost models.
    """
    df = SyntheticRetailSimulator.generate_environment(days=90, store_count=1)
    features_df, _ = DemandFeatureEngineer.create_features(df, entity_key="product_category", date_col="date")
    benchmark_results = BaselineComparator.evaluate_all_models(features_df)
    return benchmark_results
