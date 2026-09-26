"""
Automated Data Profiling Engine for UPIAI.
Computes comprehensive statistical distributions, date ranges, outlier counts,
target candidate identification, and saves JSON inspection profiles to data/processed/.
"""

from typing import Dict, Any, List, Optional
import os
import json
from datetime import datetime
import pandas as pd
import numpy as np


class DataProfiler:
    """Produces in-depth data profiling reports and structural intelligence."""

    @classmethod
    def profile(
        cls, 
        df: pd.DataFrame, 
        dataset_name: str = "dataset",
        save_to_disk: bool = True,
        output_dir: str = "data/processed"
    ) -> Dict[str, Any]:
        """Profiles a DataFrame and optionally persists the JSON summary to output_dir."""
        if df.empty:
            return {
                "dataset_name": dataset_name,
                "row_count": 0,
                "column_count": 0,
                "error": "Dataset is empty"
            }

        row_count = int(len(df))
        column_count = int(len(df.columns))
        columns = list(df.columns)
        data_types = {str(col): str(dtype) for col, dtype in df.dtypes.items()}

        missing_values = {str(col): int(val) for col, val in df.isna().sum().to_dict().items()}
        missing_percentage = {
            str(col): round((cnt / max(1, row_count)) * 100.0, 2)
            for col, cnt in missing_values.items()
        }
        duplicate_count = int(df.duplicated().sum())
        unique_counts = {str(col): int(df[col].nunique(dropna=True)) for col in df.columns}

        # 1. Numeric Statistics & Outlier Detection
        numeric_statistics: Dict[str, Dict[str, float]] = {}
        outliers: Dict[str, Dict[str, Any]] = {}
        possible_targets: List[str] = []

        target_keywords = ["qty", "quantity", "units_sold", "units", "sales", "total", "amount", "volume"]

        for col in df.columns:
            # Check target candidates
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in target_keywords):
                possible_targets.append(str(col))

            if pd.api.types.is_numeric_dtype(df[col]):
                series = df[col].dropna()
                if not series.empty:
                    mean_val = float(series.mean())
                    std_val = float(series.std()) if len(series) > 1 else 0.0
                    min_val = float(series.min())
                    max_val = float(series.max())
                    q25 = float(series.quantile(0.25))
                    median_val = float(series.median())
                    q75 = float(series.quantile(0.75))
                    iqr = q75 - q25

                    numeric_statistics[str(col)] = {
                        "mean": round(mean_val, 4),
                        "std": round(std_val, 4),
                        "min": round(min_val, 4),
                        "q25": round(q25, 4),
                        "median": round(median_val, 4),
                        "q75": round(q75, 4),
                        "max": round(max_val, 4),
                        "iqr": round(iqr, 4)
                    }

                    # Outlier identification via 1.5 * IQR rule
                    lower_bound = q25 - (1.5 * iqr)
                    upper_bound = q75 + (1.5 * iqr)
                    outlier_mask = (series < lower_bound) | (series > upper_bound)
                    outlier_cnt = int(outlier_mask.sum())

                    outliers[str(col)] = {
                        "outlier_count": outlier_cnt,
                        "outlier_percentage": round((outlier_cnt / max(1, len(series))) * 100.0, 2),
                        "lower_threshold": round(lower_bound, 4),
                        "upper_threshold": round(upper_bound, 4)
                    }

        # 2. Date Ranges & Temporal Span
        date_ranges: Dict[str, Dict[str, Any]] = {}
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    converted = pd.to_datetime(df[col], errors='coerce', format='mixed').dropna()
                    if len(converted) >= 0.7 * row_count and not converted.empty:
                        min_date = converted.min()
                        max_date = converted.max()
                        span_days = int((max_date - min_date).days) + 1
                        date_ranges[str(col)] = {
                            "min_date": min_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "max_date": max_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "span_days": span_days,
                            "valid_date_records": int(len(converted))
                        }
                except Exception:
                    pass

        profile_report = {
            "dataset_name": dataset_name,
            "profiled_at": datetime.utcnow().isoformat(),
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns,
            "data_types": data_types,
            "missing_values": missing_values,
            "missing_percentage": missing_percentage,
            "duplicate_count": duplicate_count,
            "unique_counts": unique_counts,
            "numeric_statistics": numeric_statistics,
            "date_ranges": date_ranges,
            "outliers": outliers,
            "possible_target_columns": possible_targets
        }

        if save_to_disk:
            os.makedirs(output_dir, exist_ok=True)
            sanitized_name = dataset_name.replace(" ", "_").replace("/", "_").replace(".csv", "")
            filepath = os.path.join(output_dir, f"{sanitized_name}_profile.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile_report, f, indent=2)
            profile_report["saved_profile_path"] = filepath

        return profile_report
