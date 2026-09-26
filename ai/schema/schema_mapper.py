"""
Universal Schema Mapper for UPIAI.
Automates column aliasing and canonical mapping across arbitrary business ERPs and sales logs.
Outputs confidence scores and provenance attribution for each mapped attribute.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import pandas as pd


class CanonicalField:
    """Canonical schema definitions with alias regular expressions and semantic priorities."""
    UNITS_SOLD = "units_sold"
    PRODUCT_ID = "product_id"
    PRODUCT_CATEGORY = "product_category"
    PRODUCT_NAME = "product_name"
    TRANSACTION_DATETIME = "transaction_datetime"
    TRANSACTION_TIME = "transaction_time"
    UNIT_PRICE = "unit_price"
    UNIT_COST = "unit_cost"
    TOTAL_AMOUNT = "total_amount"
    STORE_ID = "store_id"
    CUSTOMER_TYPE = "customer_type"
    CUSTOMER_NAME = "customer_name"
    CURRENT_STOCK = "current_stock"
    LEAD_TIME_DAYS = "lead_time_days"
    SUPPLIER_ID = "supplier_id"
    SUPPLIER_NAME = "supplier_name"


SCHEMA_SYNONYM_REGISTRY = {
    CanonicalField.UNITS_SOLD: {
        "exact": ["units_sold", "quantity", "qty", "units", "sales_qty", "quantity_sold", "sales_volume", "volume", "sold_qty", "qty_sold"],
        "pattern": r"(qty|quantity|units|volume|sold)",
        "confidence_base": 0.95
    },
    CanonicalField.PRODUCT_ID: {
        "exact": ["product_id", "sku", "sku_id", "item_id", "product_code", "part_number", "item_code", "item_no", "upc", "asin", "ean"],
        "pattern": r"(sku|product.*id|item.*id|part.*no|product.*code)",
        "confidence_base": 0.95
    },
    CanonicalField.PRODUCT_CATEGORY: {
        "exact": ["product_category", "productcategory", "category", "cat", "dept", "department", "segment", "product_group", "item_category"],
        "pattern": r"(category|department|segment|prod.*cat)",
        "confidence_base": 0.92
    },
    CanonicalField.PRODUCT_NAME: {
        "exact": ["product_name", "productname", "item_name", "description", "title", "name", "item_description"],
        "pattern": r"(product.*name|item.*name|description)",
        "confidence_base": 0.90
    },
    CanonicalField.TRANSACTION_DATETIME: {
        "exact": ["date", "transaction_date", "order_date", "sale_date", "timestamp", "datetime", "created_at", "invoice_date", "billing_date"],
        "pattern": r"(date|timestamp|created|invoice.*date)",
        "confidence_base": 0.98
    },
    CanonicalField.TRANSACTION_TIME: {
        "exact": ["time", "transaction_time", "order_time", "sale_time", "timestamp_time"],
        "pattern": r"(^time$|order.*time|txn.*time)",
        "confidence_base": 0.95
    },
    CanonicalField.UNIT_PRICE: {
        "exact": ["unit_price", "unitprice", "price", "selling_price", "retail_price", "sale_price", "item_price", "mrp", "rate"],
        "pattern": r"(unit.*price|price|rate|mrp|selling.*price)",
        "confidence_base": 0.94
    },
    CanonicalField.UNIT_COST: {
        "exact": ["unit_cost", "unitcost", "cost", "cost_price", "cogs", "purchase_price", "wholesale_price", "buy_price"],
        "pattern": r"(cost|cogs|purchase.*price|wholesale)",
        "confidence_base": 0.94
    },
    CanonicalField.TOTAL_AMOUNT: {
        "exact": ["total", "total_amount", "amount", "sales_total", "total_price", "net_amount", "gross_amount", "revenue", "line_total"],
        "pattern": r"(total.*amount|^total$|revenue|net.*amount)",
        "confidence_base": 0.96
    },
    CanonicalField.STORE_ID: {
        "exact": ["store_id", "store", "branch", "shop_id", "location_id", "outlet_id", "warehouse_id", "pos_id"],
        "pattern": r"(store|branch|shop|outlet|location)",
        "confidence_base": 0.90
    },
    CanonicalField.CUSTOMER_TYPE: {
        "exact": ["customer_type", "customertype", "client_type", "membership_type", "buyer_type", "segment"],
        "pattern": r"(customer.*type|member.*type|client.*type)",
        "confidence_base": 0.93
    },
    CanonicalField.CUSTOMER_NAME: {
        "exact": ["full_name", "fullname", "customer_name", "client_name", "buyer_name", "customer"],
        "pattern": r"(full.*name|cust.*name|client.*name)",
        "confidence_base": 0.93
    },
    CanonicalField.CURRENT_STOCK: {
        "exact": ["current_stock", "stock", "stock_on_hand", "available_stock", "qty_on_hand", "inventory_level", "stock_qty"],
        "pattern": r"(stock|inventory|on.*hand)",
        "confidence_base": 0.92
    },
    CanonicalField.LEAD_TIME_DAYS: {
        "exact": ["lead_time_days", "lead_time", "supplier_lead_time", "delivery_days", "replenishment_time", "leadtime"],
        "pattern": r"(lead.*time|delivery.*days|replenish)",
        "confidence_base": 0.95
    },
    CanonicalField.SUPPLIER_ID: {
        "exact": ["supplier_id", "vendor_id", "supplier", "vendor", "distributor_id"],
        "pattern": r"(supplier.*id|vendor.*id|^supplier$|^vendor$)",
        "confidence_base": 0.90
    }
}


class ColumnMapping:
    """Individual column mapping metadata."""
    def __init__(
        self,
        source_column: str,
        canonical_column: str,
        confidence: float,
        match_type: str,
        inferred: bool = False
    ):
        self.source_column = source_column
        self.canonical_column = canonical_column
        self.confidence = confidence
        self.match_type = match_type
        self.inferred = inferred

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_column": self.source_column,
            "canonical_column": self.canonical_column,
            "confidence": round(self.confidence, 4),
            "match_type": self.match_type,
            "inferred": self.inferred
        }


class UniversalSchemaMapper:
    """Intelligently detects column semantics and remaps arbitrary DataFrames to canonical models."""

    @classmethod
    def map_schema(
        cls, 
        df: pd.DataFrame, 
        min_confidence: float = 0.5
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Maps DataFrame columns to canonical schema representation with confidence logging."""
        mapped_df = df.copy()
        mappings: List[ColumnMapping] = []
        mapped_dict: Dict[str, str] = {}
        unmapped_columns: List[str] = []
        claimed_canonicals: Dict[str, Tuple[str, float]] = {}

        source_columns = list(df.columns)

        for src_col in source_columns:
            clean_name = str(src_col).strip().lower().replace(" ", "_").replace("-", "_")
            best_match: Optional[str] = None
            best_conf: float = 0.0
            match_type: str = "NONE"

            for canonical, rules in SCHEMA_SYNONYM_REGISTRY.items():
                # 1. Exact alias match
                if clean_name in [e.lower() for e in rules["exact"]]:
                    best_match = canonical
                    best_conf = rules["confidence_base"]
                    match_type = "EXACT_ALIAS"
                    break

                # 2. Regex pattern match
                if re.search(rules["pattern"], clean_name, re.IGNORECASE):
                    conf = rules["confidence_base"] * 0.85
                    if conf > best_conf:
                        best_match = canonical
                        best_conf = conf
                        match_type = "FUZZY_PATTERN"

            if best_match and best_conf >= min_confidence:
                # Resolve canonical collision if another column already claimed it
                if best_match in claimed_canonicals:
                    existing_src, existing_conf = claimed_canonicals[best_match]
                    if best_conf > existing_conf:
                        # Replace previous
                        claimed_canonicals[best_match] = (src_col, best_conf)
                        mappings = [m for m in mappings if m.canonical_column != best_match]
                        unmapped_columns.append(existing_src)
                        mappings.append(ColumnMapping(src_col, best_match, best_conf, match_type))
                        mapped_dict[src_col] = best_match
                    else:
                        unmapped_columns.append(src_col)
                else:
                    claimed_canonicals[best_match] = (src_col, best_conf)
                    mappings.append(ColumnMapping(src_col, best_match, best_conf, match_type))
                    mapped_dict[src_col] = best_match
            else:
                unmapped_columns.append(src_col)

        # Standardize renamed DataFrame
        mapped_df = mapped_df.rename(columns=mapped_dict)

        # Handle derived/fallback fields (e.g. Total = Quantity * UnitPrice if Total is missing)
        derived_actions = []
        if (
            CanonicalField.TOTAL_AMOUNT not in mapped_df.columns and
            CanonicalField.UNITS_SOLD in mapped_df.columns and
            CanonicalField.UNIT_PRICE in mapped_df.columns
        ):
            mapped_df[CanonicalField.TOTAL_AMOUNT] = (
                pd.to_numeric(mapped_df[CanonicalField.UNITS_SOLD], errors='coerce') *
                pd.to_numeric(mapped_df[CanonicalField.UNIT_PRICE], errors='coerce')
            )
            derived_actions.append("Synthesized 'total_amount' via units_sold * unit_price (Provenance: DERIVED)")

        mapping_summary = {
            "total_source_columns": len(source_columns),
            "mapped_columns_count": len(mappings),
            "unmapped_columns_count": len(unmapped_columns),
            "mappings": [m.to_dict() for m in mappings],
            "unmapped_columns": unmapped_columns,
            "derived_actions": derived_actions
        }

        return mapped_df, mapping_summary
