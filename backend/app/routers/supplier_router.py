"""
Supplier Account Logs and Intelligence Router for DMart Retail Logistics.
Provides supplier performance scorecards, on-time fulfillment rates,
lead time volatility metrics, and accounts payable ledger tracking via Turso.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

try:
    from app.models.schemas import (
        SupplierLog,
        SupplierScorecard,
        SupplierIntelligenceResponse
    )
    from app.database import turso_db
except ImportError:
    from backend.app.models.schemas import (
        SupplierLog,
        SupplierScorecard,
        SupplierIntelligenceResponse
    )
    from backend.app.database import turso_db

try:
    from ai.suppliers.scorer import SupplierScorer
except ImportError:
    SupplierScorer = None

router = APIRouter(prefix="/api/v1/suppliers", tags=["Supplier Intelligence & Logs"])


@router.get("", response_model=SupplierIntelligenceResponse)
@router.get("/intelligence", response_model=SupplierIntelligenceResponse)
async def get_supplier_intelligence():
    """
    Returns supplier scorecards, delivery reliability metrics, and accounts payable balances.
    """
    suppliers_list = turso_db.get_suppliers()
    inv_items = turso_db.get_inventory_items()

    # Count SKUs assigned to each supplier
    sku_counts: Dict[str, int] = {}
    for p in inv_items:
        sup_id = p.get("supplier_id")
        if sup_id:
            sku_counts[sup_id] = sku_counts.get(sup_id, 0) + 1

    scorecards: List[SupplierScorecard] = []
    total_on_time = 0.0
    total_pending = 0.0
    total_overdue = 0.0

    for s in suppliers_list:
        on_time = float(s.get("on_time_delivery_rate", 0.90))
        total_on_time += on_time
        bal = float(s.get("balance_due", 0.0))
        status = s.get("payment_status", "Paid")
        quality = float(s.get("quality_rating", 4.5))
        lead_time = int(s.get("avg_lead_time_days", 7))

        if status == "Pending":
            total_pending += bal
        elif status == "Overdue":
            total_overdue += bal

        # Evaluate supplier with AI SupplierScorer if available
        if SupplierScorer:
            scored = SupplierScorer.score_supplier(
                supplier_id=s["supplier_id"],
                supplier_name=s["supplier_name"],
                category=s.get("category", "Grocery"),
                on_time_delivery_rate=on_time,
                avg_lead_time_days=lead_time,
                lead_time_variance_days=1.5,
                quality_rating=quality,
                balance_due=bal,
                payment_status=status,
                payment_terms=s.get("payment_terms", "Net 30")
            )
            tier = scored["reliability_tier"]
            on_time_pct = scored["on_time_delivery_rate_pct"]
        else:
            if on_time >= 0.92 and quality >= 4.5:
                tier = "TIER_1_PREFERRED"
            elif on_time >= 0.85:
                tier = "TIER_2_RELIABLE"
            else:
                tier = "TIER_3_HIGH_RISK"
            on_time_pct = round(on_time * 100.0, 1)

        scorecards.append(
            SupplierScorecard(
                supplier_id=s["supplier_id"],
                supplier_name=s["supplier_name"],
                category=s.get("category", "Grocery"),
                on_time_delivery_rate_pct=on_time_pct,
                avg_lead_time_days=lead_time,
                lead_time_variance_days=1.5,
                quality_score=quality,
                balance_due=bal,
                payment_status=status,
                reliability_tier=tier,
                assigned_skus_count=sku_counts.get(s["supplier_id"], 1),
                active_po_recommendation_value=round(bal * 0.40, 2)
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


@router.post("/pay")
async def pay_supplier_invoice(payload: Dict[str, Any]):
    """
    Settles an accounts payable invoice with a DMart regional supplier in Turso.
    """
    supplier_id = payload.get("supplier_id")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="Supplier ID required.")

    success = turso_db.settle_supplier_invoice(supplier_id)
    if success:
        return {
            "success": True,
            "message": f"Invoice for supplier {supplier_id} settled. Balance cleared in Turso.",
            "supplier_id": supplier_id,
            "new_balance": 0.0,
            "payment_status": "Paid"
        }

    raise HTTPException(status_code=404, detail="Supplier not found or balance already zero.")
