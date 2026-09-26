"""
Data Readiness & Governance Engine for UPIAI.
Evaluates data completeness per AI capability and protects the system from misleading predictions.
Outputs explicit capability statuses: AVAILABLE, LIMITED, UNAVAILABLE with clear explanations.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from ai.schema.schema_mapper import CanonicalField, UniversalSchemaMapper


class CapabilityStatus:
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"


class CapabilityReadiness:
    """Readiness assessment for a specific AI capability."""

    def __init__(
        self,
        capability: str,
        status: str,
        can_execute: bool,
        required_fields: List[str],
        present_fields: List[str],
        missing_fields: List[str],
        confidence_penalty: float,
        explanation: str,
        remediation_guidance: str
    ):
        self.capability = capability
        self.status = status
        self.can_execute = can_execute
        self.required_fields = required_fields
        self.present_fields = present_fields
        self.missing_fields = missing_fields
        self.confidence_penalty = confidence_penalty
        self.explanation = explanation
        self.remediation_guidance = remediation_guidance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability,
            "status": self.status,
            "can_execute": self.can_execute,
            "required_fields": self.required_fields,
            "present_fields": self.present_fields,
            "missing_fields": self.missing_fields,
            "confidence_penalty": round(self.confidence_penalty, 2),
            "explanation": self.explanation,
            "remediation_guidance": self.remediation_guidance
        }


class DataReadinessAuditor:
    """Rigorous pre-flight governance engine for multi-capability AI systems."""

    @classmethod
    def audit(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Audits a DataFrame (raw or mapped) and evaluates readiness across 6 major AI capabilities.
        """
        if df.empty:
            return {
                "overall_health_score": 0.0,
                "overall_tier": "DEGRADED",
                "total_records": 0,
                "capabilities": {},
                "summary_warnings": ["Dataset is empty. No predictions can be made."]
            }

        # Step 1: Canonical schema mapping
        mapped_df, mapping_summary = UniversalSchemaMapper.map_schema(df)
        cols = set(mapped_df.columns)
        total_rows = len(mapped_df)

        # Check temporal coverage
        date_col = CanonicalField.TRANSACTION_DATETIME if CanonicalField.TRANSACTION_DATETIME in cols else None
        span_days = 0
        if date_col:
            try:
                dts = pd.to_datetime(mapped_df[date_col], errors='coerce').dropna()
                if not dts.empty:
                    span_days = (dts.max() - dts.min()).days + 1
            except Exception:
                span_days = 0

        capabilities: Dict[str, CapabilityReadiness] = {}
        summary_warnings: List[str] = []

        # -------------------------------------------------------------
        # 1. DEMAND FORECASTING READINESS
        # -------------------------------------------------------------
        has_target = CanonicalField.UNITS_SOLD in cols
        has_date = CanonicalField.TRANSACTION_DATETIME in cols
        has_product = (CanonicalField.PRODUCT_ID in cols) or (CanonicalField.PRODUCT_CATEGORY in cols)

        if has_target and has_date and has_product:
            if total_rows >= 30 and span_days >= 14:
                status = CapabilityStatus.AVAILABLE
                can_exec = True
                penalty = 0.0
                expl = "Demand forecasting is available with continuous historical sales observations."
                remed = "Ready for autoregressive and machine learning forecasting."
            else:
                status = CapabilityStatus.LIMITED
                can_exec = True
                penalty = 25.0
                expl = f"Demand forecasting is limited due to short observation span ({span_days} days, {total_rows} rows). Falling back to moving average with trend."
                remed = "Ingest 60+ days of sales records for high-confidence multi-lag XGBoost training."
                summary_warnings.append(expl)
        else:
            status = CapabilityStatus.UNAVAILABLE
            can_exec = False
            penalty = 100.0
            missing = [f for f, present in [("units_sold", has_target), ("transaction_date", has_date), ("product_id/category", has_product)] if not present]
            expl = f"Demand forecasting is unavailable because core sales metrics ({', '.join(missing)}) are missing."
            remed = f"Provide columns representing: {', '.join(missing)}."
            summary_warnings.append(expl)

        capabilities["demand_forecasting"] = CapabilityReadiness(
            capability="Demand Forecasting",
            status=status,
            can_execute=can_exec,
            required_fields=[CanonicalField.UNITS_SOLD, CanonicalField.TRANSACTION_DATETIME, CanonicalField.PRODUCT_ID],
            present_fields=[c for c in [CanonicalField.UNITS_SOLD, CanonicalField.TRANSACTION_DATETIME, CanonicalField.PRODUCT_ID, CanonicalField.PRODUCT_CATEGORY] if c in cols],
            missing_fields=[f for f in ["units_sold", "transaction_datetime", "product_id"] if f not in cols],
            confidence_penalty=penalty,
            explanation=expl,
            remediation_guidance=remed
        )

        # -------------------------------------------------------------
        # 2. STOCKOUT PREDICTION READINESS
        # -------------------------------------------------------------
        has_stock = CanonicalField.CURRENT_STOCK in cols

        if has_stock and capabilities["demand_forecasting"].can_execute:
            status = CapabilityStatus.AVAILABLE
            can_exec = True
            penalty = 0.0
            expl = "Stockout prediction is available using active stock-on-hand balances and demand velocity."
            remed = "Active real-time inventory tracking enabled."
        elif not has_stock and capabilities["demand_forecasting"].can_execute:
            status = CapabilityStatus.UNAVAILABLE
            can_exec = False
            penalty = 40.0
            expl = "Stockout prediction is unavailable because current stock on hand was not provided in the dataset."
            remed = "Map your ERP/WMS stock inventory column (e.g. 'stock', 'available_stock') to unlock stockout depletion alerts."
            summary_warnings.append(expl)
        else:
            status = CapabilityStatus.UNAVAILABLE
            can_exec = False
            penalty = 100.0
            expl = "Stockout prediction is unavailable because both inventory balances and demand forecasts are missing."
            remed = "Ingest sales records and warehouse inventory balances."
            summary_warnings.append(expl)

        capabilities["stockout_prediction"] = CapabilityReadiness(
            capability="Stockout Prediction",
            status=status,
            can_execute=can_exec,
            required_fields=[CanonicalField.CURRENT_STOCK, CanonicalField.UNITS_SOLD],
            present_fields=[c for c in [CanonicalField.CURRENT_STOCK] if c in cols],
            missing_fields=[f for f in ["current_stock"] if f not in cols],
            confidence_penalty=penalty,
            explanation=expl,
            remediation_guidance=remed
        )

        # -------------------------------------------------------------
        # 3. REORDER OPTIMIZATION & PO SIZING
        # -------------------------------------------------------------
        has_lead_time = CanonicalField.LEAD_TIME_DAYS in cols
        has_supplier = CanonicalField.SUPPLIER_ID in cols or CanonicalField.SUPPLIER_NAME in cols

        if has_stock and has_lead_time and capabilities["demand_forecasting"].can_execute:
            status = CapabilityStatus.AVAILABLE
            can_exec = True
            penalty = 0.0
            expl = "Reorder optimization is fully available with verified supplier lead times and stock buffers."
            remed = "Purchase order sizing running at optimal accuracy."
        elif has_stock and not has_lead_time and capabilities["demand_forecasting"].can_execute:
            status = CapabilityStatus.LIMITED
            can_exec = True
            penalty = 20.0
            expl = "Reorder optimization is limited because supplier lead time is missing. Defaulted to conservative 14-day SLA buffer (+25% safety stock)."
            remed = "Provide supplier lead time records to optimize working capital buffers."
            summary_warnings.append(expl)
        else:
            status = CapabilityStatus.UNAVAILABLE
            can_exec = False
            penalty = 80.0
            expl = "Reorder optimization is unavailable because inventory balances are missing."
            remed = "Upload stock-on-hand levels and supplier lead time schedules."
            summary_warnings.append(expl)

        capabilities["reorder_optimization"] = CapabilityReadiness(
            capability="Reorder Optimization",
            status=status,
            can_execute=can_exec,
            required_fields=[CanonicalField.CURRENT_STOCK, CanonicalField.LEAD_TIME_DAYS, CanonicalField.UNITS_SOLD],
            present_fields=[c for c in [CanonicalField.CURRENT_STOCK, CanonicalField.LEAD_TIME_DAYS] if c in cols],
            missing_fields=[f for f in ["current_stock", "lead_time_days"] if f not in cols],
            confidence_penalty=penalty,
            explanation=expl,
            remediation_guidance=remed
        )

        # -------------------------------------------------------------
        # 4. SUPPLIER INTELLIGENCE & SLA TRACKING
        # -------------------------------------------------------------
        if has_supplier and has_lead_time:
            status = CapabilityStatus.AVAILABLE
            can_exec = True
            penalty = 0.0
            expl = "Supplier intelligence is available for vendor performance scorecards and SLA monitoring."
            remed = "Supplier reliability tracking operational."
        elif has_supplier and not has_lead_time:
            status = CapabilityStatus.LIMITED
            can_exec = True
            penalty = 30.0
            expl = "Supplier intelligence is limited because lead times and delivery variance records are absent."
            remed = "Ingest purchase order fulfillment dates and delivery timelines."
            summary_warnings.append(expl)
        else:
            status = CapabilityStatus.UNAVAILABLE
            can_exec = False
            penalty = 50.0
            expl = "Supplier intelligence is unavailable because supplier identifier was not provided."
            remed = "Include 'supplier_id' or 'vendor_name' in your dataset."
            summary_warnings.append(expl)

        capabilities["supplier_intelligence"] = CapabilityReadiness(
            capability="Supplier Intelligence",
            status=status,
            can_execute=can_exec,
            required_fields=[CanonicalField.SUPPLIER_ID, CanonicalField.LEAD_TIME_DAYS],
            present_fields=[c for c in [CanonicalField.SUPPLIER_ID, CanonicalField.SUPPLIER_NAME, CanonicalField.LEAD_TIME_DAYS] if c in cols],
            missing_fields=[f for f in ["supplier_id", "lead_time_days"] if f not in cols],
            confidence_penalty=penalty,
            explanation=expl,
            remediation_guidance=remed
        )

        # -------------------------------------------------------------
        # 5. PROFITABILITY & MARGIN ANALYSIS
        # -------------------------------------------------------------
        has_price = CanonicalField.UNIT_PRICE in cols or CanonicalField.TOTAL_AMOUNT in cols
        has_cost = CanonicalField.UNIT_COST in cols

        if has_price and has_cost and has_target:
            status = CapabilityStatus.AVAILABLE
            can_exec = True
            penalty = 0.0
            expl = "Profit and margin analysis is fully available with verified retail price and wholesale unit cost."
            remed = "Margin analytics enabled."
        elif has_price and not has_cost and has_target:
            status = CapabilityStatus.LIMITED
            can_exec = True
            penalty = 15.0
            expl = "Profit analysis is limited: Product unit cost absent. Inventory valuation approximated using 65% COGS margin proxy."
            remed = "Provide unit cost or COGS to calculate exact profit contributions."
            summary_warnings.append(expl)
        else:
            status = CapabilityStatus.UNAVAILABLE
            can_exec = False
            penalty = 60.0
            expl = "Profit analysis is unavailable because selling price or sales volume is missing."
            remed = "Provide unit price and quantity sold."
            summary_warnings.append(expl)

        capabilities["profit_analysis"] = CapabilityReadiness(
            capability="Profit Analysis",
            status=status,
            can_execute=can_exec,
            required_fields=[CanonicalField.UNIT_PRICE, CanonicalField.UNIT_COST, CanonicalField.UNITS_SOLD],
            present_fields=[c for c in [CanonicalField.UNIT_PRICE, CanonicalField.UNIT_COST, CanonicalField.TOTAL_AMOUNT] if c in cols],
            missing_fields=[f for f in ["unit_price", "unit_cost"] if f not in cols],
            confidence_penalty=penalty,
            explanation=expl,
            remediation_guidance=remed
        )

        # -------------------------------------------------------------
        # 6. SEASONALITY & FESTIVAL ANALYSIS
        # -------------------------------------------------------------
        if has_date and span_days >= 60:
            status = CapabilityStatus.AVAILABLE
            can_exec = True
            penalty = 0.0
            expl = f"Seasonality analysis is available with {span_days} days of historical continuity."
            remed = "Day-of-week, monthly, and holiday demand lift models active."
        elif has_date and span_days >= 14:
            status = CapabilityStatus.LIMITED
            can_exec = True
            penalty = 20.0
            expl = f"Seasonality analysis is limited: Historical depth is {span_days} days. Short-term weekly seasonality active, but annual festival cycles cannot be verified."
            remed = "Provide 180-365 days of sales records to unlock annual festival & quarterly seasonality."
            summary_warnings.append(expl)
        else:
            status = CapabilityStatus.UNAVAILABLE
            can_exec = False
            penalty = 50.0
            expl = "Seasonality analysis is unavailable due to lack of continuous date timestamps."
            remed = "Include valid transaction timestamps."
            summary_warnings.append(expl)

        capabilities["seasonality_analysis"] = CapabilityReadiness(
            capability="Seasonality Analysis",
            status=status,
            can_execute=can_exec,
            required_fields=[CanonicalField.TRANSACTION_DATETIME],
            present_fields=[c for c in [CanonicalField.TRANSACTION_DATETIME] if c in cols],
            missing_fields=[f for f in ["transaction_datetime"] if f not in cols],
            confidence_penalty=penalty,
            explanation=expl,
            remediation_guidance=remed
        )

        # Calculate Overall Health Score
        avg_penalty = sum(c.confidence_penalty for c in capabilities.values()) / len(capabilities)
        overall_score = max(5.0, min(100.0, round(100.0 - avg_penalty, 1)))

        if overall_score >= 80.0 and capabilities["demand_forecasting"].can_execute:
            tier = "HIGH_CONFIDENCE"
        elif overall_score >= 50.0 and capabilities["demand_forecasting"].can_execute:
            tier = "MODERATE_CONFIDENCE"
        else:
            tier = "DEGRADED"

        return {
            "overall_health_score": overall_score,
            "overall_tier": tier,
            "total_records": total_rows,
            "data_span_days": span_days,
            "mapped_columns_count": mapping_summary["mapped_columns_count"],
            "unmapped_columns": mapping_summary["unmapped_columns"],
            "capabilities": {k: v.to_dict() for k, v in capabilities.items()},
            "summary_warnings": summary_warnings,
            "can_proceed_to_forecast": capabilities["demand_forecasting"].can_execute
        }
