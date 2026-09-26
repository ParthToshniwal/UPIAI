"""
Supplier Intelligence & SLA Reliability Scorer for UPIAI.
Evaluates fulfillment accuracy, lead-time volatility, quality metrics,
and accounts payable balances with multi-tier risk classification.
"""

from typing import Dict, Any, List, Optional
import numpy as np


class SupplierTier:
    TIER_1_PREFERRED = "TIER_1_PREFERRED"
    TIER_2_RELIABLE = "TIER_2_RELIABLE"
    TIER_3_HIGH_RISK = "TIER_3_HIGH_RISK"


class SupplierScorer:
    """Computes vendor performance scorecards and financial ledger balances."""

    @classmethod
    def score_supplier(
        cls,
        supplier_id: str,
        supplier_name: str,
        category: str,
        on_time_delivery_rate: float,
        avg_lead_time_days: int,
        lead_time_variance_days: float,
        quality_rating: float,
        balance_due: float,
        payment_status: str,
        payment_terms: str = "Net 30"
    ) -> Dict[str, Any]:
        """
        Produces a standardized supplier scorecard and SLA risk index.
        """
        # Composite Reliability Index (0 - 100)
        # 50% on-time delivery + 30% quality rating + 20% lead time stability
        variance_penalty = min(20.0, (lead_time_variance_days / max(1.0, float(avg_lead_time_days))) * 40.0)
        quality_component = (quality_rating / 5.0) * 30.0
        on_time_component = (on_time_delivery_rate) * 50.0

        composite_score = round(max(0.0, min(100.0, on_time_component + quality_component + (20.0 - variance_penalty))), 1)

        # Tier assignment
        if on_time_delivery_rate >= 0.92 and quality_rating >= 4.5 and lead_time_variance_days <= 3.5:
            tier = SupplierTier.TIER_1_PREFERRED
        elif on_time_delivery_rate >= 0.85:
            tier = SupplierTier.TIER_2_RELIABLE
        else:
            tier = SupplierTier.TIER_3_HIGH_RISK

        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "category": category,
            "composite_reliability_score": composite_score,
            "reliability_tier": tier,
            "on_time_delivery_rate_pct": round(on_time_delivery_rate * 100.0, 1),
            "avg_lead_time_days": avg_lead_time_days,
            "lead_time_variance_days": round(lead_time_variance_days, 1),
            "quality_rating_5": round(quality_rating, 1),
            "payment_terms": payment_terms,
            "balance_due": round(balance_due, 2),
            "payment_status": payment_status
        }
