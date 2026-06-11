# src/models.py
"""Dataclasses untuk pipeline. Type-safe, self-documenting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EnrichmentResult:
    """Raw enrichment data per domain (sebelum scoring)."""
    domain: str
    location: Optional[str]
    niche: str
    category: Optional[str]

    # Reachability
    reachable: bool
    fail_reason: Optional[str]  # "connect_timeout", "HTTP 404", dll
    response_ms: Optional[int]
    status_code: Optional[int]

    # Platform
    platform: Optional[str]

    # Pixels (from HTML)
    has_meta_pixel: bool
    has_tiktok_pixel: bool
    has_ga4: bool
    has_gtm: bool
    has_google_ads: bool

    # Performance (from PageSpeed API)
    pagespeed_score: Optional[int]  # 0-100
    lcp_ms: Optional[int]


@dataclass
class QualifiedLead:
    """Scored lead, siap di-enrich AI & export."""
    domain: str
    location: Optional[str]
    niche: str
    category: Optional[str]
    score: float  # 0.0 - 1.0

    platform: Optional[str]
    meta_pixel_in_html: bool
    tiktok_pixel_in_html: bool
    ga4_in_html: bool
    gtm_in_html: bool
    google_ads_in_html: bool

    pagespeed_score: Optional[int]
    lcp_ms: Optional[int]
    response_ms: Optional[int]

    # AI-generated (filled by analyst.py)
    gold_reasons: str = ""
    outreach_angle: str = ""
