"""
Personalization Engine for UPIAI.
Customizes demand forecasting, safety stock multipliers, holding cost rates,
and seasonality profiles to specific business sectors and operating models.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class BusinessSectorProfile(BaseModel):
    sector_id: str
    sector_name: str
    target_service_level: float = Field(default=0.95, ge=0.5, le=0.999)
    z_score_multiplier: float = Field(default=1.645)  # 95% service level Z
    annual_holding_cost_rate: float = Field(default=0.20)  # 20% annual cost of carry
    shelf_life_constraint_days: Optional[int] = None
    default_lead_time_days: int = Field(default=14)
    weekend_lift_factor: float = Field(default=1.25)
    promo_elasticity: float = Field(default=-1.3)


# Preconfigured industry vertical templates
SECTOR_TEMPLATES = {
    "GROCERY_SUPERMARKET": BusinessSectorProfile(
        sector_id="GROCERY_SUPERMARKET",
        sector_name="Grocery & Supermarket Retail",
        target_service_level=0.96,
        z_score_multiplier=1.75,
        annual_holding_cost_rate=0.25,
        shelf_life_constraint_days=14,
        default_lead_time_days=3,
        weekend_lift_factor=1.45,
        promo_elasticity=-1.5
    ),
    "CONSUMER_TECH": BusinessSectorProfile(
        sector_id="CONSUMER_TECH",
        sector_name="Consumer Electronics & Hardware",
        target_service_level=0.95,
        z_score_multiplier=1.645,
        annual_holding_cost_rate=0.18,
        shelf_life_constraint_days=None,
        default_lead_time_days=18,
        weekend_lift_factor=1.20,
        promo_elasticity=-0.9
    ),
    "PHARMACEUTICAL": BusinessSectorProfile(
        sector_id="PHARMACEUTICAL",
        sector_name="Healthcare & Pharmacy",
        target_service_level=0.99,
        z_score_multiplier=2.33,
        annual_holding_cost_rate=0.15,
        shelf_life_constraint_days=180,
        default_lead_time_days=7,
        weekend_lift_factor=1.05,
        promo_elasticity=-0.3
    ),
    "FASHION_APPAREL": BusinessSectorProfile(
        sector_id="FASHION_APPAREL",
        sector_name="Fashion & Omnichannel Apparel",
        target_service_level=0.90,
        z_score_multiplier=1.28,
        annual_holding_cost_rate=0.30,
        shelf_life_constraint_days=90,
        default_lead_time_days=30,
        weekend_lift_factor=1.60,
        promo_elasticity=-1.8
    )
}


class PersonalizationEngine:
    """Adapts AI inventory and forecasting equations to a business's operational reality."""

    @classmethod
    def get_profile(cls, sector_key: str = "GROCERY_SUPERMARKET") -> BusinessSectorProfile:
        """Retrieves or defaults a business sector profile."""
        clean_key = sector_key.upper().replace(" ", "_")
        return SECTOR_TEMPLATES.get(clean_key, SECTOR_TEMPLATES["GROCERY_SUPERMARKET"])

    @classmethod
    def compute_personalized_safety_stock(
        cls,
        daily_velocity: float,
        daily_std: float,
        lead_time_days: int,
        lead_time_std_days: float = 1.5,
        sector_key: str = "GROCERY_SUPERMARKET"
    ) -> Dict[str, Any]:
        """
        Calculates safety stock using combined demand uncertainty + lead-time variance:
        SS = Z * sqrt( (LT * std_demand^2) + (avg_demand^2 * std_LT^2) )
        """
        profile = cls.get_profile(sector_key)
        z = profile.z_score_multiplier

        variance_term = (lead_time_days * (daily_std ** 2)) + ((daily_velocity ** 2) * (lead_time_std_days ** 2))
        safety_stock = int(np.ceil(z * np.sqrt(max(0.1, variance_term))))

        return {
            "sector": profile.sector_name,
            "target_service_level": f"{profile.target_service_level * 100}%",
            "z_multiplier": z,
            "safety_stock_units": max(2, safety_stock),
            "reorder_point_units": int(np.ceil((daily_velocity * lead_time_days) + safety_stock))
        }
