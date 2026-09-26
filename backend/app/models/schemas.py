"""
Pydantic schemas and data models for UPIAI.
Enforces strict typing and validation across business profiles, inventory, sales,
suppliers, data readiness engine, and ML demand forecasting pipelines.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Business Profile & Master Entities
# ---------------------------------------------------------------------------

class BusinessProfile(BaseModel):
    business_id: str = Field(..., example="BIZ-1001", description="Unique identifier for business entity")
    business_name: str = Field(..., example="Apex Global Electronics", description="Legal or operating business name")
    industry_sector: str = Field(..., example="Retail & Consumer Tech", description="Industry vertical")
    currency: str = Field(default="USD", example="USD")
    target_service_level: float = Field(default=0.95, ge=0.5, le=0.999, description="Target fulfillment rate (e.g. 95%)")
    default_lead_time_days: int = Field(default=14, ge=1, le=365)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)


class ProductMaster(BaseModel):
    sku: str = Field(..., example="TECH-4090-GPU", description="Stock Keeping Unit code")
    name: str = Field(..., example="GeForce RTX 4090 OC 24GB")
    category: str = Field(..., example="Hardware / Graphics")
    unit_cost: float = Field(..., ge=0.0, description="Cost of goods sold (COGS) per unit")
    unit_price: float = Field(..., ge=0.0, description="Retail selling price per unit")
    current_stock: int = Field(default=0, ge=0, description="Physical units in warehouse")
    reserved_stock: int = Field(default=0, ge=0, description="Units allocated to pending orders")
    on_order_stock: int = Field(default=0, ge=0, description="Units ordered from supplier in transit")
    lead_time_days: int = Field(default=14, ge=1, description="Supplier replenishment lead time")
    reorder_point: Optional[int] = Field(default=None, ge=0)
    safety_stock: Optional[int] = Field(default=None, ge=0)
    supplier_id: Optional[str] = Field(default=None, example="SUP-001")
    supplier_name: Optional[str] = Field(default=None, example="MicroChip Global Ltd")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)


class SalesRecord(BaseModel):
    date: str = Field(..., example="2026-09-01", description="Date of sale (YYYY-MM-DD)")
    sku: str = Field(..., example="TECH-4090-GPU")
    units_sold: int = Field(..., ge=0, description="Quantity sold")
    unit_price: Optional[float] = Field(default=None, ge=0.0)
    channel: Optional[str] = Field(default="E-Commerce", example="E-Commerce")
    discount: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    is_promotion: Optional[bool] = Field(default=False)

    model_config = ConfigDict(populate_by_name=True)


class InventoryState(BaseModel):
    sku: str = Field(...)
    warehouse_id: str = Field(default="WH-CENTRAL-01")
    available_stock: int = Field(..., ge=0)
    reserved_stock: int = Field(default=0, ge=0)
    on_order_stock: int = Field(default=0, ge=0)
    unit_cost: float = Field(default=0.0, ge=0.0)
    last_restocked_at: Optional[datetime] = None


class SupplierLog(BaseModel):
    supplier_id: str = Field(..., example="SUP-001")
    supplier_name: str = Field(..., example="Silicon Horizons Manufacturing")
    category: str = Field(default="Components", example="Semiconductors")
    avg_lead_time_days: int = Field(..., ge=1, example=12)
    on_time_delivery_rate: float = Field(..., ge=0.0, le=1.0, example=0.94, description="Fulfillment accuracy (0-1)")
    quality_rating: float = Field(..., ge=1.0, le=5.0, example=4.8, description="Rating out of 5.0")
    payment_terms: str = Field(default="Net 30", example="Net 30")
    balance_due: float = Field(default=0.0, ge=0.0, example=18500.0)
    payment_status: str = Field(default="Paid", example="Pending", description="Paid, Pending, or Overdue")
    contact_email: str = Field(default="accounts@siliconhorizons.com")
    country: str = Field(default="Taiwan")
    last_audit_date: Optional[str] = Field(default="2026-09-20")

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Data Readiness & Provenance Engine Models
# ---------------------------------------------------------------------------

class ColumnAuditResult(BaseModel):
    column_name: str
    status: str = Field(..., description="PRESENT, MISSING, or INFERRED")
    data_type: str
    missing_count: int
    missing_percentage: float
    importance: str = Field(..., description="CRITICAL, HIGH, MEDIUM, or OPTIONAL")
    impact_description: str


class ReadinessScorecardResponse(BaseModel):
    overall_readiness_score: float = Field(..., ge=0.0, le=100.0, description="Overall dataset health (0-100)")
    operational_tier: str = Field(..., description="HIGH_CONFIDENCE, MODERATE_CONFIDENCE, or DEGRADED")
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


class ReadinessAuditRequest(BaseModel):
    dataset: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Raw dataset rows as JSON. If empty, engine audits active database tables."
    )
    dataset_name: Optional[str] = Field(default="Uploaded Raw Dataset")


# ---------------------------------------------------------------------------
# Demand Forecasting & AI Inventory Intelligence Models
# ---------------------------------------------------------------------------

class ForecastHorizonPrediction(BaseModel):
    day_offset: int
    forecast_date: str
    predicted_units: float
    lower_bound_90: float
    upper_bound_90: float


class StockoutRiskAssessment(BaseModel):
    risk_level: str = Field(..., description="CRITICAL, WARNING, OPTIMAL, or OVERSTOCKED")
    stockout_probability_pct: float = Field(..., ge=0.0, le=100.0)
    estimated_days_of_supply: float
    projected_stockout_date: Optional[str] = None
    estimated_revenue_at_risk: float = Field(default=0.0)


class ReorderRecommendation(BaseModel):
    sku: str
    product_name: str
    category: str
    current_stock: int
    on_order: int
    lead_time_days: int
    reorder_point: int
    safety_stock: int
    recommended_order_quantity: int
    estimated_order_cost: float
    preferred_supplier_id: Optional[str] = None
    preferred_supplier_name: Optional[str] = None
    urgency: str = Field(..., description="IMMEDIATE, PLAN_THIS_WEEK, NORMAL, NO_ACTION")
    rationale: str


class SKUForecastDetail(BaseModel):
    sku: str
    product_name: str
    category: str
    current_stock: int
    unit_cost: float
    unit_price: float
    forecast_7d_total: float
    forecast_30d_total: float
    daily_average_velocity: float
    risk_assessment: StockoutRiskAssessment
    reorder_recommendation: ReorderRecommendation
    daily_trajectory_30d: List[ForecastHorizonPrediction]


class ForecastRequest(BaseModel):
    skus: Optional[List[str]] = Field(default=None, description="Filter forecast by specific SKU list. None = all SKUs.")
    historical_days_lookback: int = Field(default=90, ge=14, le=730)
    forecast_horizon_days: int = Field(default=30, ge=7, le=90)
    include_daily_trajectories: bool = Field(default=True)
    custom_sales_data: Optional[List[Dict[str, Any]]] = None


class ForecastResponse(BaseModel):
    generated_at: str
    model_type_used: str
    total_skus_analyzed: int
    critical_stockout_count: int
    warning_count: int
    total_inventory_value: float
    total_capital_at_risk: float
    total_recommended_reorder_cost: float
    sku_forecasts: List[SKUForecastDetail]


# ---------------------------------------------------------------------------
# Supplier Intelligence Models
# ---------------------------------------------------------------------------

class SupplierScorecard(BaseModel):
    supplier_id: str
    supplier_name: str
    category: str
    on_time_delivery_rate_pct: float
    avg_lead_time_days: int
    lead_time_variance_days: float
    quality_score: float
    balance_due: float
    payment_status: str
    reliability_tier: str = Field(..., description="TIER_1_PREFERRED, TIER_2_RELIABLE, TIER_3_HIGH_RISK")
    assigned_skus_count: int
    active_po_recommendation_value: float


class SupplierIntelligenceResponse(BaseModel):
    total_suppliers: int
    average_on_time_rate: float
    total_pending_payables: float
    overdue_payables: float
    supplier_scorecards: List[SupplierScorecard]


# ---------------------------------------------------------------------------
# Executive KPI Response
# ---------------------------------------------------------------------------

class ExecutiveKPIResponse(BaseModel):
    total_revenue_30d_projected: float
    total_inventory_value: float
    capital_tied_up_excess: float
    stockout_risk_percentage: float
    critical_skus_count: int
    supplier_reliability_index: float
    system_readiness_score: float
    dataset_health_label: str
    pending_reorder_budget: float
