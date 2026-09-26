"""
Sales Intelligence and Revenue Analytics Engine for UPIAI.
Computes categorical revenue contribution, gross profit margins,
velocity distribution, and customer segment purchasing behaviors.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class SalesIntelligenceAnalyzer:
    """Analyzes sales velocity, category margins, and customer cohort dynamics."""

    @classmethod
    def analyze_sales(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Produces comprehensive sales, revenue, margin, and segment breakdown."""
        if df.empty:
            return {"error": "Empty dataset provided"}

        data = df.copy()

        # Identify target columns
        units_col = "units_sold" if "units_sold" in data.columns else "Quantity"
        price_col = "unit_price" if "unit_price" in data.columns else "UnitPrice"
        cost_col = "unit_cost" if "unit_cost" in data.columns else None
        cat_col = "product_category" if "product_category" in data.columns else ("ProductCategory" if "ProductCategory" in data.columns else None)
        cust_col = "customer_type" if "customer_type" in data.columns else ("CustomerType" if "CustomerType" in data.columns else None)

        if units_col not in data.columns or price_col not in data.columns:
            return {"error": "Required units or price columns missing for sales intelligence."}

        data['units'] = pd.to_numeric(data[units_col], errors='coerce').fillna(0)
        data['price'] = pd.to_numeric(data[price_col], errors='coerce').fillna(0)
        data['revenue'] = data['units'] * data['price']

        if cost_col and cost_col in data.columns:
            data['cost'] = pd.to_numeric(data[cost_col], errors='coerce').fillna(data['price'] * 0.65)
        else:
            # Proxy margin 65% COGS
            data['cost'] = data['price'] * 0.65

        data['gross_profit'] = (data['price'] - data['cost']) * data['units']

        total_units = int(data['units'].sum())
        total_revenue = float(data['revenue'].sum())
        total_profit = float(data['gross_profit'].sum())
        overall_margin_pct = round((total_profit / max(1.0, total_revenue)) * 100.0, 2)

        # 1. Category Breakdown
        category_breakdown = []
        if cat_col and cat_col in data.columns:
            cat_agg = data.groupby(cat_col).agg(
                units=('units', 'sum'),
                revenue=('revenue', 'sum'),
                profit=('gross_profit', 'sum')
            ).reset_index()

            for _, row in cat_agg.iterrows():
                cat_rev = float(row['revenue'])
                cat_prof = float(row['profit'])
                category_breakdown.append({
                    "category": str(row[cat_col]),
                    "units_sold": int(row['units']),
                    "total_revenue": round(cat_rev, 2),
                    "gross_profit": round(cat_prof, 2),
                    "margin_percentage": round((cat_prof / max(1.0, cat_rev)) * 100.0, 2),
                    "revenue_share_pct": round((cat_rev / max(1.0, total_revenue)) * 100.0, 2)
                })
            category_breakdown.sort(key=lambda x: x["total_revenue"], reverse=True)

        # 2. Customer Segmentation Breakdown
        customer_segments = []
        if cust_col and cust_col in data.columns:
            cust_agg = data.groupby(cust_col).agg(
                orders=('units', 'count'),
                units=('units', 'sum'),
                revenue=('revenue', 'sum')
            ).reset_index()

            for _, row in cust_agg.iterrows():
                seg_rev = float(row['revenue'])
                order_cnt = int(row['orders'])
                customer_segments.append({
                    "segment": str(row[cust_col]),
                    "total_orders": order_cnt,
                    "total_units": int(row['units']),
                    "total_revenue": round(seg_rev, 2),
                    "average_order_value": round(seg_rev / max(1, order_cnt), 2),
                    "revenue_share_pct": round((seg_rev / max(1.0, total_revenue)) * 100.0, 2)
                })
            customer_segments.sort(key=lambda x: x["total_revenue"], reverse=True)

        return {
            "total_units_sold": total_units,
            "total_revenue": round(total_revenue, 2),
            "total_gross_profit": round(total_profit, 2),
            "overall_profit_margin_pct": overall_margin_pct,
            "category_performance": category_breakdown,
            "customer_segments": customer_segments
        }
