"""
Unit tests for UniversalSchemaMapper and DataReadinessAuditor.
"""

import pytest
import pandas as pd
from ai.schema.schema_mapper import UniversalSchemaMapper, CanonicalField
from ai.schema.data_readiness import DataReadinessAuditor, CapabilityStatus


def test_schema_mapper_dmart():
    raw_data = {
        "Date": ["2026-06-01", "2026-06-02"],
        "Time": ["10:15:00", "11:20:00"],
        "CustomerType": ["Member", "Regular"],
        "ProductCategory": ["Grocery", "Dairy"],
        "UnitPrice": [120.0, 60.0],
        "Quantity": [3, 4],
        "Total": [360.0, 240.0],
        "FullName": ["Aarav", "Priya"]
    }
    df = pd.DataFrame(raw_data)
    mapped_df, summary = UniversalSchemaMapper.map_schema(df)

    assert CanonicalField.UNITS_SOLD in mapped_df.columns
    assert CanonicalField.TRANSACTION_DATETIME in mapped_df.columns
    assert CanonicalField.PRODUCT_CATEGORY in mapped_df.columns
    assert CanonicalField.UNIT_PRICE in mapped_df.columns
    assert summary["mapped_columns_count"] == 8


def test_data_readiness_audit_rule_never_hide_missing():
    # Only sales data provided -> Demand Forecasting available, Stockout UNAVAILABLE
    raw_sales = {
        "date": [f"2026-06-{i:02d}" for i in range(1, 31)],
        "sku": ["SKU-001"] * 30,
        "units_sold": [10 + (i % 3) for i in range(1, 31)],
        "unit_price": [100.0] * 30
    }
    df = pd.DataFrame(raw_sales)
    audit = DataReadinessAuditor.audit(df)

    # Demand forecasting can proceed
    assert audit["can_proceed_to_forecast"] is True
    assert audit["capabilities"]["demand_forecasting"]["can_execute"] is True

    # Stockout is explicitly UNAVAILABLE because inventory was not provided
    assert audit["capabilities"]["stockout_prediction"]["status"] == CapabilityStatus.UNAVAILABLE
    assert audit["capabilities"]["stockout_prediction"]["can_execute"] is False
    assert "current stock on hand was not provided" in audit["capabilities"]["stockout_prediction"]["explanation"]
