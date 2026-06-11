# tests/test_qualifier.py 
# By Idin Code
import pytest
from src.models import EnrichmentResult, QualifiedLead
from src.qualifiers.config import get_config, LUXURY_FITNESS, BUDGET_DROPSHIP
from src.qualifiers.engine import (
    _score_reachable,
    _score_platform,
    _score_pixels,
    _score_pagespeed,
    qualify,
)


def _make_enrichment(
    domain: str = "example.com",
    niche: str = "luxury_fitness",
    reachable: bool = True,
    response_ms: int = 1500,
    platform: str | None = "Shopify",
    has_meta: bool = False,
    has_tiktok: bool = False,
    has_ga4: bool = True,
    has_gtm: bool = True,
    pagespeed_available: bool = True,
    pagespeed_score: int | None = 75,
) -> EnrichmentResult:
    """Factory buat test."""
    return EnrichmentResult(
        domain=domain,
        niche=niche,
        category_name="Test",
        reachable=reachable,
        status_code=200 if reachable else None,
        response_ms=response_ms,
        has_meta_pixel=has_meta,
        has_tiktok_pixel=has_tiktok,
        has_ga4=has_ga4,
        has_gtm=has_gtm,
        platform=platform,
        pagespeed_available=pagespeed_available,
        pagespeed_score=pagespeed_score,
        error=None if reachable else "timeout",
    )


def test_score_reachable():
    assert _score_reachable(_make_enrichment(reachable=True)) == 1.0
    assert _score_reachable(_make_enrichment(reachable=False)) == 0.0


def test_score_platform():
    # Exact match
    assert _score_platform(_make_enrichment(platform="Shopify"), {"Shopify"}) == 1.0
    
    # No match but reachable (unknown) → 0.5
    assert _score_platform(_make_enrichment(platform=None, reachable=True), {"Shopify"}) == 0.5
    
    # No match and not reachable → 0.0
    assert _score_platform(_make_enrichment(platform="WooCommerce", reachable=True), {"Shopify"}) == 0.0
    
    # No requirement → 0.5 if reachable
    assert _score_platform(_make_enrichment(platform="Anything", reachable=True), set()) == 0.5


def test_score_pixels():
    # 4 pixels → 1.0
    result = _make_enrichment(has_meta=True, has_tiktok=True, has_ga4=True, has_gtm=True)
    assert _score_pixels(result) == 1.0
    
    # 2 pixels → 0.6
    result = _make_enrichment(has_meta=True, has_tiktok=False, has_ga4=True, has_gtm=False)
    assert _score_pixels(result) == 0.6
    
    # 0 pixels → 0.0
    result = _make_enrichment(has_meta=False, has_tiktok=False, has_ga4=False, has_gtm=False)
    assert _score_pixels(result) == 0.0


def test_score_pagespeed():
    # Available, score 75 → 0.75
    assert _score_pagespeed(_make_enrichment(pagespeed_available=True, pagespeed_score=75)) == 0.75
    
    # Unavailable → 0.5 (neutral)
    assert _score_pagespeed(_make_enrichment(pagespeed_available=False, pagespeed_score=None)) == 0.5
    
    # Score 100 → 1.0 (clamped)
    assert _score_pagespeed(_make_enrichment(pagespeed_available=True, pagespeed_score=100)) == 1.0


def test_qualify_luxury_fitness_threshold():
    """Luxury fitness: strict pagespeed + required platform."""
    # ✅ High-quality lead
    good = _make_enrichment(
        domain="luxury-gym.com",
        niche="luxury_fitness",
        reachable=True,
        response_ms=1500,
        platform="Shopify",
        has_meta=True,
        has_ga4=True,
        has_gtm=True,
        pagespeed_score=75,
    )
    
    # ❌ Slow response (>5000ms)
    slow = _make_enrichment(
        domain="slow-gym.com",
        niche="luxury_fitness",
        response_ms=6000,
    )
    
    # ❌ Low pagespeed (<60)
    bad_speed = _make_enrichment(
        domain="bad-speed.com",
        niche="luxury_fitness",
        response_ms=1500,
        pagespeed_score=45,
    )
    
    results = [good, slow, bad_speed]
    qualified = qualify(results)
    
    assert len(qualified) == 1
    assert qualified[0].domain == "luxury-gym.com"
    assert qualified[0].score > 0.5  # High quality


def test_qualify_budget_dropship_lenient():
    """Budget dropship: pagespeed optional, any platform OK."""
    lead = _make_enrichment(
        domain="dropship-store.com",
        niche="budget_dropship",
        reachable=True,
        response_ms=6000,  # Slow, but OK (min_response_ms=8000)
        platform=None,     # Unknown platform, still OK
        has_meta=True,
        has_tiktok=True,
        has_ga4=False,
        has_gtm=False,
        pagespeed_available=False,  # Nggak perlu PageSpeed
        pagespeed_score=None,
    )
    
    results = [lead]
    qualified = qualify(results)
    
    assert len(qualified) == 1
    assert qualified[0].niche == "budget_dropship"
    # Pagespeed nggak boleh ngedrag score (unavailable = 0.5, bukan 0.0)
    assert qualified[0].score > 0.3


def test_qualify_ranking():
    """Leads harus di-sort descending score."""
    high = _make_enrichment(
        domain="high-score.com",
        niche="luxury_fitness",
        has_meta=True,
        has_tiktok=True,
        has_ga4=True,
        has_gtm=True,
        pagespeed_score=90,
    )
    medium = _make_enrichment(
        domain="medium-score.com",
        niche="luxury_fitness",
        has_meta=True,
        has_ga4=True,
        has_tiktok=False,
        has_gtm=False,
        pagespeed_score=60,
    )
    
    results = [medium, high]  # Unordered input
    qualified = qualify(results)
    
    assert len(qualified) == 2
    assert qualified[0].domain == "high-score.com"
    assert qualified[1].domain == "medium-score.com"
    assert qualified[0].score > qualified[1].score
