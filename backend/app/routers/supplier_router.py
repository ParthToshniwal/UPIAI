"""
Supplier Account Logs and Intelligence Router.
Provides supplier performance scorecards, on-time fulfillment rates,
lead time volatility metrics, and payment balance tracking.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    SupplierLog,
    SupplierScorecard,
    SupplierIntelligenceResponse
)
from app.database import get_database
from app.services.sample_data import SAMPLE_SUPPLIERS, SAMPLE_PRODUCTS

router = APIRouter(prefix="/api/v1/suppliers", tags=["Supplier Intelligence & Logs"])


@router.get("/intelligence", response_model=SupplierIntelligenceResponse)
async def get_supplier_intelligence():
    """
    Returns supplier scorecards, delivery reliability metrics, and accounts payable balances.
    """
    db = get_database()
    suppliers_list = list(SAMPLE_SUPPLIERS)

    if db is not None:
        try:
            cursor = db.suppliers.find({}, {"_id": 0})
            db_sups = await cursor.to_list(length=100)
            if db_sups:
                suppliers_list = db_sups
        except Exception:
            pass

    # Count SKUs assigned to each supplier
    sku_counts: Dict[str, int] = {}
    for p in SAMPLE_PRODUCTS:
        sup_id = p.get("supplier_id")
        if sup_id:
            sku_counts[sup_id] = sku_counts.get(sup_id, 0) + 1

    scorecards: List[SupplierScorecard] = []
    total_on_time = 0.0
    total_pending = 0.0
    total_overdue = 0.0

    for s in suppliers_list:
        on_time = s.get("on_time_delivery_rate", 0.90)
        total_on_time += on_time
        bal = float(s.get("balance_due", 0.0))
        status = s.get("payment_status", "Paid")

        if status == "Pending":
            total_pending += bal
        elif status == "Overdue":
            total_overdue += bal

        # Reliability Tier assignment
        if on_time >= 0.92 and s.get("quality_rating", 4.0) >= 4.5:
            tier = "TIER_1_PREFERRED"
        elif on_time >= 0.85:
            tier = "TIER_2_RELIABLE"
        else:
            tier = "TIER_3_HIGH_RISK"

        scorecards.append(
            SupplierScorecard(
                supplier_id=s["supplier_id"],
                supplier_name=s["supplier_name"],
                category=s.get("category", "Components"),
                on_time_delivery_rate_pct=round(on_time * 100.0, 1),
                avg_lead_time_days=int(s.get("avg_lead_time_days", 14)),
                lead_time_variance_days=float(s.get("lead_time_variance_days", 2.0)),
                quality_score=float(s.get("quality_rating", 4.5)),
                balance_due=bal,
                payment_status=status,
                reliability_tier=tier,
                assigned_skus_count=sku_counts.get(s["supplier_id"], 0),
                active_po_recommendation_value=round(bal * 0.45, 2)
            )
        )

    avg_on_time_rate = round((total_on_time / max(1, len(suppliers_list))) * 100.0, 1)

    return SupplierIntelligenceResponse(
        total_suppliers=len(scorecards),
        average_on_time_rate=avg_on_time_rate,
        total_pending_payables=round(total_pending, 2),
        overdue_payables=round(total_overdue, 2),
        supplier_scorecards=scorecards
    )


@router.post("/log", response_model=Dict[str, Any])
async def create_or_update_supplier_log(payload: SupplierLog):
    """
    Registers or updates supplier profile, SLA ratings, and payment obligations.
    """
    supplier_dict = payload.model_dump()
    supplier_id = supplier_dict["supplier_id"]

    # Update in memory
    updated = False
    for i, s in enumerate(SAMPLE_SUPPLIERS):
        if s["supplier_id"] == supplier_id:
            SAMPLE_SUPPLIERS[i] = supplier_dict
            updated = True
            break

    if not updated:
        SAMPLE_SUPPLIERS.append(supplier_dict)

    db = get_database()
    if db is not None:
        try:
            await db.suppliers.update_one(
                {"supplier_id": supplier_id},
                {"$set": supplier_dict},
                upsert=True
            )
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Supplier record for {supplier_dict['supplier_name']} ({supplier_id}) saved successfully.",
        "supplier": supplier_dict
    }


@router.post("/pay")
async def pay_supplier_invoice(payload: Dict[str, Any]):
    """
    Simulates settling an accounts payable invoice with a supplier.
    """
    supplier_id = payload.get("supplier_id")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="Supplier ID required.")

    for s in SAMPLE_SUPPLIERS:
        if s["supplier_id"] == supplier_id:
            s["balance_due"] = 0.0
            s["payment_status"] = "Paid"
            return {
                "success": True,
                "message": f"Invoice for {s['supplier_name']} settled. Balance cleared.",
                "supplier_id": supplier_id,
                "new_balance": 0.0,
                "payment_status": "Paid"
            }

    raise HTTPException(status_code=404, detail="Supplier not found.")
