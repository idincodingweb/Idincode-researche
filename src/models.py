# src/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class Target:
    """Input target dari targets.yaml."""
    domain: str
    location: str
    niche: str
    category: str


@dataclass(slots=True)
class FetchResult:
    """Hasil fetch HTML dari domain target."""
    domain: str
    ok: bool
    status_code: int
    response_ms: int
    html: str
    headers: dict[str, str]
    final_url: str
    error: Optional[str] = None


@dataclass(slots=True)
class PixelSignals:
    """Hasil deteksi pixel/tracking di HTML.
    
    CATATAN PENTING: Field name HARUS sama dengan EnrichmentResult
    biar gak ada naming mismatch (bug yang udah pernah kejadian).
    """
    has_meta_pixel: bool = False
    has_tiktok_pixel: bool = False  # ← UDAH FIX (sebelumnya: has_tiktok)
    has_ga4: bool = False
    has_gtm: bool = False
    has_google_ads: bool = False
    has_hotjar: bool = False
    has_clarity: bool = False
    has_linkedin_insight: bool = False


@dataclass(slots=True)
class EnrichmentResult:
    """Hasil lengkap enrichment per domain."""
    domain: str
    location: str
    niche: str
    category: str

    # Reachability
    reachable: bool = False
    response_ms: Optional[int] = None
    status_code: Optional[int] = None

    # Platform detection
    platform: Optional[str] = None

    # Pixel signals (in HTML) — naming sekarang konsisten dengan PixelSignals
    has_meta_pixel: bool = False
    has_tiktok_pixel: bool = False
    has_ga4: bool = False
    has_gtm: bool = False
    has_google_ads: bool = False
    has_hotjar: bool = False
    has_clarity: bool = False
    has_linkedin_insight: bool = False

    # PageSpeed metrics
    pagespeed_score: Optional[int] = None
    lcp_ms: Optional[int] = None
    fid_ms: Optional[int] = None
    cls: Optional[float] = None

    # Errors (untuk debugging)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class QualifiedLead:
    """Lead final dengan score + AI-generated narasi."""
    # Identitas
    domain: str
    location: str
    niche: str
    category: str

    # Score
    score: float
    rank: int = 0

    # Platform
    platform: Optional[str] = None

    # Pixel boolean (untuk export CSV)
    meta_pixel_in_html: bool = False
    tiktok_pixel_in_html: bool = False
    ga4_in_html: bool = False
    gtm_in_html: bool = False
    google_ads_in_html: bool = False

    # Performance
    pagespeed_score: Optional[int] = None
    lcp_ms: Optional[int] = None
    response_ms: Optional[int] = None

    # AI narasi (diisi oleh analyst.py)
    gold_reasons: str = ""
    outreach_angle: str = ""
