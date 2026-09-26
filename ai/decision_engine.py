"""
Unified AI Decision & Inventory Optimization Engine for UPIAI.
Orchestrates the entire pipeline: Ingestion -> Profiling -> Schema Mapping ->
Readiness Governance -> Feature Engineering -> ML Forecasting ->
Inventory Health -> Supplier Allocation -> Executive Action Ledger.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from ai.data.loader import DataLoader
from ai.data.profiler import DataProfiler
from ai.schema.schema_mapper import UniversalSchemaMapper, CanonicalField
from ai.schema.data_readiness import DataReadinessAuditor
from ai.features.demand_features import DemandFeatureEngineer
from ai.forecasting.forecaster import DemandForecasterModel
from ai.inventory.optimizer import InventoryOptimizer
from ai.suppliers.scorer import SupplierScorer
from ai.sales.analyzer import SalesIntelligenceAnalyzer
from ai.personalization.engine import PersonalizationEngine


class UPIDecisionEngine:
    """Master AI engine coordinating all intelligence modules."""

    @classmethod
    def process_business_dataset(
        cls,
        df_raw: pd.DataFrame,
        dataset_name: str = "Client Dataset",
        sector_key: str = "GROCERY_SUPERMARKET",
        forecast_horizon_days: int = 7,
        custom_inventory_stock: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end audit, mapping, readiness check, forecasting, and inventory optimization.
        """
        # 1. Profile Raw Dataset
        profile_report = DataProfiler.profile(df_raw, dataset_name=dataset_name, save_to_disk=False)

        # 2. Universal Schema Mapping
        mapped_df, mapping_summary = UniversalSchemaMapper.map_schema(df_raw)

        # 3. Data Readiness & Governance Audit
        readiness_scorecard = DataReadinessAuditor.audit(mapped_df)

        # 4. Sales Intelligence Breakdown
        sales_intelligence = SalesIntelligenceAnalyzer.analyze_sales(mapped_df)

        # 5. Check if Demand Forecasting is permitted
        forecast_results = []
        inventory_recommendations = []
        model_training_summary = None

        if readiness_scorecard["can_proceed_to_forecast"]:
            try:
                # 6. Feature Engineering
                features_df, feat_meta = DemandFeatureEngineer.create_features(
                    mapped_df,
                    entity_key="product_category" if "product_category" in mapped_df.columns else "product_id"
                )

                # 7. Model Training & Forecasting
                forecaster = DemandForecasterModel(horizon_days=forecast_horizon_days)
                model_training_summary = forecaster.train(features_df)

                entity_col = feat_meta["entity_key"]
                unique_entities = features_df[entity_col].unique()

                for ent in unique_entities:
                    ent_history = features_df[features_df[entity_col] == ent]
                    fc_detail = forecaster.forecast_horizon(
                        recent_history_df=ent_history,
                        entity_name=str(ent),
                        horizon_days=forecast_horizon_days
                    )
                    forecast_results.append(fc_detail)

                    # 8. Inventory Optimization
                    # Use provided stock or simulate realistic level for testing
                    current_stock = 30
                    if custom_inventory_stock and str(ent) in custom_inventory_stock:
                        current_stock = custom_inventory_stock[str(ent)]

                    daily_vol = fc_detail["daily_velocity"]
                    daily_std = max(0.5, float(ent_history["units_sold"].std()) if len(ent_history) > 1 else 1.0)

                    inv_rec = InventoryOptimizer.evaluate_sku_inventory(
                        sku=f"SKU-{str(ent)[:8].upper().replace(' ', '-')}",
                        product_name=str(ent),
                        current_stock=current_stock,
                        on_order_stock=0,
                        daily_velocity=daily_vol,
                        daily_std=daily_std,
                        unit_cost=65.0,
                        unit_price=100.0,
                        lead_time_days=7
                    )
                    inventory_recommendations.append(inv_rec)

            except Exception as exc:
                readiness_scorecard["summary_warnings"].append(f"Forecasting pipeline notice: {str(exc)}")

        # 9. Aggregate Executive Summary
        total_projected_units = sum(f["total_predicted_units"] for f in forecast_results)
        total_projected_revenue = sum(f["projected_revenue"] for f in forecast_results)
        critical_risk_count = sum(1 for r in inventory_recommendations if r["risk_tier"] == "CRITICAL")

        return {
            "dataset_name": dataset_name,
            "readiness_scorecard": readiness_scorecard,
            "schema_mappings": mapping_summary,
            "model_training_summary": model_training_summary,
            "executive_kpis": {
                "readiness_score": readiness_scorecard["overall_health_score"],
                "readiness_tier": readiness_scorecard["overall_tier"],
                "total_projected_units": round(total_projected_units, 2),
                "total_projected_revenue": round(total_projected_revenue, 2),
                "critical_skus_at_risk": critical_risk_count,
                "total_categories_modeled": len(forecast_results)
            },
            "sales_intelligence": sales_intelligence,
            "demand_forecasts": forecast_results,
            "inventory_recommendations": inventory_recommendations
        }
