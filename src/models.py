# src/models.py
"""Dataclasses untuk pipeline. Type-safe, self-documenting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# Input: dari targets.yaml (dipakai loader.py)
# ============================================================
@dataclass
class Target:
    """Single target dari targets.yaml — input mentah sebelum di-enrich."""
    domain: str
    location: Optional[str] = None
    niche: str = "default"
    category: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert ke dict — kompatibel dengan enrich_domain() yang expect dict."""
        return {
            "domain": self.domain,
            "location": self.location,
            "niche": self.niche,
            "category": self.category,
        }


# ============================================================
# Intermediate: hasil enrichment (dipakai enrichers.py)
# ============================================================
@dataclass
class EnrichmentResult:
    """Raw enrichment data per domain (sebelum scoring)."""
    domain: str
    location: Optional[str]
    niche: str
    category: Optional[str]

    # Reachability
    reachable: bool
    fail_reason: Optional[str] = None
    response_ms: Optional[int] = None
    status_code: Optional[int] = None

    # Platform
    platform: Optional[str] = None

    # Pixels (from HTML)
    has_meta_pixel: bool = False
    has_tiktok_pixel: bool = False
    has_ga4: bool = False
    has_gtm: bool = False
    has_google_ads: bool = False

    # Performance (from PageSpeed API)
    pagespeed_score: Optional[int] = None
    lcp_ms: Optional[int] = None


# ============================================================
# Final: scored lead siap export (dipakai qualifier.py, analyst.py, export.py)
# ============================================================
@dataclass
class QualifiedLead:
    """Scored lead, siap di-enrich AI & export."""
    domain: str
    location: Optional[str]
    niche: str
    category: Optional[str]
    score: float

    platform: Optional[str] = None
    meta_pixel_in_html: bool = False
    tiktok_pixel_in_html: bool = False
    ga4_in_html: bool = False
    gtm_in_html: bool = False
    google_ads_in_html: bool = False

    pagespeed_score: Optional[int] = None
    lcp_ms: Optional[int] = None
    response_ms: Optional[int] = None

    # AI-generated (filled by analyst.py)
    gold_reasons: str = ""
    outreach_angle: str = ""

    # Rank (assigned by export.py)
    rank: int = 0
