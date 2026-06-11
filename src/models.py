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
