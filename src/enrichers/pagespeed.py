# src/enrichers/pagespeed.py
from __future__ import annotations

import httpx

from src.models import PageSpeedResult

_PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


async def fetch_pagespeed(
    client: httpx.AsyncClient,
    url: str,
    *,
    api_key: str | None,
    timeout: float = 30.0,
) -> PageSpeedResult:
    """
    Ambil skor performance dari Google PageSpeed Insights.

    Kalau api_key None/kosong → langsung skip (available=False), NGGAK hit network.
    Ini bikin modul ini 'opsional sungguhan': pipeline tetap jalan tanpa key.
    """
    if not api_key:
        return PageSpeedResult(available=False, error="no_api_key")

    params = {
        "url": url,
        "key": api_key,
        "category": "performance",
        "strategy": "mobile",  # mobile = sinyal lebih relevan buat lead modern
    }
    try:
        resp = await client.get(_PSI_ENDPOINT, params=params, timeout=timeout)
        if resp.status_code != 200:
            return PageSpeedResult(available=False, error=f"http_{resp.status_code}")

        data = resp.json()
        # Struktur: lighthouseResult.categories.performance.score (0.0–1.0)
        score_raw = (
            data.get("lighthouseResult", {})
            .get("categories", {})
            .get("performance", {})
            .get("score")
        )
        if score_raw is None:
            return PageSpeedResult(available=False, error="no_score_in_response")

        return PageSpeedResult(
            available=True,
            performance_score=round(float(score_raw) * 100),
        )
    except httpx.HTTPError as e:
        return PageSpeedResult(available=False, error=f"http_error: {type(e).__name__}")
    except (ValueError, KeyError) as e:
        return PageSpeedResult(available=False, error=f"parse_error: {type(e).__name__}")
