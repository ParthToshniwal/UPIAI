"""
Interactive CLI Runner & Demonstration Script for UPIAI AI Core.
Ingests dataset, profiles schema, runs Data Readiness Engine, trains multi-model benchmarks,
and executes 7-day demand forecasting & dynamic reorder optimization.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
import pandas as pd

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai.data.loader import DataLoader
from ai.data.profiler import DataProfiler
from ai.schema.schema_mapper import UniversalSchemaMapper
from ai.schema.data_readiness import DataReadinessAuditor
from ai.decision_engine import UPIDecisionEngine
from ai.models.baselines import BaselineComparator
from ai.features.demand_features import DemandFeatureEngineer
from simulation.retail_environment import SyntheticRetailSimulator


def print_banner():
    print("\n" + "=" * 80)
    print("  UPIAI -- UNIVERSAL PERSONALIZED INVENTORY & DEMAND INTELLIGENCE AI  ")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="UPIAI Core AI Pipeline CLI")
    parser.add_argument("--file", type=str, default="data/raw/DMart_sample_data.csv", help="Path to input data file")
    parser.add_argument("--simulate", action="store_true", help="Generate and run on synthetic multi-month retail data")
    parser.add_argument("--horizon", type=int, default=7, help="Forecast horizon days (default: 7)")
    parser.add_argument("--sector", type=str, default="GROCERY_SUPERMARKET", help="Business vertical sector")
    args = parser.parse_args()

    print_banner()

    # 1. Ingestion
    if args.simulate:
        print("\n[PHASE 1] Generating 180-Day Multi-Store Synthetic Retail Environment...")
        df = SyntheticRetailSimulator.generate_environment(days=180, store_count=2)
        dataset_name = "Synthetic Retail Simulation (180d)"
    else:
        print(f"\n[PHASE 1] Loading Dataset from: {args.file}")
        df, report = DataLoader.load(args.file)
        dataset_name = os.path.basename(args.file)
        print(f"  * Ingested Rows: {report.row_count}")
        print(f"  * Columns Detected ({report.column_count}): {', '.join(report.columns)}")
        print(f"  * Provenance Tag: {report.provenance_tag}")

    # 2. Data Profiling
    print("\n[PHASE 2] Running Automated Data Profiler...")
    profile = DataProfiler.profile(df, dataset_name=dataset_name, save_to_disk=True)
    print(f"  * Profile saved to: {profile.get('saved_profile_path', 'memory')}")
    print(f"  * Target candidate columns: {profile['possible_target_columns']}")
    print(f"  * Duplicate rows detected: {profile['duplicate_count']}")

    # 3. Universal Schema Mapping
    print("\n[PHASE 3] Executing Universal Schema Mapper...")
    mapped_df, mapping_summary = UniversalSchemaMapper.map_schema(df)
    for m in mapping_summary["mappings"]:
        print(f"  * {m['source_column']}  -->  {m['canonical_column']} (Confidence: {m['confidence']:.2f}, Type: {m['match_type']})")

    # 4. Data Readiness & Governance Engine
    print("\n[PHASE 4] Running Data Readiness & Governance Engine (Rule: Never Hide Missing Data)...")
    readiness = DataReadinessAuditor.audit(mapped_df)
    print(f"  * Overall Data Readiness Index: {readiness['overall_health_score']}% [{readiness['overall_tier']}]")
    print("  * Capability Status Matrix:")
    for cap_key, cap in readiness["capabilities"].items():
        status_icon = "[READY]" if cap["status"] == "AVAILABLE" else ("[LIMIT]" if cap["status"] == "LIMITED" else "[UNAV]")
        print(f"    {status_icon:<7} {cap['capability']:<24}: {cap['status']:<11} | {cap['explanation']}")

    # 5. Full End-to-End Decision Execution
    print(f"\n[PHASE 5] Executing Feature Engineering, XGBoost Training & {args.horizon}-Day Forecast...")
    result = UPIDecisionEngine.process_business_dataset(
        df_raw=df,
        dataset_name=dataset_name,
        sector_key=args.sector,
        forecast_horizon_days=args.horizon
    )

    if result.get("model_training_summary"):
        m_metrics = result["model_training_summary"]["training_metrics"]
        print(f"  * Model Training Metrics: MAE={m_metrics['mae']}, RMSE={m_metrics['rmse']}, R2={m_metrics['r2']}")

    print("\n[PHASE 6] AI Demand Forecast & Inventory Recommendations:")
    print(f"{'Category / Product':<28} | {'Stock':<6} | {'Fcst ' + str(args.horizon) + 'd':<9} | {'Days Supply':<12} | {'Risk Tier':<12} | {'Recommended PO':<18}")
    print("-" * 96)

    for rec in result.get("inventory_recommendations", []):
        fc_match = next((f for f in result["demand_forecasts"] if f["entity"] == rec["product_name"]), None)
        fc_units = f"{fc_match['total_predicted_units']}u" if fc_match else "---"
        po_str = f"+{rec['recommended_reorder_qty']} units" if rec['recommended_reorder_qty'] > 0 else "None"
        print(f"{rec['product_name'][:26]:<28} | {rec['current_stock']:<6} | {fc_units:<9} | {str(rec['days_of_supply_remaining']) + 'd':<12} | {rec['risk_tier']:<12} | {po_str:<18}")

    print("\n" + "=" * 80)
    print(f"  UPIAI Pipeline Execution Complete for {dataset_name}  ")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
