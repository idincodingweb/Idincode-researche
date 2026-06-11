# src/qualifiers/config.py
from __future__ import annotations
from src.models import QualifierConfig

# Template: luxury fitness (high-ticket coaching, premium audience)
LUXURY_FITNESS = QualifierConfig(
    niche="luxury_fitness",
    min_response_ms=5000,
    min_pagespeed_score=60,  # Premium users impatient, strict PageSpeed
    required_platforms={"Shopify", "WooCommerce", "Custom"},
    weight_reachable=0.15,
    weight_platform=0.25,
    weight_pixels=0.35,    # Pixels penting = sophisticated tracking
    weight_pagespeed=0.25,
)

# Template: budget dropship (performance marketing, less platform-specific)
BUDGET_DROPSHIP = QualifierConfig(
    niche="budget_dropship",
    min_response_ms=8000,   # Dropshipper lebih toleran ke slow sites
    min_pagespeed_score=None,  # Optional (ada sumber traffic dari ads, bukan organic)
    required_platforms=set(),  # Any platform OK
    weight_reachable=0.2,
    weight_platform=0.15,  # Platform less important
    weight_pixels=0.5,     # Pixels crucial = retargeting, ROAS tracking
    weight_pagespeed=0.15,
)

# Template: medical high-ticket (trust signals paramount)
MEDICAL_HIGH_TICKET = QualifierConfig(
    niche="medical_high_ticket",
    min_response_ms=5000,
    min_pagespeed_score=55,  # Decent UX matters (conversion = consultation booking)
    required_platforms={"WordPress", "Custom"},  # Compliance = custom build sering
    weight_reachable=0.2,
    weight_platform=0.3,   # Platform choice signals maturity
    weight_pixels=0.25,
    weight_pagespeed=0.25,
)

# Registry: map niche name ke config
QUALIFIER_REGISTRY: dict[str, QualifierConfig] = {
    "luxury_fitness": LUXURY_FITNESS,
    "budget_dropship": BUDGET_DROPSHIP,
    "medical_high_ticket": MEDICAL_HIGH_TICKET,
}


def get_config(niche: str) -> QualifierConfig:
    """
    Ambil config buat niche. Kalau niche nggak ada → return default (permissive).
    """
    return QUALIFIER_REGISTRY.get(niche) or QualifierConfig(niche=niche)
