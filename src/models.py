# src/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Target:
    """Satu domain target hasil parse dari targets.yaml."""
    domain: str                                  # sudah dinormalisasi (lowercase, tanpa scheme/slash)
    niche: str                                   # diwarisi dari kategori induk
    category_name: str                           # buat traceability
    extra: dict[str, Any] = field(default_factory=dict)  # location, tier, details, dst

    @property
    def url(self) -> str:
        """URL kanonik buat di-fetch enricher (Fase 1)."""
        return f"https://{self.domain}"


@dataclass(slots=True)
class Category:
    """Satu kategori = satu SKU produk."""
    name: str
    niche: str
    targets: list[Target]
    directories: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TargetsConfig:
    """Hasil akhir parse seluruh targets.yaml."""
    generated_by: str
    version: str
    categories: list[Category]

    @property
    def total_targets(self) -> int:
        return sum(len(c.targets) for c in self.categories)

# === Tambahkan di src/models.py, di bawah TargetsConfig ===

@dataclass(slots=True)
class FetchResult:
    """Hasil mentah satu fetch HTTP. Network layer ngisi ini."""
    ok: bool
    status_code: int | None = None
    html: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    response_ms: int | None = None       # waktu respon (proxy kasar buat 'speed')
    error: str | None = None             # diisi kalau ok=False


@dataclass(slots=True)
class PageSpeedResult:
    """Hasil PageSpeed. available=False kalau di-skip (no API key) atau gagal."""
    available: bool
    performance_score: int | None = None  # 0-100
    error: str | None = None


@dataclass(slots=True)
class EnrichmentResult:
    """Gabungan semua sinyal untuk satu target. Output Fase 1, input Fase 2."""
    domain: str
    niche: str
    category_name: str
    reachable: bool
    status_code: int | None
    response_ms: int | None
    # pixel signals
    has_meta_pixel: bool
    has_tiktok_pixel: bool
    has_ga4: bool
    has_gtm: bool
    # techstack
    platform: str | None
    # pagespeed (opsional)
    pagespeed_available: bool
    pagespeed_score: int | None
    # diagnostics
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

# === Tambahkan di src/models.py ===

@dataclass(slots=True)
class QualifierConfig:
    """
    Per-niche rules: minimum sinyal + scoring weights.
    
    Contoh luxury_fitness: butuh pagespeed (premium customer = impatient)
    vs budget_dropship: pagespeed optional (traffic source berasal dari ads, nggak tergantung organic).
    """
    niche: str
    min_response_ms: int = 5000       # timeout threshold (ms)
    min_pagespeed_score: int | None = None  # None = nggak wajib
    required_platforms: set[str] = field(default_factory=set)  # e.g., {'Shopify', 'WooCommerce'}
    
    # Scoring weights (bobot masing-masing sinyal, 0-1)
    weight_reachable: float = 0.2
    weight_platform: float = 0.25
    weight_pixels: float = 0.3
    weight_pagespeed: float = 0.25
    
    @property
    def total_weight(self) -> float:
        return (
            self.weight_reachable
            + self.weight_platform
            + self.weight_pixels
            + self.weight_pagespeed
        )


@dataclass(slots=True)
class QualifiedLead:
    """Output Fase 2: lead yang lolos threshold + udah di-score."""
    domain: str
    niche: str
    category_name: str
    score: float  # 0.0-1.0, buat ranking
    score_breakdown: dict[str, float]  # transparency: {'reachable': 0.2, 'platform': 0.15, ...}
    response_ms: int | None
    platform: str | None
    has_any_pixel: bool
    pagespeed_score: int | None
    extra: dict[str, Any] = field(default_factory=dict)
