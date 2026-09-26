"""
Universal Data Ingestion Engine for UPIAI.
Loads tabular datasets (CSV, Excel, JSON) with strict data integrity preservation,
column type inspection, missingness auditing, and provenance tagging.
"""

from typing import Dict, Any, List, Optional, Union
import os
import json
from datetime import datetime
import pandas as pd
import numpy as np


class DatasetProvenance:
    """Standardized provenance taxonomy for data audit trails."""
    OBSERVED_REAL_DATA = "OBSERVED_REAL_DATA"
    USER_PROVIDED = "USER_PROVIDED"
    PUBLIC_COMPANY_DATA = "PUBLIC_COMPANY_DATA"
    DERIVED = "DERIVED"
    SYNTHETIC = "SYNTHETIC"
    SIMULATED = "SIMULATED"
    MODEL_PREDICTED = "MODEL_PREDICTED"


class IngestionReport:
    """Structured report produced upon dataset ingestion."""

    def __init__(
        self,
        filepath: str,
        file_type: str,
        row_count: int,
        column_count: int,
        columns: List[str],
        dtypes: Dict[str, str],
        missing_counts: Dict[str, int],
        missing_percentages: Dict[str, float],
        duplicate_rows: int,
        date_columns: List[str],
        numeric_columns: List[str],
        provenance_tag: str
    ):
        self.filepath = filepath
        self.file_type = file_type
        self.row_count = row_count
        self.column_count = column_count
        self.columns = columns
        self.dtypes = dtypes
        self.missing_counts = missing_counts
        self.missing_percentages = missing_percentages
        self.duplicate_rows = duplicate_rows
        self.date_columns = date_columns
        self.numeric_columns = numeric_columns
        self.provenance_tag = provenance_tag
        self.ingested_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filepath": self.filepath,
            "file_type": self.file_type,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": self.columns,
            "dtypes": self.dtypes,
            "missing_counts": self.missing_counts,
            "missing_percentages": self.missing_percentages,
            "duplicate_rows": self.duplicate_rows,
            "date_columns": self.date_columns,
            "numeric_columns": self.numeric_columns,
            "provenance_tag": self.provenance_tag,
            "ingested_at": self.ingested_at
        }


class DataLoader:
    """Universal Loader for CSV, XLSX, XLS, and JSON files without silent column dropping."""

    @classmethod
    def load(
        cls, 
        filepath: str, 
        provenance: str = DatasetProvenance.OBSERVED_REAL_DATA,
        **kwargs
    ) -> (pd.DataFrame, IngestionReport):
        """Auto-detects file format and loads data with full telemetry."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dataset file not found at: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()

        if ext in ['.csv', '.txt']:
            return cls.load_csv(filepath, provenance=provenance, **kwargs)
        elif ext in ['.xlsx', '.xls']:
            return cls.load_excel(filepath, provenance=provenance, **kwargs)
        elif ext in ['.json']:
            return cls.load_json(filepath, provenance=provenance, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Expected CSV, Excel, or JSON.")

    @classmethod
    def load_csv(
        cls, 
        filepath: str, 
        provenance: str = DatasetProvenance.OBSERVED_REAL_DATA, 
        **kwargs
    ) -> (pd.DataFrame, IngestionReport):
        """Loads CSV files preserving all column headers and data types."""
        df = pd.read_csv(filepath, **kwargs)
        report = cls._inspect_dataframe(df, filepath, "CSV", provenance)
        return df, report

    @classmethod
    def load_excel(
        cls, 
        filepath: str, 
        sheet_name: Union[str, int] = 0,
        provenance: str = DatasetProvenance.OBSERVED_REAL_DATA,
        **kwargs
    ) -> (pd.DataFrame, IngestionReport):
        """Loads Excel spreadsheet without dropping columns."""
        df = pd.read_excel(filepath, sheet_name=sheet_name, **kwargs)
        report = cls._inspect_dataframe(df, filepath, "EXCEL", provenance)
        return df, report

    @classmethod
    def load_json(
        cls, 
        filepath: str, 
        provenance: str = DatasetProvenance.OBSERVED_REAL_DATA,
        **kwargs
    ) -> (pd.DataFrame, IngestionReport):
        """Loads JSON files (records or split format)."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Check if dict of lists or records
            if "records" in data:
                df = pd.DataFrame(data["records"])
            else:
                df = pd.DataFrame(data)
        else:
            raise ValueError("Unsupported JSON layout for tabular ingestion.")

        report = cls._inspect_dataframe(df, filepath, "JSON", provenance)
        return df, report

    @staticmethod
    def _inspect_dataframe(
        df: pd.DataFrame, 
        filepath: str, 
        file_type: str, 
        provenance: str
    ) -> IngestionReport:
        """Inspects loaded DataFrame across columns, types, nulls, duplicates, and ranges."""
        row_count = len(df)
        column_count = len(df.columns)
        columns = list(df.columns)
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

        missing_counts = df.isna().sum().to_dict()
        missing_percentages = {
            col: round((count / max(1, row_count)) * 100.0, 2)
            for col, count in missing_counts.items()
        }
        duplicate_rows = int(df.duplicated().sum())

        date_columns = []
        numeric_columns = []

        for col in df.columns:
            # Check numeric
            if pd.api.types.is_numeric_dtype(df[col]):
                numeric_columns.append(col)
            else:
                # Test for date parseability
                sample = df[col].dropna().head(10)
                if not sample.empty:
                    try:
                        pd.to_datetime(sample, errors='raise', format='mixed')
                        date_columns.append(col)
                    except Exception:
                        pass

        return IngestionReport(
            filepath=filepath,
            file_type=file_type,
            row_count=row_count,
            column_count=column_count,
            columns=columns,
            dtypes=dtypes,
            missing_counts=missing_counts,
            missing_percentages=missing_percentages,
            duplicate_rows=duplicate_rows,
            date_columns=date_columns,
            numeric_columns=numeric_columns,
            provenance_tag=provenance
        )
