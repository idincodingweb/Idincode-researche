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
