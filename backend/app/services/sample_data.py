"""
High-fidelity Sample Datasets and Seed Generators for UPIAI.
Contains product catalogs, supplier registries, and 90-day multi-SKU daily sales histories.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

SAMPLE_PRODUCTS = [
    {
        "sku": "TECH-4090-GPU",
        "name": "Titan RTX 4090 OC 24GB",
        "category": "Hardware / GPU",
        "unit_cost": 1150.0,
        "unit_price": 1699.0,
        "current_stock": 14,
        "reserved_stock": 2,
        "on_order_stock": 0,
        "lead_time_days": 18,
        "supplier_id": "SUP-001",
        "supplier_name": "Silicon Horizons Micro"
    },
    {
        "sku": "TECH-NVME-2TB",
        "name": "HyperDrive Gen5 2TB NVMe SSD",
        "category": "Storage",
        "unit_cost": 110.0,
        "unit_price": 189.0,
        "current_stock": 185,
        "reserved_stock": 12,
        "on_order_stock": 50,
        "lead_time_days": 10,
        "supplier_id": "SUP-002",
        "supplier_name": "Nexus Memory Global"
    },
    {
        "sku": "TECH-CPU-7800X",
        "name": "QuantumCore i9-14900KS Processor",
        "category": "Hardware / CPU",
        "unit_cost": 410.0,
        "unit_price": 599.0,
        "current_stock": 22,
        "reserved_stock": 4,
        "on_order_stock": 30,
        "lead_time_days": 14,
        "supplier_id": "SUP-001",
        "supplier_name": "Silicon Horizons Micro"
    },
    {
        "sku": "TECH-MON-4K144",
        "name": "Spectra 32-inch OLED 4K 144Hz Monitor",
        "category": "Peripherals",
        "unit_cost": 580.0,
        "unit_price": 899.0,
        "current_stock": 8,
        "reserved_stock": 3,
        "on_order_stock": 0,
        "lead_time_days": 21,
        "supplier_id": "SUP-003",
        "supplier_name": "Apex Display Tech"
    },
    {
        "sku": "TECH-MECH-KB80",
        "name": "AeroKey Wireless Mechanical 80% Keyboard",
        "category": "Accessories",
        "unit_cost": 65.0,
        "unit_price": 149.0,
        "current_stock": 320,
        "reserved_stock": 15,
        "on_order_stock": 100,
        "lead_time_days": 7,
        "supplier_id": "SUP-004",
        "supplier_name": "Vortex Peripherals"
    },
    {
        "sku": "TECH-AUDIO-PRO",
        "name": "SonarWave Studio Wireless Headphones",
        "category": "Audio",
        "unit_cost": 135.0,
        "unit_price": 279.0,
        "current_stock": 45,
        "reserved_stock": 5,
        "on_order_stock": 25,
        "lead_time_days": 12,
        "supplier_id": "SUP-004",
        "supplier_name": "Vortex Peripherals"
    }
]

SAMPLE_SUPPLIERS = [
    {
        "supplier_id": "SUP-001",
        "supplier_name": "Silicon Horizons Micro",
        "category": "Semiconductors & Processors",
        "avg_lead_time_days": 18,
        "lead_time_variance_days": 3.2,
        "on_time_delivery_rate": 0.94,
        "quality_rating": 4.9,
        "payment_terms": "Net 30",
        "balance_due": 34500.0,
        "payment_status": "Pending",
        "contact_email": "orders@siliconhorizons.com",
        "country": "Taiwan",
        "reliability_tier": "TIER_1_PREFERRED"
    },
    {
        "supplier_id": "SUP-002",
        "supplier_name": "Nexus Memory Global",
        "category": "Storage & Flash Memory",
        "avg_lead_time_days": 10,
        "lead_time_variance_days": 1.4,
        "on_time_delivery_rate": 0.98,
        "quality_rating": 4.8,
        "payment_terms": "Net 45",
        "balance_due": 12800.0,
        "payment_status": "Paid",
        "contact_email": "fulfillment@nexusmemory.com",
        "country": "South Korea",
        "reliability_tier": "TIER_1_PREFERRED"
    },
    {
        "supplier_id": "SUP-003",
        "supplier_name": "Apex Display Tech",
        "category": "OLED & Display Panels",
        "avg_lead_time_days": 21,
        "lead_time_variance_days": 5.8,
        "on_time_delivery_rate": 0.81,
        "quality_rating": 4.3,
        "payment_terms": "Net 15",
        "balance_due": 46200.0,
        "payment_status": "Overdue",
        "contact_email": "billing@apexdisplay.com",
        "country": "Japan",
        "reliability_tier": "TIER_3_HIGH_RISK"
    },
    {
        "supplier_id": "SUP-004",
        "supplier_name": "Vortex Peripherals",
        "category": "Input & Acoustic Peripherals",
        "avg_lead_time_days": 7,
        "lead_time_variance_days": 1.1,
        "on_time_delivery_rate": 0.96,
        "quality_rating": 4.7,
        "payment_terms": "Net 30",
        "balance_due": 9400.0,
        "payment_status": "Paid",
        "contact_email": "support@vortexgear.com",
        "country": "United States",
        "reliability_tier": "TIER_2_RELIABLE"
    }
]


def generate_synthetic_sales_history(days: int = 90) -> List[Dict[str, Any]]:
    """
    Generates realistic daily sales history for sample SKUs with seasonality and weekend lifts.
    """
    random.seed(42)
    records = []
    base_date = datetime.utcnow().date() - timedelta(days=days)

    sku_demand_profiles = {
        "TECH-4090-GPU": {"mean": 2.4, "weekend_boost": 1.8, "price": 1699.0},
        "TECH-NVME-2TB": {"mean": 11.2, "weekend_boost": 1.3, "price": 189.0},
        "TECH-CPU-7800X": {"mean": 3.8, "weekend_boost": 1.5, "price": 599.0},
        "TECH-MON-4K144": {"mean": 1.6, "weekend_boost": 1.9, "price": 899.0},
        "TECH-MECH-KB80": {"mean": 14.5, "weekend_boost": 1.4, "price": 149.0},
        "TECH-AUDIO-PRO": {"mean": 5.1, "weekend_boost": 1.6, "price": 279.0}
    }

    for day_i in range(days):
        current_dt = base_date + timedelta(days=day_i)
        date_str = current_dt.strftime("%Y-%m-%d")
        dow = current_dt.weekday()
        is_weekend = dow in [5, 6]

        for sku, profile in sku_demand_profiles.items():
            base_qty = profile["mean"]
            if is_weekend:
                base_qty *= profile["weekend_boost"]
            
            # Organic noise + slight upward trend
            trend_factor = 1.0 + (day_i / days) * 0.15
            daily_qty = max(0, int(round(random.gauss(base_qty * trend_factor, base_qty * 0.25))))

            records.append({
                "date": date_str,
                "sku": sku,
                "units_sold": daily_qty,
                "unit_price": profile["price"],
                "channel": "Direct Online" if random.random() > 0.3 else "B2B Partner",
                "discount": 0.05 if is_weekend else 0.0,
                "is_promotion": is_weekend
            })

    return records
