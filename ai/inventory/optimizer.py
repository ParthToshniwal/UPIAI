"""
Inventory Intelligence & Dynamic Reorder Optimization Engine for UPIAI.
Calculates days-of-supply depletion timelines, stockout risk probabilities,
overstock capital burdens, and automated purchase order sizes with urgency classification.
"""

from typing import Dict, Any, List, Optional
import numpy as np


class InventoryRiskTier:
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    OPTIMAL = "OPTIMAL"
    OVERSTOCKED = "OVERSTOCKED"


class InventoryOptimizer:
    """Calculates stockout exposure, overstock capital, and automated purchase order recommendations."""

    @classmethod
    def evaluate_sku_inventory(
        cls,
        sku: str,
        product_name: str,
        current_stock: int,
        on_order_stock: int,
        daily_velocity: float,
        daily_std: float,
        unit_cost: float,
        unit_price: float,
        lead_time_days: int = 14,
        lead_time_std_days: float = 2.0,
        service_level_z: float = 1.645
    ) -> Dict[str, Any]:
        """
        Evaluates stock health, stockout risk, and automated replenishment for a single SKU.
        """
        safe_velocity = max(0.05, float(daily_velocity))
        days_of_supply = round(current_stock / safe_velocity, 1)

        # 1. Safety Stock Calculation
        # SS = Z * sqrt( (LT * sigma_demand^2) + (avg_demand^2 * sigma_LT^2) )
        combined_variance = (lead_time_days * (daily_std ** 2)) + ((safe_velocity ** 2) * (lead_time_std_days ** 2))
        safety_stock = max(2, int(np.ceil(service_level_z * np.sqrt(max(0.01, combined_variance)))))

        # 2. Reorder Point (ROP) = (Daily Demand * Lead Time) + Safety Stock
        lead_time_demand = safe_velocity * lead_time_days
        reorder_point = int(np.ceil(lead_time_demand + safety_stock))

        # 3. Stockout Risk Assessment
        if days_of_supply <= lead_time_days:
            risk_tier = InventoryRiskTier.CRITICAL
            stockout_prob = min(99.5, 80.0 + (lead_time_days - days_of_supply) * 3.0)
            urgency = "IMMEDIATE"
            rationale = (
                f"CRITICAL: Stock on hand ({current_stock} units, {days_of_supply}d supply) is less than supplier replenishment lead time ({lead_time_days} days). "
                f"Stockout imminent before shipment can arrive."
            )
        elif days_of_supply <= (lead_time_days * 1.5):
            risk_tier = InventoryRiskTier.WARNING
            stockout_prob = round(40.0 + ((lead_time_days * 1.5 - days_of_supply) / (lead_time_days * 0.5)) * 38.0, 1)
            urgency = "PLAN_THIS_WEEK"
            rationale = (
                f"WARNING: Inventory ({current_stock} units) approaching safety threshold ({reorder_point} units). Reorder within 3-5 days."
            )
        elif days_of_supply > 65.0:
            risk_tier = InventoryRiskTier.OVERSTOCKED
            stockout_prob = 1.0
            urgency = "NO_ACTION"
            excess_units = max(0, current_stock - int(safe_velocity * 45))
            rationale = f"OVERSTOCKED: {days_of_supply} days of supply on hand. Approx ${round(excess_units * unit_cost, 2)} tied up in excess working capital."
        else:
            risk_tier = InventoryRiskTier.OPTIMAL
            stockout_prob = round(max(3.0, 20.0 - (days_of_supply - lead_time_days)), 1)
            urgency = "NORMAL"
            rationale = f"OPTIMAL: Balanced inventory buffer ({days_of_supply} days of supply). Stock levels above reorder point ({reorder_point} units)."

        # 4. Target Inventory & Recommended Order Sizing
        # Target stock covers Lead Time + 30-day review cycle + Safety Stock
        target_inventory = int(np.ceil((safe_velocity * (lead_time_days + 30)) + safety_stock))
        effective_stock = current_stock + on_order_stock

        if effective_stock <= reorder_point:
            recommended_order_qty = max(5, target_inventory - effective_stock)
        else:
            recommended_order_qty = 0

        estimated_po_cost = round(recommended_order_qty * unit_cost, 2)
        revenue_at_risk = 0.0
        if days_of_supply < 30.0:
            unmet_days = 30.0 - days_of_supply
            revenue_at_risk = round(unmet_days * safe_velocity * unit_price, 2)

        return {
            "sku": sku,
            "product_name": product_name,
            "current_stock": current_stock,
            "on_order_stock": on_order_stock,
            "daily_velocity": round(safe_velocity, 2),
            "days_of_supply_remaining": days_of_supply,
            "safety_stock_units": safety_stock,
            "reorder_point_units": reorder_point,
            "target_inventory_units": target_inventory,
            "risk_tier": risk_tier,
            "stockout_probability_pct": stockout_prob,
            "recommended_reorder_qty": recommended_order_qty,
            "estimated_reorder_cost": estimated_po_cost,
            "revenue_at_risk": revenue_at_risk,
            "urgency": urgency,
            "rationale": rationale
        }
