# src/enrichers/fetcher.py
from __future__ import annotations
import time

import httpx

from src.models import FetchResult

# Browser-like UA biar nggak langsung diblok WAF/bot-filter.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Batasi ukuran HTML yang diproses (anti memory-bloat dari halaman raksasa).
_MAX_HTML_BYTES = 2_000_000  # 2 MB cukup buat deteksi footprint di <head>


async def fetch_site(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 15.0,
) -> FetchResult:
    """
    Fetch satu URL sekali. Selalu return FetchResult — TIDAK pernah raise.
    Error jaringan/timeout ditangkap dan dimasukin ke field `error`
    (graceful degradation: satu domain mati nggak ngebunuh batch).
    """
    start = time.perf_counter()
    try:
        resp = await client.get(
            url,
            headers=_DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # Ambil HTML, tapi batasi ukurannya
        html = resp.text[:_MAX_HTML_BYTES]
        # Normalisasi headers ke dict[str, str] biasa (httpx.Headers itu khusus)
        headers = {k: v for k, v in resp.headers.items()}

        return FetchResult(
            ok=True,
            status_code=resp.status_code,
            html=html,
            headers=headers,
            response_ms=elapsed_ms,
        )
    except httpx.TimeoutException:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return FetchResult(ok=False, response_ms=elapsed_ms, error="timeout")
    except httpx.HTTPError as e:
        # ConnectError, TooManyRedirects, dll. — semua subclass HTTPError
        return FetchResult(ok=False, error=f"http_error: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001 — last-resort guard, jangan pernah crash batch
        return FetchResult(ok=False, error=f"unexpected: {type(e).__name__}")
