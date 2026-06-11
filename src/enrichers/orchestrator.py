# src/enrichers/orchestrator.py
from __future__ import annotations
import asyncio
import os

import httpx

from src.models import Target, EnrichmentResult
from src.enrichers.fetcher import fetch_site
from src.enrichers.pixels import detect_pixels_in_html
from src.enrichers.techstack import detect_platform
from src.enrichers.pagespeed import fetch_pagespeed


async def enrich_target(
    client: httpx.AsyncClient,
    target: Target,
    *,
    api_key: str | None,
) -> EnrichmentResult:
    """
    Enrich satu target: fetch 1x, lalu parse semua sinyal dari hasil yang sama.
    Selalu return EnrichmentResult — domain mati pun tetap jadi record.
    """
    fetch = await fetch_site(client, target.url)

    # Domain nggak kejangkau → record minimal, sisa sinyal kosong.
    if not fetch.ok:
        return EnrichmentResult(
            domain=target.domain,
            niche=target.niche,
            category_name=target.category_name,
            reachable=False,
            status_code=fetch.status_code,
            response_ms=fetch.response_ms,
            has_meta_pixel=False,
            has_tiktok_pixel=False,
            has_ga4=False,
            has_gtm=False,
            platform=None,
            pagespeed_available=False,
            pagespeed_score=None,
            error=fetch.error,
            extra=dict(target.extra),
        )

    # Parse pure-function dari HTML/headers yang sama (no extra network).
    pixels = detect_pixels_in_html(fetch.html)
    tech = detect_platform(fetch.html, fetch.headers)

    # PageSpeed terpisah & opsional (skip otomatis kalau no key).
    ps = await fetch_pagespeed(client, target.url, api_key=api_key)

    return EnrichmentResult(
        domain=target.domain,
        niche=target.niche,
        category_name=target.category_name,
        reachable=True,
        status_code=fetch.status_code,
        response_ms=fetch.response_ms,
        has_meta_pixel=pixels.has_meta,
        has_tiktok_pixel=pixels.has_tiktok,
        has_ga4=pixels.has_ga4,
        has_gtm=pixels.has_gtm,
        platform=tech.platform,
        pagespeed_available=ps.available,
        pagespeed_score=ps.performance_score,
        error=None,
        extra=dict(target.extra),
    )


async def enrich_all(
    targets: list[Target],
    *,
    api_key: str | None = None,
    concurrency: int = 8,
) -> list[EnrichmentResult]:
    """
    Enrich banyak target secara konkuren dengan batas (Semaphore = rate-limit sopan).
    concurrency=8 aman buat GitHub Actions (IP shared, jangan agresif).
    """
    if not targets:
        return []

    if api_key is None:
        api_key = os.environ.get("PAGESPEED_API_KEY") or None

    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    async with httpx.AsyncClient(limits=limits) as client:
        async def _bounded(t: Target) -> EnrichmentResult:
            async with sem:
                return await enrich_target(client, t, api_key=api_key)

        # return_exceptions=False aman karena enrich_target nggak pernah raise.
        return await asyncio.gather(*(_bounded(t) for t in targets))
