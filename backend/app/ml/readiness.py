"""
Data Readiness & Provenance Engine.
Inspects raw datasets, performs schema & data health auditing, calculates a 
governance confidence readiness score (0-100%), and yields structural limitation disclosures.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from app.models.schemas import ColumnAuditResult, ReadinessScorecardResponse


# Canonical schema definitions and aliases
COLUMN_DEFINITIONS = {
    "date": {
        "aliases": ["date", "order_date", "transaction_date", "timestamp", "sale_date", "day"],
        "importance": "CRITICAL",
        "expected_type": "datetime",
        "impact": "Required for time-series aggregation, seasonality detection, and lag feature computation."
    },
    "sku": {
        "aliases": ["sku", "item_id", "product_id", "sku_id", "part_number", "item_code"],
        "importance": "CRITICAL",
        "expected_type": "string",
        "impact": "Primary entity key required for product-level demand partitioning and inventory tracking."
    },
    "units_sold": {
        "aliases": ["units_sold", "quantity", "qty", "sales_volume", "units", "quantity_sold"],
        "importance": "CRITICAL",
        "expected_type": "numeric",
        "impact": "Core target variable. Missing sales volume prevents demand forecasting entirely."
    },
    "current_stock": {
        "aliases": ["current_stock", "stock_on_hand", "inventory_level", "available_stock", "qty_on_hand", "stock"],
        "importance": "HIGH",
        "expected_type": "numeric",
        "impact": "Required to compute days-of-supply remaining and evaluate immediate stockout probabilities."
    },
    "unit_price": {
        "aliases": ["unit_price", "selling_price", "price", "retail_price", "sales_price"],
        "importance": "HIGH",
        "expected_type": "numeric",
        "impact": "Required to calculate revenue projections and financial value at risk during stockouts."
    },
    "unit_cost": {
        "aliases": ["unit_cost", "cost_price", "cogs", "purchase_price", "wholesale_cost"],
        "importance": "MEDIUM",
        "expected_type": "numeric",
        "impact": "Used for capital valuation, tied-up working capital calculations, and PO expense estimation."
    },
    "lead_time_days": {
        "aliases": ["lead_time_days", "lead_time", "supplier_lead_time", "replenishment_days", "delivery_days"],
        "importance": "HIGH",
        "expected_type": "numeric",
        "impact": "Determines reorder point deadlines. Missing values require a default safety buffer (14 days)."
    },
    "supplier_id": {
        "aliases": ["supplier_id", "vendor_id", "supplier", "vendor", "supplier_name"],
        "importance": "MEDIUM",
        "expected_type": "string",
        "impact": "Enables supplier reliability tracking and automated purchase order routing."
    },
    "category": {
        "aliases": ["category", "product_category", "segment", "department", "product_group"],
        "importance": "OPTIONAL",
        "expected_type": "string",
        "impact": "Used for hierarchical demand aggregation and cross-category velocity profiling."
    }
}


class DataReadinessEngine:
    """Audits tabular datasets for ML forecasting readiness and provenance hygiene."""

    @classmethod
    def audit_dataset(cls, data: Any) -> ReadinessScorecardResponse:
        """
        Audits a dataset (list of dicts or pandas DataFrame) and returns a complete health scorecard.
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            return cls._generate_empty_scorecard("Invalid data input type")

        if df.empty:
            return cls._generate_empty_scorecard("Empty dataset provided")

        total_records = len(df)
        df_cols_lower = {str(col).strip().lower(): col for col in df.columns}

        column_audits: List[ColumnAuditResult] = []
        critical_missing: List[str] = []
        structural_limitations: List[str] = []
        remediation_recommendations: List[str] = []
        assumed_defaults: Dict[str, Any] = {}

        # 1. Column Presence & Aliasing Check
        matched_columns: Dict[str, str] = {}
        for canonical_name, defs in COLUMN_DEFINITIONS.items():
            matched_col_raw = None
            for alias in defs["aliases"]:
                if alias in df_cols_lower:
                    matched_col_raw = df_cols_lower[alias]
                    break

            if matched_col_raw is not None:
                matched_columns[canonical_name] = matched_col_raw
                series = df[matched_col_raw]
                missing_cnt = int(series.isna().sum())
                missing_pct = round((missing_cnt / total_records) * 100.0, 2)
                dtype_str = str(series.dtype)

                column_audits.append(
                    ColumnAuditResult(
                        column_name=canonical_name,
                        status="PRESENT",
                        data_type=dtype_str,
                        missing_count=missing_cnt,
                        missing_percentage=missing_pct,
                        importance=defs["importance"],
                        impact_description=defs["impact"]
                    )
                )

                if missing_pct > 10.0:
                    structural_limitations.append(
                        f"Field '{canonical_name}' has {missing_pct}% null values. Imputation will be applied."
                    )
            else:
                # Column is missing
                column_audits.append(
                    ColumnAuditResult(
                        column_name=canonical_name,
                        status="MISSING",
                        data_type="none",
                        missing_count=total_records,
                        missing_percentage=100.0,
                        importance=defs["importance"],
                        impact_description=defs["impact"]
                    )
                )

                if defs["importance"] == "CRITICAL":
                    critical_missing.append(canonical_name)
                    structural_limitations.append(
                        f"CRITICAL: Missing required column '{canonical_name}'. Model cannot run without core identifier."
                    )
                    remediation_recommendations.append(
                        f"Map your source column representing '{canonical_name}' to '{defs['aliases'][0]}'."
                    )
                elif canonical_name == "lead_time_days":
                    assumed_defaults["lead_time_days"] = 14
                    structural_limitations.append(
                        "Supplier lead time absent. Defaulted to conservative 14-day cycle (+25% safety stock buffer)."
                    )
                    remediation_recommendations.append(
                        "Provide supplier lead time records to optimize buffer safety stock and prevent over-purchasing."
                    )
                elif canonical_name == "current_stock":
                    assumed_defaults["current_stock"] = 50
                    structural_limitations.append(
                        "Inventory state column missing. Stockout risks estimated assuming baseline 50 units."
                    )
                    remediation_recommendations.append(
                        "Sync ERP/WMS stock-on-hand values to enable real-time depletion monitoring."
                    )
                elif canonical_name == "unit_cost":
                    assumed_defaults["unit_cost_margin_proxy"] = 0.65
                    structural_limitations.append(
                        "Product unit cost absent. Inventory valuation approximated using 65% COGS margin proxy."
                    )

        # 2. Temporal Span & Continuity Analysis
        date_start_str = None
        date_end_str = None
        data_span_days = 0

        if "date" in matched_columns:
            date_col = matched_columns["date"]
            try:
                converted_dates = pd.to_datetime(df[date_col], errors='coerce').dropna()
                if not converted_dates.empty:
                    min_dt = converted_dates.min()
                    max_dt = converted_dates.max()
                    date_start_str = min_dt.strftime("%Y-%m-%d")
                    date_end_str = max_dt.strftime("%Y-%m-%d")
                    data_span_days = (max_dt - min_dt).days + 1

                    if data_span_days < 30:
                        structural_limitations.append(
                            f"Historical depth is limited ({data_span_days} days). Demand forecasts rely on short-term rolling momentum."
                        )
                        remediation_recommendations.append(
                            "Ingest at least 90-180 days of sales history to unlock multi-week XGBoost seasonality detection."
                        )
            except Exception as e:
                structural_limitations.append(f"Failed to parse datetime series: {str(e)}")

        # 3. Unique SKU Cardinality
        unique_skus = 0
        if "sku" in matched_columns:
            unique_skus = int(df[matched_columns["sku"]].nunique())

        # 4. Composite Readiness Score Calculation (0 - 100)
        score = 100.0

        # Penalize for critical missing
        if "date" not in matched_columns:
            score -= 30.0
        if "sku" not in matched_columns:
            score -= 30.0
        if "units_sold" not in matched_columns:
            score -= 30.0

        # Penalize for high/medium missing
        if "current_stock" not in matched_columns:
            score -= 10.0
        if "lead_time_days" not in matched_columns:
            score -= 8.0
        if "unit_price" not in matched_columns:
            score -= 6.0
        if "unit_cost" not in matched_columns:
            score -= 4.0
        if "supplier_id" not in matched_columns:
            score -= 4.0

        # Penalize for short historical span
        if data_span_days > 0 and data_span_days < 30:
            score -= 10.0
        elif data_span_days >= 90:
            score = min(100.0, score + 5.0)

        # Penalize for high null ratios in present columns
        for audit in column_audits:
            if audit.status == "PRESENT" and audit.missing_percentage > 5.0:
                score -= min(10.0, (audit.missing_percentage / 10.0) * 2.0)

        readiness_score = max(5.0, min(100.0, round(score, 1)))

        # Tier classification
        if readiness_score >= 80.0 and len(critical_missing) == 0:
            tier = "HIGH_CONFIDENCE"
        elif readiness_score >= 50.0 and len(critical_missing) == 0:
            tier = "MODERATE_CONFIDENCE"
        else:
            tier = "DEGRADED"

        can_forecast = len(critical_missing) == 0

        return ReadinessScorecardResponse(
            overall_readiness_score=readiness_score,
            operational_tier=tier,
            total_records=total_records,
            unique_skus_detected=unique_skus,
            date_range_start=date_start_str,
            date_range_end=date_end_str,
            data_span_days=data_span_days,
            column_audits=column_audits,
            critical_missing_fields=critical_missing,
            structural_limitations=structural_limitations,
            remediation_recommendations=remediation_recommendations,
            can_proceed_to_forecast=can_forecast,
            assumed_defaults_applied=assumed_defaults
        )

    @staticmethod
    def _generate_empty_scorecard(reason: str) -> ReadinessScorecardResponse:
        return ReadinessScorecardResponse(
            overall_readiness_score=0.0,
            operational_tier="DEGRADED",
            total_records=0,
            unique_skus_detected=0,
            date_range_start=None,
            date_range_end=None,
            data_span_days=0,
            column_audits=[],
            critical_missing_fields=["date", "sku", "units_sold"],
            structural_limitations=[f"Dataset unavailable or invalid: {reason}"],
            remediation_recommendations=["Upload a valid JSON or CSV dataset with sales and product columns."],
            can_proceed_to_forecast=False,
            assumed_defaults_applied={}
        )
