# src/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Target:
    domain: str
    niche: str
    category_name: str = ""
    location: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        if self.domain.startswith(("http://", "https://")):
            return self.domain
        return f"https://{self.domain}"


@dataclass(slots=True)
class FetchResult:
    ok: bool
    status_code: int | None = None
    html: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    response_ms: int | None = None
    error: str | None = None


@dataclass(slots=True)
class PixelSignals:
    has_meta: bool = False
    has_tiktok: bool = False
    has_ga4: bool = False
    has_gtm: bool = False
    has_google_ads: bool = False


@dataclass(slots=True)
class PageSpeedResult:
    available: bool
    performance_score: int | None = None
    lcp_ms: int | None = None
    error: str | None = None


@dataclass(slots=True)
class EnrichmentResult:
    domain: str
    niche: str
    category_name: str
    location: str
    reachable: bool
    status_code: int | None
    response_ms: int | None
    has_meta_pixel: bool
    has_tiktok_pixel: bool
    has_ga4: bool
    has_gtm: bool
    has_google_ads: bool
    platform: str | None
    pagespeed_available: bool
    pagespeed_score: int | None
    lcp_ms: int | None
    error: str | None = None


@dataclass(slots=True)
class QualifiedLead:
    domain: str
    niche: str
    category_name: str
    location: str
    score: float
    response_ms: int | None
    platform: str | None
    meta_pixel_in_html: bool
    ga4_in_html: bool
    gtm_in_html: bool
    google_ads_in_html: bool
    pagespeed_score: int | None
    lcp_ms: int | None
    gold_reasons: str = ""
    outreach_angle: str = ""


class TargetsValidationError(Exception):
    """Raised kalau targets.yaml invalid."""
    pass
