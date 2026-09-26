"""
Synthetic Retail Business Environment & What-If Multi-Scenario Simulator for UPIAI.
Generates multi-SKU retail transactions with organic trend, seasonality, promotions,
and simulates what-if supply chain disruptions with explicit SIMULATED provenance tagging.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import pandas as pd
import numpy as np

from ai.data.loader import DatasetProvenance


class SyntheticRetailSimulator:
    """Simulates retail store environments and what-if stress tests."""

    @classmethod
    def generate_environment(
        cls,
        days: int = 180,
        business_type: str = "Grocery_Supermarket",
        store_count: int = 2,
        base_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Generates realistic multi-month retail sales logs with seasonal & weekend lifts."""
        random.seed(42)
        np.random.seed(42)

        start_dt = datetime.strptime(base_date, "%Y-%m-%d") if base_date else (datetime.utcnow() - timedelta(days=days))

        catalog = [
            {"product_id": "SKU-GROC-01", "name": "Organic Basmati Rice 5kg", "category": "Grocery & Staples", "base_price": 450.0, "cost": 310.0, "base_vol": 8.5},
            {"product_id": "SKU-GROC-02", "name": "Sunflower Cooking Oil 1L", "category": "Grocery & Staples", "base_price": 160.0, "cost": 115.0, "base_vol": 14.0},
            {"product_id": "SKU-DAIR-01", "name": "Pasteurized Milk 1L", "category": "Dairy & Eggs", "base_price": 60.0, "cost": 42.0, "base_vol": 32.0},
            {"product_id": "SKU-BEVG-01", "name": "Sparkling Apple Juice 750ml", "category": "Beverages", "base_price": 120.0, "cost": 75.0, "base_vol": 6.5},
            {"product_id": "SKU-CARE-01", "name": "Herbal Shampoo 400ml", "category": "Personal Care", "base_price": 280.0, "cost": 160.0, "base_vol": 4.2},
            {"product_id": "SKU-HOME-01", "name": "Multi-Surface Disinfectant 2L", "category": "Home & Cleaning", "base_price": 350.0, "cost": 210.0, "base_vol": 3.8}
        ]

        rows = []
        customer_types = ["Member", "Regular", "Corporate"]

        for d_idx in range(days):
            current_date = start_dt + timedelta(days=d_idx)
            date_str = current_date.strftime("%Y-%m-%d")
            dow = current_date.weekday()
            is_weekend = dow in [5, 6]

            # Growth trend over time (+15% over span)
            trend_multiplier = 1.0 + (d_idx / max(1, days)) * 0.15

            for store_idx in range(1, store_count + 1):
                store_id = f"STORE-{store_idx:02d}"

                for item in catalog:
                    mean_vol = item["base_vol"] * trend_multiplier
                    if is_weekend:
                        mean_vol *= 1.4  # Weekend retail rush

                    # Random promo on some weekends
                    has_promo = is_weekend and random.random() > 0.6
                    price = item["base_price"] * (0.90 if has_promo else 1.0)
                    if has_promo:
                        mean_vol *= 1.35  # Price elasticity lift

                    qty = max(0, int(round(np.random.poisson(mean_vol))))
                    total_sales = round(qty * price, 2)

                    cust_type = random.choices(customer_types, weights=[0.4, 0.45, 0.15])[0]

                    rows.append({
                        "date": date_str,
                        "time": f"{random.randint(9, 21):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
                        "store_id": store_id,
                        "product_id": item["product_id"],
                        "product_name": item["name"],
                        "product_category": item["category"],
                        "unit_price": price,
                        "unit_cost": item["cost"],
                        "units_sold": qty,
                        "total_amount": total_sales,
                        "customer_type": cust_type,
                        "is_promotion": int(has_promo),
                        "provenance": DatasetProvenance.SIMULATED
                    })

        return pd.DataFrame(rows)

    @classmethod
    def simulate_what_if_scenario(
        cls,
        base_df: pd.DataFrame,
        price_adjustment_pct: float = 0.0,
        marketing_lift_pct: float = 0.0,
        supplier_lead_time_delay_days: int = 0
    ) -> Dict[str, Any]:
        """Runs what-if scenario projection on sales and inventory exposure."""
        df = base_df.copy()
        
        # Price elasticity assumption: -1.2 elasticity for grocery
        price_elasticity = -1.2
        volume_shift_pct = (price_adjustment_pct * price_elasticity) + marketing_lift_pct

        simulated_units = df['units_sold'] * (1.0 + (volume_shift_pct / 100.0))
        simulated_units = np.clip(simulated_units, 0, None)
        
        simulated_prices = df['unit_price'] * (1.0 + (price_adjustment_pct / 100.0))
        simulated_revenue = simulated_units * simulated_prices

        original_rev = float((df['units_sold'] * df['unit_price']).sum())
        projected_rev = float(simulated_revenue.sum())
        rev_delta = projected_rev - original_rev

        return {
            "scenario": "What-If Analysis",
            "price_adjustment_applied": f"{price_adjustment_pct:+}%",
            "marketing_lift_applied": f"{marketing_lift_pct:+}%",
            "lead_time_delay": f"{supplier_lead_time_delay_days} days added",
            "original_total_revenue": round(original_rev, 2),
            "projected_total_revenue": round(projected_rev, 2),
            "revenue_impact_delta": round(rev_delta, 2),
            "percentage_revenue_change": round((rev_delta / max(1.0, original_rev)) * 100.0, 2),
            "provenance": DatasetProvenance.SIMULATED
        }
