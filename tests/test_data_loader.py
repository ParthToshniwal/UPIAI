"""
Unit tests for DataLoader and DataProfiler.
"""

import os
import pytest
import pandas as pd
from ai.data.loader import DataLoader, DatasetProvenance
from ai.data.profiler import DataProfiler


def test_data_loader_csv():
    df, report = DataLoader.load("data/raw/DMart_sample_data.csv")
    assert not df.empty
    assert len(df) == 50
    assert report.row_count == 50
    assert report.column_count == 8
    assert "Date" in report.columns
    assert "Quantity" in report.columns
    assert report.provenance_tag == DatasetProvenance.OBSERVED_REAL_DATA


def test_data_profiler():
    df, _ = DataLoader.load("data/raw/DMart_sample_data.csv")
    profile = DataProfiler.profile(df, dataset_name="test_dmart", save_to_disk=False)
    assert profile["row_count"] == 50
    assert "Quantity" in profile["possible_target_columns"]
    assert "UnitPrice" in profile["numeric_statistics"]
    assert profile["duplicate_count"] == 0
