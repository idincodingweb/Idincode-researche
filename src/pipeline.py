# src/pipeline.py
"""Pipeline orchestrator: load → enrich → qualify → AI analyst → export."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from src.analyst import enrich_with_ai_analyst
from src.config import CONCURRENCY, REQUEST_TIMEOUT
from src.enrichers import (
    detect_pixels,
    detect_platform,
    fetch_pagespeed,
    fetch_site,
)
from src.export import export_tiered_csvs
from src.loader import load_targets
from src.models import EnrichmentResult, QualifiedLead, Target
from src.qualifier import qualify_lead


# ============================================================
# Public entry
# ============================================================
async def run_pipeline(yaml_path: str = "targets.yaml") -> dict[str, Any]:
    """Main pipeline. Return summary dict."""
    start = time.perf_counter()

    print("[pipeline] Loading targets from targets.yaml...")
    targets = load_targets(yaml_path)
    print(f"[pipeline] ✅ Loaded {len(targets)} targets")

    print(f"[pipeline] Starting enrichment (concurrency={CONCURRENCY})...")
    enrichments = await _enrich_all(targets)
    reachable = sum(1 for e in enrichments if e.reachable)
    print(f"[pipeline] ✅ Enrichment done. Reachable: {reachable}/{len(targets)}")

    print("[pipeline] Scoring leads...")
    qualified: list[QualifiedLead] = [qualify_lead(e) for e in enrichments]
    qualified.sort(key=lambda x: x.score, reverse=True)
    print(f"[pipeline] ✅ {len(qualified)} leads scored")

    print("[pipeline] Top 5 leads by score:")
    for lead in qualified[:5]:
        pixels = sum([
            lead.meta_pixel_in_html,
            lead.ga4_in_html,
            lead.gtm_in_html,
            lead.google_ads_in_html,
        ])
        print(
            f"  {lead.score:.3f}  {lead.domain:<40} "
            f"platform={lead.platform or 'N/A':<12} pixels={pixels}"
        )

    print("[pipeline] Enriching with Claude AI analyst...")
    qualified = await enrich_with_ai_analyst(qualified)

    print("[pipeline] Exporting tiered CSVs...")
    output_files = export_tiered_csvs(qualified)
    print(f"[pipeline] ✅ Exported {len(output_files)} CSV files")

    duration = time.perf_counter() - start
    return {
        "total_targets": len(targets),
        "reachable": reachable,
        "qualified": len(qualified),
        "output_files": output_files,
        "duration_seconds": round(duration, 1),
    }


# ============================================================
# Concurrent enrichment
# ============================================================
async def _enrich_all(targets: list[Target]) -> list[EnrichmentResult]:
    """Enrich semua targets dengan concurrency control."""
    semaphore = asyncio.Semaphore(CONCURRENCY)

    timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=10.0)
    limits = httpx.Limits(max_connections=CONCURRENCY * 2, max_keepalive_connections=CONCURRENCY)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        tasks = [_enrich_one(t, client, semaphore) for t in targets]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    return results


async def _enrich_one(
    target: Target,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> EnrichmentResult:
    """Enrich single target. Gak pernah raise — selalu return EnrichmentResult."""
    async with semaphore:
        print(f"[enrich] → {target.domain}")

        result = EnrichmentResult(
            domain=target.domain,
            location=target.location,
            niche=target.niche,
            category=target.category,
        )

        # 1. Fetch HTML
        fetch_result = await fetch_site(target.domain, client=client)
        result.reachable = fetch_result.ok
        result.response_ms = fetch_result.response_ms
        result.status_code = fetch_result.status_code

        if not fetch_result.ok:
            if fetch_result.error:
                result.errors.append(f"fetch: {fetch_result.error}")
            return result

        # 2. Detect pixels & platform
        pixels = detect_pixels(fetch_result.html)
        result.has_meta_pixel = pixels.has_meta_pixel
        result.has_tiktok_pixel = pixels.has_tiktok_pixel  # ← FIX naming konsisten
        result.has_ga4 = pixels.has_ga4
        result.has_gtm = pixels.has_gtm
        result.has_google_ads = pixels.has_google_ads
        result.has_hotjar = pixels.has_hotjar
        result.has_clarity = pixels.has_clarity
        result.has_linkedin_insight = pixels.has_linkedin_insight

        result.platform = detect_platform(fetch_result.html, fetch_result.headers)

        # 3. PageSpeed (parallel-safe karena beda endpoint)
        try:
            ps = await fetch_pagespeed(target.domain, client=client)
            result.pagespeed_score = ps.get("pagespeed_score")
            result.lcp_ms = ps.get("lcp_ms")
            result.fid_ms = ps.get("fid_ms")
            result.cls = ps.get("cls")
        except Exception as e:  # noqa: BLE001
            result.errors.append(f"pagespeed: {type(e).__name__}: {e}")

        return result
