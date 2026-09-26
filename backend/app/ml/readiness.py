"""
Data Readiness & Provenance Engine.
Inspects raw datasets, performs schema & data health auditing, calculates a 
governance confidence readiness score (0-100%), and yields structural limitation disclosures.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

try:
    from app.models.schemas import ColumnAuditResult, ReadinessScorecardResponse
except ImportError:
    try:
        from backend.app.models.schemas import ColumnAuditResult, ReadinessScorecardResponse
    except ImportError:
        # Pydantic schema fallback for standalone execution
        from pydantic import BaseModel, Field
        class ColumnAuditResult(BaseModel):
            column_name: str
            status: str
            data_type: str
            missing_count: int
            missing_percentage: float
            importance: str
            impact_description: str

        class ReadinessScorecardResponse(BaseModel):
            overall_readiness_score: float
            operational_tier: str
            total_records: int
            unique_skus_detected: int
            date_range_start: Optional[str] = None
            date_range_end: Optional[str] = None
            data_span_days: int
            column_audits: List[ColumnAuditResult]
            critical_missing_fields: List[str]
            structural_limitations: List[str]
            remediation_recommendations: List[str]
            can_proceed_to_forecast: bool
            assumed_defaults_applied: Dict[str, Any]


# Canonical schema definitions and aliases tailored for Retail & DMart datasets
COLUMN_DEFINITIONS = {
    "date": {
        "aliases": ["date", "transaction_date", "order_date", "timestamp", "sale_date", "day"],
        "importance": "CRITICAL",
        "expected_type": "datetime",
        "weight": 25.0,
        "impact": "Required for time-series aggregation, seasonality detection, and autoregressive lag computation."
    },
    "product_category": {
        "aliases": ["productcategory", "product_category", "category", "dept", "department", "segment"],
        "importance": "CRITICAL",
        "expected_type": "string",
        "weight": 20.0,
        "impact": "Primary entity key for grocery department clustering and category demand forecasting."
    },
    "units_sold": {
        "aliases": ["quantity", "units_sold", "qty", "sales_volume", "units", "quantity_sold"],
        "importance": "CRITICAL",
        "expected_type": "numeric",
        "weight": 25.0,
        "impact": "Core target variable. Missing sales volume prevents demand forecasting entirely."
    },
    "unit_price": {
        "aliases": ["unitprice", "unit_price", "selling_price", "price", "retail_price", "sales_price"],
        "importance": "HIGH",
        "expected_type": "numeric",
        "weight": 10.0,
        "impact": "Required to calculate revenue projections and financial gross margins."
    },
    "total_amount": {
        "aliases": ["total", "total_amount", "amount", "revenue", "gross_sales"],
        "importance": "HIGH",
        "expected_type": "numeric",
        "weight": 10.0,
        "impact": "Validates transactional revenue reconciliation and basket size analytics."
    },
    "customer_type": {
        "aliases": ["customertype", "customer_type", "type", "member_type", "loyalty_tier"],
        "importance": "MEDIUM",
        "expected_type": "string",
        "weight": 5.0,
        "impact": "Enables customer cohort behavior modeling (Member vs Regular vs Corporate)."
    },
    "customer_name": {
        "aliases": ["fullname", "customer_name", "name", "client", "shopper"],
        "importance": "OPTIONAL",
        "expected_type": "string",
        "weight": 5.0,
        "impact": "Used for basket frequency tracking and repeat customer profiling."
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

        total_score = 0.0

        for canonical_col, meta in COLUMN_DEFINITIONS.items():
            matched_col_name = None
            for alias in meta["aliases"]:
                if alias.lower() in df_cols_lower:
                    matched_col_name = df_cols_lower[alias.lower()]
                    break

            if matched_col_name is not None:
                series = df[matched_col_name]
                missing_count = int(series.isna().sum()) + int((series.astype(str).str.strip() == '').sum())
                missing_pct = round((missing_count / total_records) * 100.0, 2)

                # Penalize score based on missingness
                completeness_ratio = max(0.0, 1.0 - (missing_count / total_records))
                total_score += meta["weight"] * completeness_ratio

                col_status = "PRESENT" if missing_pct == 0.0 else "PRESENT_WITH_NULLS"

                column_audits.append(ColumnAuditResult(
                    column_name=f"{matched_col_name} (maps to '{canonical_col}')",
                    status=col_status,
                    data_type=str(series.dtype),
                    missing_count=missing_count,
                    missing_percentage=missing_pct,
                    importance=meta["importance"],
                    impact_description=meta["impact"]
                ))

                if missing_pct > 10.0 and meta["importance"] == "CRITICAL":
                    structural_limitations.append(
                        f"Critical column '{matched_col_name}' has {missing_pct}% missing values."
                    )
                    remediation_recommendations.append(
                        f"Impute or backfill missing values in '{matched_col_name}'."
                    )
            else:
                # Column is missing
                if meta["importance"] == "CRITICAL":
                    critical_missing.append(canonical_col)
                    structural_limitations.append(
                        f"Missing critical dimension: '{canonical_col}'. Forecasting accuracy will be impacted."
                    )
                    remediation_recommendations.append(
                        f"Provide '{canonical_col}' column in data ingestion pipeline."
                    )
                else:
                    # Inferred default
                    if canonical_col == "unit_price":
                        assumed_defaults["unit_price"] = "Inferred 100.0 average retail price"
                    elif canonical_col == "customer_type":
                        assumed_defaults["customer_type"] = "Defaulted to 'Regular' tier"

                column_audits.append(ColumnAuditResult(
                    column_name=f"MISSING: '{canonical_col}'",
                    status="MISSING",
                    data_type="none",
                    missing_count=total_records,
                    missing_percentage=100.0,
                    importance=meta["importance"],
                    impact_description=meta["impact"]
                ))

        # Date range analysis
        date_start = None
        date_end = None
        span_days = 0

        date_col = None
        for alias in ["date", "transaction_date", "Date", "day"]:
            if alias.lower() in df_cols_lower:
                date_col = df_cols_lower[alias.lower()]
                break

        if date_col:
            try:
                date_series = pd.to_datetime(df[date_col], errors='coerce').dropna()
                if not date_series.empty:
                    date_start = date_series.min().strftime('%Y-%m-%d')
                    date_end = date_series.max().strftime('%Y-%m-%d')
                    span_days = (date_series.max() - date_series.min()).days + 1
            except Exception:
                pass

        # Determine Unique Categories / Entities
        cat_col = None
        for alias in ["productcategory", "product_category", "category", "dept"]:
            if alias.lower() in df_cols_lower:
                cat_col = df_cols_lower[alias.lower()]
                break

        unique_cats = df[cat_col].nunique() if cat_col and cat_col in df.columns else 1

        # Additional provenance structural limitation disclosures
        if span_days < 14:
            structural_limitations.append(
                f"Historical timespan is {span_days} days. Multi-horizon 30d forecast utilizes bootstrap lag augmentation."
            )
            remediation_recommendations.append(
                "Ingest at least 60-90 days of daily transaction history to maximize seasonal capture."
            )

        # Readiness Tier
        overall_score = round(min(100.0, max(0.0, total_score)), 1)
        if overall_score >= 80.0 and len(critical_missing) == 0:
            operational_tier = "HIGH_CONFIDENCE"
            can_proceed = True
        elif overall_score >= 50.0:
            operational_tier = "MODERATE_CONFIDENCE"
            can_proceed = True
        else:
            operational_tier = "DEGRADED"
            can_proceed = False

        return ReadinessScorecardResponse(
            overall_readiness_score=overall_score,
            operational_tier=operational_tier,
            total_records=total_records,
            unique_skus_detected=unique_cats,
            date_range_start=date_start,
            date_range_end=date_end,
            data_span_days=span_days,
            column_audits=column_audits,
            critical_missing_fields=critical_missing,
            structural_limitations=structural_limitations,
            remediation_recommendations=remediation_recommendations,
            can_proceed_to_forecast=can_proceed,
            assumed_defaults_applied=assumed_defaults
        )

    @classmethod
    def _generate_empty_scorecard(cls, reason: str) -> ReadinessScorecardResponse:
        return ReadinessScorecardResponse(
            overall_readiness_score=0.0,
            operational_tier="DEGRADED",
            total_records=0,
            unique_skus_detected=0,
            date_range_start=None,
            date_range_end=None,
            data_span_days=0,
            column_audits=[],
            critical_missing_fields=["ALL"],
            structural_limitations=[reason],
            remediation_recommendations=["Upload a valid non-empty CSV dataset with DMart retail columns."],
            can_proceed_to_forecast=False,
            assumed_defaults_applied={}
        )
