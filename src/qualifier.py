# src/qualifier.py
from __future__ import annotations

from src.models import EnrichmentResult, QualifiedLead


# Per-niche threshold + weights. Tambah niche baru di sini.
NICHE_CONFIG: dict[str, dict] = {
    "medical_high_ticket": {
        "min_response_ms": 6000,
        "min_pagespeed": None,   # PageSpeed optional (kalau API key gak ada)
        "weights": {
            "reachable": 0.15,
            "platform": 0.20,
            "pixels": 0.35,
            "pagespeed": 0.30,
        },
    },
    "luxury_fitness": {
        "min_response_ms": 5000,
        "min_pagespeed": None,
        "weights": {
            "reachable": 0.15,
            "platform": 0.25,
            "pixels": 0.35,
            "pagespeed": 0.25,
        },
    },
}

_DEFAULT_CONFIG = {
    "min_response_ms": 8000,
    "min_pagespeed": None,
    "weights": {
        "reachable": 0.2,
        "platform": 0.25,
        "pixels": 0.3,
        "pagespeed": 0.25,
    },
}


def _get_config(niche: str) -> dict:
    return NICHE_CONFIG.get(niche, _DEFAULT_CONFIG)


def _score_pixels(r: EnrichmentResult) -> float:
    """
    Logic inverted: SEDIKIT pixel = GOLD (peluang jual jasa tracking).
    Banyak pixel = sudah established, less opportunity.
    """
    pixel_count = sum([
        r.has_meta_pixel,
        r.has_tiktok_pixel,
        r.has_ga4,
        r.has_gtm,
