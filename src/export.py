# src/export.py
"""
Tiered CSV Export

Dari 1 dataset hasil pipeline, slice jadi 3 tier produk:

  Tier         | Threshold       | Limit | Filename
  -------------|-----------------|-------|----------------------------------
  Starter      | score >= 0.50   | 25    | leads_starter.csv      ($19)
  Pro          | score >= 0.70   | 100   | leads_pro.csv          ($79)
  Premium      | score >= 0.85   | 50    | leads_premium_gold.csv ($199)

Plus 1 file master:
  leads_all.csv — semua leads (internal use, jangan dijual)
"""
from __future__ import annotations
import csv
from pathlib import Path

from src.models import QualifiedLead


# ============================================================
# Tier config
# ============================================================

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

# Kolom CSV (urut sesuai mata buyer scan dulu)
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


# ============================================================
# Helpers
# ============================================================

def _lead_to_row(lead: QualifiedLead, rank: int) -> dict:
    """Convert QualifiedLead -> dict row untuk CSV."""
    return {
        "rank": rank,
        "domain": lead.domain,
        "location": lead.location or "",
        "niche": lead.niche,
        "category": lead.category_name,
        "gold_score": f"{lead.score:.4f}",
        "platform": lead.platform or
