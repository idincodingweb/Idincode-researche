# src/qualifier.py
"""
Qualifier / Scoring Engine

Inverted scoring logic:
  - Sedikit pixel  = score TINGGI  (peluang jual jasa tracking)
  - PageSpeed buruk = score TINGGI  (peluang jual jasa speed optimization)
  - Response lambat = score TINGGI  (sign tech debt)

Buyer kita = marketing agency. Mereka cari klinik yang PUNYA MASALAH,
bukan yang udah perfect.
"""
from __future__ import annotations

from src.models import EnrichmentResult, QualifiedLead


# ============================================================
# Per-niche config
# ============================================================

NICHE_CONFIG: dict[str, dict] = {
    "medical_high_ticket": {
        "min_response_ms": 6000,
        "weights": {
            "reachable": 0.15,
            "platform": 0.20,
            "pixels": 0.35,
            "pagespeed": 0.30,
        },
    },
    "luxury_fitness": {
        "min_response_ms": 5000,
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
    "weights": {
        "reachable": 0.20,
        "platform": 0.25,
        "pixels": 0.30,
        "pagespeed": 0.25,
    },
}


def _get_config(niche: str) -> dict:
    return NICHE_CONFIG.get(niche, _DEFAULT_CONFIG)


# ============================================================
# Sub-scorers (semua return float 0.0 - 1.0)
# ============================================================

def _score_reachable(r: EnrichmentResult) -> float:
    """Site harus reachable. Kalau ga reachable, gak bisa jual jasa."""
    if not r.reachable:
        return 0.0
    if r.status_code and 200 <= r.status_code < 400:
        return 1.0
    return 0.3  # reachable tapi non-2xx


def _score_platform(r: EnrichmentResult) -> float:
    """
    Platform yang 'fixable' = score tinggi.
    WordPress/WooCommerce/Shopify gampang di-improve = peluang besar.
    Custom/unknown = lebih sulit di-onboard.
    """
    if not r.platform:
        return 0.4  # unknown platform = medium
    platform = r.platform.lower()
    if platform in ("wordpress", "woocommerce"):
        return 1.0  # gold — most fixable
    if platform in ("shopify",):
        return 0.85
    if platform in ("wix", "squarespace", "webflow"):
        return 0.5  # SaaS = limited customization
    if platform in ("magento",):
        return 0.7
    return 0.4


def _score_pixels(r: EnrichmentResult) -> float:
    """
    INVERTED LOGIC: SEDIKIT pixel = GOLD.
    0 pixel       = 1.00 (jackpot — semua jasa tracking bisa dijual)
    1 pixel       = 0.75
    2 pixel       = 0.50
    3 pixel       = 0.25
    4+ pixel      = 0.10 (sudah established, less opportunity)
    """
    pixel_count = sum([
        r.has_meta_pixel,
        r.has_tiktok_pixel,
        r.has_ga4,
        r.has_gtm,
        r.has_google_ads,
    ])

    if pixel_count == 0:
        return 1.00
    if pixel_count == 1:
        return 0.75
    if pixel_count == 2:
        return 0.50
    if pixel_count == 3:
        return 0.25
    return 0.10


def _score_pagespeed(r: EnrichmentResult) -> float:
    """
    INVERTED LOGIC: PageSpeed JELEK = GOLD (peluang jual jasa speed opt).
    Kalau PageSpeed API ga jalan (no key), return neutral 0.5.

    Score mapping (mobile performance):
      0-29   = 1.00 (sangat lambat — urgent)
      30-49  = 0.85
      50-69  = 0.60
      70-84  = 0.30
      85-100 = 0.10 (udah cepet — less opportunity)
    """
    if not r.pagespeed_available or r.pagespeed_score is None:
        return 0.5  # neutral, gak bisa dinilai

    s = r.pagespeed_score
    if s < 30:
        return 1.00
    if s < 50:
        return 0.85
    if s < 70:
        return 0.60
    if s < 85:
        return 0.30
    return 0.10


# ============================================================
# Main scoring
# ============================================================

def score_lead(r: EnrichmentResult) -> QualifiedLead:
    """Hitung composite score 0.0-1.0 dari weighted sub-scores."""
    config = _get_config(r.niche)
    weights = config["weights"]

    sub_scores = {
        "reachable": _score_reachable(r),
        "platform": _score_platform(r),
        "pixels": _score_pixels(r),
        "pagespeed": _score_pagespeed(r),
    }

    composite = sum(
        sub_scores[key] * weights.get(key, 0.0)
        for key in sub_scores
    )

    # Penalty untuk response time lambat
    if r.response_ms and r.response_ms > config["min_response_ms"]:
        composite *= 0.85  # 15% penalty kalo terlalu lambat (mungkin server issue)

    composite = round(min(max(composite, 0.0), 1.0), 4)

    return QualifiedLead(
        domain=r.domain,
        niche=r.niche,
        category_name=r.category_name,
        location=r.location,
        score=composite,
        response_ms=r.response_ms,
        platform=r.platform,
        meta_pixel_in_html=r.has_meta_pixel,
        ga4_in_html=r.has_ga4,
        gtm_in_html=r.has_gtm,
        google_ads_in_html=r.has_google_ads,
        pagespeed_score=r.pagespeed_score,
        lcp_ms=r.lcp_ms,
        gold_reasons="",       # Diisi nanti oleh analyst.py
        outreach_angle="",     # Diisi nanti oleh analyst.py
    )


def qualify_leads(
    enrichments: list[EnrichmentResult],
    *,
    min_score: float = 0.0,
) -> list[QualifiedLead]:
    """
    Convert enrichments -> qualified leads, filter by min_score, sort desc.
    """
    leads = [score_lead(r) for r in enrichments]
    leads = [l for l in leads if l.score >= min_score]
    leads.sort(key=lambda x: x.score, reverse=True)
    return leads
