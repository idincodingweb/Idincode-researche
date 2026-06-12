# src/export.py
# === Tambah di paling bawah export.py ===

# Alias buat backward-compat (jaga-jaga kalau ada code lain manggil nama baru)
export_tiered = export_tiered_csvs
"""Export qualified leads ke CSV bertingkat (Starter / Pro / Premium Gold).

ARSITEKTUR:
- export_tiered() = entry point dari pipeline (sesuai naming pipeline.py)
- export_tiered_csvs() = alias backward-compatible
- Tiered logic: filter by min_score, limit by tier, re-rank locally
- Output dir auto-create kalau belum ada
"""
from __future__ import annotations

import csv
from copy import copy
from dataclasses import replace
from pathlib import Path
from typing import Optional

from src.config import OUTPUT_DIR, TIER_CONFIGS
from src.models import QualifiedLead


# ============================================================
# CSV column order (jangan diubah tanpa update analyst & buyer docs)
# ============================================================
_CSV_COLUMNS = [
    "rank",
    "domain",
    "location",
    "niche",
    "category",
    "gold_score",
    "platform",
    "meta_pixel_in_html",
    "tiktok_pixel_in_html",
    "ga4_in_html",
    "gtm_in_html",
    "google_ads_in_html",
    "pagespeed_mobile",
    "lcp_ms",
    "response_ms",
    "gold_reasons",
    "outreach_angle",
]


# ============================================================
# Public API
# ============================================================
def export_tiered(
    leads: list[QualifiedLead],
    output_dir: Optional[str] = None,
) -> list[str]:
    """Entry point dipanggil dari pipeline.py.

    Args:
        leads: list QualifiedLead (sudah di-sort by score di pipeline)
        output_dir: override OUTPUT_DIR dari config (untuk testing)

    Returns:
        list path file yang berhasil di-export
    """
    out_dir = Path(output_dir) if output_dir else Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Handle empty input (kalau 0 reachable, masih bikin file kosong biar
    # GitHub Actions artifact upload gak fail)
    if not leads:
        print("[export] ⚠️  No leads to export. Writing empty CSV files for debugging.")
        empty_path = out_dir / "leads_all.csv"
        _write_csv(empty_path, [])
        return [str(empty_path)]

    # Sort + assign global rank (defensive — pipeline harusnya udah sort)
    sorted_leads = sorted(leads, key=lambda x: x.score, reverse=True)
    ranked_all = [_assign_rank(lead, idx) for idx, lead in enumerate(sorted_leads, 1)]

    output_files: list[str] = []

    # 1. Internal master file (semua leads)
    all_path = out_dir / "leads_all.csv"
    _write_csv(all_path, ranked_all)
    print(f"[export] OK leads_all.csv         ({len(ranked_all)} leads) - INTERNAL")
    output_files.append(str(all_path))

    # 2. Tiered exports
    for tier in TIER_CONFIGS:
        filtered = [lead for lead in ranked_all if lead.score >= tier["min_score"]]
        filtered = filtered[: tier["limit"]]
        # Re-rank lokal dalam tier
        ranked = [_assign_rank(lead, idx) for idx, lead in enumerate(filtered, 1)]

        tier_path = out_dir / tier["filename"]
        _write_csv(tier_path, ranked)
        print(
            f"[export] OK {tier['filename']:<24} "
            f"({len(ranked):3d} leads, score >= {tier['min_score']}) - {tier['label']}"
        )
        output_files.append(str(tier_path))

    return output_files


# Backward-compatible alias (kalau ada code lain yang masih panggil nama lama)
def export_tiered_csvs(leads: list[QualifiedLead]) -> list[str]:
    return export_tiered(leads)


# ============================================================
# Helpers
# ============================================================
def _assign_rank(lead: QualifiedLead, rank: int) -> QualifiedLead:
    """Bikin copy dengan rank assigned. Defensive terhadap dataclass slots/frozen."""
    try:
        # Path 1: dataclass dengan replace() (paling clean)
        new_lead = replace(lead, rank=rank)
        return new_lead
    except (TypeError, ValueError):
        # Path 2: copy + setattr (kalau rank bukan field formal di dataclass)
        new_lead = copy(lead)
        try:
            setattr(new_lead, "rank", rank)
        except AttributeError:
            # Path 3: object pakai __slots__ tanpa rank → silently skip
            pass
        return new_lead


def _get_rank(lead: QualifiedLead, fallback: int = 0) -> int:
    """Get rank dengan fallback kalau attribute belum di-set."""
    return getattr(lead, "rank", fallback)


def _write_csv(path: Path, leads: list[QualifiedLead]) -> None:
    """Write CSV dengan column order fixed."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(_CSV_COLUMNS)
        for lead in leads:
            writer.writerow([
                _get_rank(lead),
                lead.domain,
                lead.location or "",
                lead.niche,
                lead.category or "",
                f"{lead.score:.4f}",
                lead.platform or "Unknown",
                _yn(lead.meta_pixel_in_html),
                _yn(getattr(lead, "tiktok_pixel_in_html", False)),
                _yn(lead.ga4_in_html),
                _yn(lead.gtm_in_html),
                _yn(lead.google_ads_in_html),
                lead.pagespeed_score if lead.pagespeed_score is not None else "",
                lead.lcp_ms if lead.lcp_ms is not None else "",
                lead.response_ms if lead.response_ms is not None else "",
                lead.gold_reasons or "",
                lead.outreach_angle or "",
            ])


def _yn(b: bool) -> str:
    return "yes" if b else "no"
