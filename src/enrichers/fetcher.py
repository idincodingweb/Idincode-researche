# src/enrichers/fetcher.py
from __future__ import annotations
import time
import httpx

from src.models import FetchResult

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ApexIntelBot/1.0; "
        "+https://github.com/idiniskandar/apex-intel) "
        "Research/Lead-Qualification"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_MAX_HTML_BYTES = 2_000_000  # 2 MB cap


async def fetch_site(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 15.0,
) -> FetchResult:
    """Fetch one URL. Never raises - always returns FetchResult."""
    start = time.perf_counter()
    try:
        resp = await client.get(
            url, headers=_HEADERS, timeout=timeout, follow_redirects=True,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        html = resp.text[:_MAX_HTML_BYTES]
        headers = dict(resp.headers)
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
        return FetchResult(ok=False, error=f"http_error:{type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        return FetchResult(ok=False, error=f"unexpected:{type(e).__name__}")
