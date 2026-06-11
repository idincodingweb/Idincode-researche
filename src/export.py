# src/export.py
"""
Tiered CSV Export.

Dari 1 dataset hasil pipeline, slice jadi 3 tier produk:

  Tier         | Threshold       | Limit | Filename
  -------------|-----------------|-------|----------------------------------
  Starter      | score >= 0.50   | 25    | leads_starter.csv      ($19)
  Pro          | score >= 0.70   | 100   | leads_pro.csv          ($79)
  Premium      | score >= 0.85   | 50    | leads_premium_gold.csv ($199)

Plus 1 file master:
  leads_all.csv - semua leads (internal use, jangan dijual)
"""
from __future__ import annotations
import csv
from pathlib import Path

from src.models import QualifiedLead


TIER_CONFIGS = [
    {
        "filename": "leads_starter.csv",
        "min_score": 0.50,
        "limit": 25,
        "label": "Starter ($19)",
    },
    {
        "filename": "leads_pro.csv",
        "min_score": 0.70,
        "limit": 100,
        "label": "Pro ($79)",
    },
    {
        "filename": "leads_premium_gold.csv",
        "min_score": 0.85,
        "limit": 50,
        "label": "Premium Gold ($199)",
    },
]

CSV_FIELDS = [
    "rank",
    "domain",
    "location",
    "niche",
    "category",
    "gold_score",
    "platform",
    "meta_pixel_in_html",
    "ga4_in_html",
    "gtm_in_html",
    "google_ads_in_html",
    "pagespeed_mobile",
    "lcp_ms",
    "response_ms",
    "gold_reasons",
    "outreach_angle",
]


def _lead_to_row(lead: QualifiedLead, rank: int) -> dict:
    return {
        "rank": rank,
        "domain": lead.domain,
        "location": lead.location or "",
        "niche": lead.niche,
        "category": lead.category_name,
        "gold_score": f"{lead.score:.4f}",
        "platform": lead.platform or "Unknown",
        "meta_pixel_in_html": "yes" if lead.meta_pixel_in_html else "no",
        "ga4_in_html": "yes" if lead.ga4_in_html else "no",
        "gtm_in_html": "yes" if lead.gtm_in_html else "no",
        "google_ads_in_html": "yes" if lead.google_ads_in_html else "no",
        "pagespeed_mobile": lead.pagespeed_score if lead.pagespeed_score is not None else "",
        "lcp_ms": lead.lcp_ms if lead.lcp_ms is not None else "",
        "response_ms": lead.response_ms if lead.response_ms is not None else "",
        "gold_reasons": lead.gold_reasons or "",
        "outreach_angle": lead.outreach_angle or "",
    }


def _write_csv(path: Path, leads: list[QualifiedLead]) -> None:
    """Write list of leads to CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for rank, lead in enumerate(leads, start=1):
            writer.writerow(_lead_to_row(lead, rank))


def export_tiered_csvs(
    leads: list[QualifiedLead],
    *,
    output_dir: str | Path,
) -> list[Path]:
    """
    Export 3 tiered CSVs + 1 master CSV.
    Return list of created file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_paths: list[Path] = []

    # --- Master file (internal use) ---
    master_path = output_dir / "leads_all.csv"
    _write_csv(master_path, leads)
    created_paths.append(master_path)
    print(f"[export] OK leads_all.csv         ({len(leads)} leads) - INTERNAL")

    # --- Tiered files ---
    for tier in TIER_CONFIGS:
        filtered = [l for l in leads if l.score >= tier["min_score"]]
        filtered = filtered[: tier["limit"]]

        tier_path = output_dir / tier["filename"]
        _write_csv(tier_path, filtered)
        created_paths.append(tier_path)

        print(
            f"[export] OK {tier['filename']:<28} "
            f"({len(filtered):>3} leads, score >= {tier['min_score']}) "
            f"- {tier['label']}"
        )

    return created_paths
