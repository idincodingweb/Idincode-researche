# src/pipeline.py
"""
Pipeline Orchestrator

Flow:
  1. Load targets.yaml
  2. Untuk tiap target (concurrent, semaphore-limited):
       a. fetch_site (HTTP GET)
       b. detect_pixels + detect_platform (regex on HTML)
       c. fetch_pagespeed (Google PSI API) — opsional
  3. Build EnrichmentResult per target
  4. Qualify & score → QualifiedLead list
  5. Enrich dengan Claude AI Analyst (gold_reasons + outreach_angle)
  6. Export ke CSV (3 tier: starter/pro/premium)
"""
from __future__ import annotations
import asyncio
import time
from pathlib import Path

import httpx

from src.config import (
    CONCURRENCY,
    REQUEST_TIMEOUT,
    PAGESPEED_TIMEOUT,
    PAGESPEED_API_KEY,
    OUTPUT_DIR,
)
from src.models import EnrichmentResult, Target
from src.targets_loader import load_targets
from src.enrichers import (
    fetch_site,
    detect_pixels,
    detect_platform,
    fetch_pagespeed,
)
from src.qualifier import qualify_leads
from src.analyst import enrich_with_ai_analyst
from src.export import export_tiered_csvs


# ============================================================
# Per-target enrichment
# ============================================================

async def _enrich_one(
    client: httpx.AsyncClient,
    target: Target,
    semaphore: asyncio.Semaphore,
) -> EnrichmentResult:
    """
    Enrich satu target: fetch site + detect pixels + detect platform + pagespeed.
    Never raises — always return EnrichmentResult.
    """
    async with semaphore:
        print(f"[enrich] → {target.domain}")

        # Step 1: fetch HTML
        fetch_result = await fetch_site(
            client, target.url, timeout=REQUEST_TIMEOUT,
        )

        # Kalo gagal fetch, return minimal result
        if not fetch_result.ok:
            return EnrichmentResult(
                domain=target.domain,
                niche=target.niche,
                category_name=target.category_name,
                location=target.location,
                reachable=False,
                status_code=fetch_result.status_code,
                response_ms=fetch_result.response_ms,
                has_meta_pixel=False,
                has_tiktok_pixel=False,
                has_ga4=False,
                has_gtm=False,
                has_google_ads=False,
                platform=None,
                pagespeed_available=False,
                pagespeed_score=None,
                lcp_ms=None,
                error=fetch_result.error,
            )

        # Step 2: detect pixels (regex pada HTML)
        pixels = detect_pixels(fetch_result.html)

        # Step 3: detect platform
        platform = detect_platform(fetch_result.html, fetch_result.headers)

        # Step 4: fetch PageSpeed (parallel-safe, optional)
        ps_result = await fetch_pagespeed(
            client,
            target.url,
            api_key=PAGESPEED_API_KEY,
            timeout=PAGESPEED_TIMEOUT,
        )

        reachable = (
            fetch_result.status_code is not None
            and 200 <= fetch_result.status_code < 400
        )

        return EnrichmentResult(
            domain=target.domain,
            niche=target.niche,
            category_name=target.category_name,
            location=target.location,
            reachable=reachable,
            status_code=fetch_result.status_code,
            response_ms=fetch_result.response_ms,
            has_meta_pixel=pixels.has_meta,
            has_tiktok_pixel=pixels.has_tiktok,
            has_ga4=pixels.has_ga4,
            has_gtm=pixels.has_gtm,
            has_google_ads=pixels.has_google_ads,
            platform=platform,
            pagespeed_available=ps_result.available,
            pagespeed_score=ps_result.performance_score,
            lcp_ms=ps_result.lcp_ms,
            error=None,
        )


# ============================================================
# Main pipeline
# ============================================================

async def run_pipeline(
    *,
    targets_path: str | Path = "targets.yaml",
    output_dir: str | Path = OUTPUT_DIR,
) -> dict:
    """
    Run end-to-end pipeline. Return summary dict untuk run.py print.
    """
    started = time.perf_counter()

    # --- 1. Load targets ---
    print(f"[pipeline] Loading targets from {targets_path}...")
    targets = load_targets(targets_path)
    print(f"[pipeline] ✅ Loaded {len(targets)} targets")

    # --- 2. Concurrent enrichment ---
    print(f"[pipeline] Starting enrichment (concurrency={CONCURRENCY})...")
    semaphore = asyncio.Semaphore(CONCURRENCY)

    # Single httpx client for connection pooling
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        limits=httpx.Limits(
            max_connections=CONCURRENCY * 2,
            max_keepalive_connections=CONCURRENCY,
        ),
    ) as client:
        tasks = [_enrich_one(client, t, semaphore) for t in targets]
        enrichments: list[EnrichmentResult] = await asyncio.gather(*tasks)

    reachable_count = sum(1 for e in enrichments if e.reachable)
    print(f"[pipeline] ✅ Enrichment done. Reachable: {reachable_count}/{len(enrichments)}")

    # --- 3. Score & qualify ---
    print("[pipeline] Scoring leads...")
    leads = qualify_leads(enrichments, min_score=0.0)
    print(f"[pipeline] ✅ {len(leads)} leads scored")

    # Debug: print top 5
    if leads:
        print("\n[pipeline] Top 5 leads by score:")
        for lead in leads[:5]:
            print(
                f"  {lead.score:.3f}  {lead.domain:<40} "
                f"platform={lead.platform or 'N/A':<12} "
                f"pixels={sum([lead.meta_pixel_in_html, lead.ga4_in_html, lead.gtm_in_html, lead.google_ads_in_html])}"
            )

    # --- 4. AI Analyst layer (gold_reasons + outreach_angle) ---
    print("\n[pipeline] Enriching with Claude AI analyst...")
    leads = await enrich_with_ai_analyst(leads)

    # --- 5. Export tiered CSVs ---
    print("\n[pipeline] Exporting tiered CSVs...")
    output_paths = export_tiered_csvs(leads, output_dir=output_dir)
    print(f"[pipeline] ✅ Exported {len(output_paths)} CSV files")

    # --- 6. Build summary ---
    duration = time.perf_counter() - started
    return {
        "total_targets": len(targets),
        "reachable": reachable_count,
        "qualified_count": len(leads),
        "output_files": len(output_paths),
        "output_paths": [str(p) for p in output_paths],
        "duration_sec": duration,
    }
