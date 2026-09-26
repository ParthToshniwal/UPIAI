"""
Demand Feature Engineering Pipeline for UPIAI.
Transforms mapped daily sales and pricing observations into multi-horizon autoregressive,
rolling statistical, temporal, calendar, holiday/festival, and price-elasticity feature matrices.
Attaches explicit provenance metadata to each generated feature column.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from ai.data.loader import DatasetProvenance
from ai.schema.schema_mapper import CanonicalField


# Reference major retail festival calendar periods (Month-Day)
FESTIVAL_CALENDAR = {
    "Republic_Day": (1, 26),
    "Holi_Season": (3, 15),
    "Independence_Day": (8, 15),
    "Ganesh_Chaturthi": (9, 10),
    "Navratri_Dussehra": (10, 12),
    "Diwali_Peak": (11, 1),
    "Christmas_NewYear": (12, 25),
}


class FeatureProvenanceRegistry:
    """Tracks the data lineage of engineered features."""

    @staticmethod
    def get_feature_provenance_map() -> Dict[str, str]:
        return {
            "units_sold": DatasetProvenance.OBSERVED_REAL_DATA,
            "unit_price": DatasetProvenance.OBSERVED_REAL_DATA,
            "sales_lag_1": DatasetProvenance.DERIVED,
            "sales_lag_7": DatasetProvenance.DERIVED,
            "sales_lag_14": DatasetProvenance.DERIVED,
            "sales_lag_28": DatasetProvenance.DERIVED,
            "rolling_mean_7": DatasetProvenance.DERIVED,
            "rolling_mean_14": DatasetProvenance.DERIVED,
            "rolling_mean_30": DatasetProvenance.DERIVED,
            "rolling_std_7": DatasetProvenance.DERIVED,
            "rolling_std_30": DatasetProvenance.DERIVED,
            "sales_growth": DatasetProvenance.DERIVED,
            "day_of_week": DatasetProvenance.DERIVED,
            "week_of_year": DatasetProvenance.DERIVED,
            "month": DatasetProvenance.DERIVED,
            "quarter": DatasetProvenance.DERIVED,
            "is_weekend": DatasetProvenance.DERIVED,
            "is_festival": DatasetProvenance.DERIVED,
            "price_change": DatasetProvenance.DERIVED,
            "is_promotion": DatasetProvenance.DERIVED
        }


class DemandFeatureEngineer:
    """Transforms raw time series into high-dimensional ML-ready feature matrices."""

    @classmethod
    def create_features(
        cls, 
        df: pd.DataFrame, 
        entity_key: str = "product_id",
        target_col: str = "units_sold",
        date_col: str = "transaction_datetime",
        price_col: str = "unit_price"
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Creates lags, rolling windows, calendar attributes, festivals, and growth signals.
        """
        if df.empty:
            raise ValueError("Cannot engineer features from an empty DataFrame.")

        data = df.copy()

        # Ensure date format
        if date_col in data.columns:
            data['date_dt'] = pd.to_datetime(data[date_col], errors='coerce', format='mixed')
            data = data.dropna(subset=['date_dt'])
            data['date_only'] = data['date_dt'].dt.date
        else:
            raise ValueError(f"Date column '{date_col}' not found in DataFrame.")

        # Determine grouping key (entity)
        if entity_key not in data.columns:
            if "product_category" in data.columns:
                entity_key = "product_category"
            elif "sku" in data.columns:
                entity_key = "sku"
            else:
                data["_global_entity"] = "ALL_PRODUCTS"
                entity_key = "_global_entity"

        # 1. Aggregate Daily Sales per Entity
        agg_dict = {target_col: 'sum'}
        if price_col in data.columns:
            agg_dict[price_col] = 'mean'

        daily_df = data.groupby(['date_only', entity_key]).agg(agg_dict).reset_index()
        daily_df['date_dt'] = pd.to_datetime(daily_df['date_only'])
        daily_df = daily_df.sort_values(['date_dt']).reset_index(drop=True)

        features_list = []
        created_feature_names = []

        # Process per entity to prevent cross-product lag contamination
        for entity_val, group in daily_df.groupby(entity_key):
            g = group.sort_values('date_dt').copy()

            # Ensure continuous daily index
            min_date = g['date_dt'].min()
            max_date = g['date_dt'].max()
            full_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
            
            g = g.set_index('date_dt').reindex(full_date_range)
            g[entity_key] = entity_val
            g[target_col] = g[target_col].fillna(0.0)

            if price_col in g.columns:
                g[price_col] = g[price_col].ffill().bfill().fillna(100.0)

            g = g.reset_index().rename(columns={'index': 'date_dt'})

            # --- Temporal & Calendar Features ---
            g['day_of_week'] = g['date_dt'].dt.dayofweek
            g['week_of_year'] = g['date_dt'].dt.isocalendar().week.astype(int)
            g['month'] = g['date_dt'].dt.month
            g['quarter'] = g['date_dt'].dt.quarter
            g['is_weekend'] = g['day_of_week'].isin([5, 6]).astype(int)

            # --- Festival Proximity Feature ---
            def is_near_festival(dt) -> int:
                m, d = dt.month, dt.day
                for fest, (fm, fd) in FESTIVAL_CALENDAR.items():
                    if m == fm and abs(d - fd) <= 4:
                        return 1
                return 0

            g['is_festival'] = g['date_dt'].apply(is_near_festival)

            # --- Autoregressive Lags ---
            for lag in [1, 7, 14, 28]:
                col_name = f"sales_lag_{lag}"
                g[col_name] = g[target_col].shift(lag)
                if col_name not in created_feature_names:
                    created_feature_names.append(col_name)

            # --- Rolling Window Statistics ---
            # Shift by 1 to prevent data leakage of the target day
            g['rolling_mean_7'] = g[target_col].shift(1).rolling(window=7, min_periods=1).mean()
            g['rolling_mean_14'] = g[target_col].shift(1).rolling(window=14, min_periods=1).mean()
            g['rolling_mean_30'] = g[target_col].shift(1).rolling(window=30, min_periods=1).mean()
            g['rolling_std_7'] = g[target_col].shift(1).rolling(window=7, min_periods=1).std().fillna(0)
            g['rolling_std_30'] = g[target_col].shift(1).rolling(window=30, min_periods=1).std().fillna(0)

            # --- Sales Growth & Velocity Momentum ---
            g['sales_growth'] = (
                (g['rolling_mean_7'] - g['rolling_mean_14']) / (g['rolling_mean_14'] + 1e-4)
            ).clip(-2.0, 5.0)

            # --- Price Dynamics ---
            if price_col in g.columns:
                g['rolling_price_14'] = g[price_col].shift(1).rolling(window=14, min_periods=1).mean()
                g['price_change'] = (
                    (g[price_col] - g['rolling_price_14']) / (g['rolling_price_14'] + 1e-4)
                ).fillna(0.0)
                g['is_promotion'] = (g['price_change'] < -0.05).astype(int)
            else:
                g['price_change'] = 0.0
                g['is_promotion'] = 0

            # Backfill initial lag NaNs to preserve data depth
            g = g.bfill().fillna(0.0)
            features_list.append(g)

        result_df = pd.concat(features_list, ignore_index=True)
        result_df['date'] = result_df['date_dt'].dt.strftime('%Y-%m-%d')

        metadata = {
            "entity_key": entity_key,
            "target_variable": target_col,
            "total_rows_produced": len(result_df),
            "date_range_start": str(result_df['date'].min()),
            "date_range_end": str(result_df['date'].max()),
            "feature_provenance": FeatureProvenanceRegistry.get_feature_provenance_map()
        }

        return result_df, metadata
