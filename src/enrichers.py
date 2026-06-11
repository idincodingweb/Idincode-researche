# src/enrichers.py
from __future__ import annotations
import asyncio
import re
import time
import httpx

from src.models import FetchResult, PixelSignals, PageSpeedResult

# ============================================================
# Fetcher
# ============================================================

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ApexIntelBot/1.0; "
        "Research/Lead-Qualification)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_MAX_HTML_BYTES = 2_000_000


async def fetch_site(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 15.0,
) -> FetchResult:
    """Fetch one URL. Never raises."""
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


# ============================================================
# Pixel detection
# ============================================================

_META_PATTERNS = [
    re.compile(r"connect\.facebook\.net/[^/]+/fbevents\.js", re.I),
    re.compile(r"fbq\s*\(\s*['\"]init['\"]", re.I),
    re.compile(r"facebook-pixel", re.I),
]
_TIKTOK_PATTERNS = [
    re.compile(r"analytics\.tiktok\.com", re.I),
    re.compile(r"ttq\.load\s*\(", re.I),
]
_GA4_PATTERNS = [
    re.compile(r"googletagmanager\.com/gtag/js\?id=G-", re.I),
    re.compile(r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]G-", re.I),
]
_GTM_PATTERNS = [
    re.compile(r"googletagmanager\.com/gtm\.js\?id=GTM-", re.I),
    re.compile(r"GTM-[A-Z0-9]{4,}", re.I),
]
_GOOGLE_ADS_PATTERNS = [
    re.compile(r"googletagmanager\.com/gtag/js\?id=AW-", re.I),
    re.compile(r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]AW-", re.I),
    re.compile(r"googleadservices\.com", re.I),
]


def _any_match(html: str, patterns) -> bool:
    return any(p.search(html) for p in patterns)


def detect_pixels(html: str) -> PixelSignals:
    if not html:
        return PixelSignals()
    return PixelSignals(
        has_meta=_any_match(html, _META_PATTERNS),
        has_tiktok=_any_match(html, _TIKTOK_PATTERNS),
        has_ga4=_any_match(html, _GA4_PATTERNS),
        has_gtm=_any_match(html, _GTM_PATTERNS),
        has_google_ads=_any_match(html, _GOOGLE_ADS_PATTERNS),
    )


# ============================================================
# Platform / Tech stack detection
# ============================================================

def detect_platform(html: str, headers: dict[str, str]) -> str | None:
    if not html and not headers:
        return None

    h = {k.lower(): v for k, v in headers.items()}
    html_l = html.lower() if html else ""

    if "x-shopify-stage" in h or "x-shopid" in h:
        return "Shopify"
    if "cdn.shopify.com" in html_l:
        return "Shopify"
    if "wp-content/plugins/woocommerce" in html_l:
        return "WooCommerce"
    if re.search(r"wp-content/(themes|plugins|uploads)", html_l):
        return "WordPress"
    if "x-powered-by" in h and "wordpress" in h["x-powered-by"].lower():
        return "WordPress"
    if "static.wixstatic.com" in html_l:
        return "Wix"
    if "squarespace.com" in html_l:
        return "Squarespace"
    if "webflow.com" in html_l:
        return "Webflow"
    if "x-magento-cache-debug" in h:
        return "Magento"

    return None


# ============================================================
# PageSpeed Insights
# ============================================================

_PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


async def fetch_pagespeed(
    client: httpx.AsyncClient,
    url: str,
    *,
    api_key: str | None,
    timeout: float = 30.0,
) -> PageSpeedResult:
    """Ambil PageSpeed mobile score. Skip kalau no API key."""
    if not api_key:
        return PageSpeedResult(available=False, error="no_api_key")

    params = {
        "url": url,
        "key": api_key,
        "category": "performance",
        "strategy": "mobile",
    }
    try:
        resp = await client.get(_PSI_ENDPOINT, params=params, timeout=timeout)
        if resp.status_code != 200:
            return PageSpeedResult(
                available=False,
                error=f"http_{resp.status_code}",
            )
        data = resp.json()
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        perf = categories.get("performance", {})
        score = perf.get("score")
        score_int = int(score * 100) if isinstance(score, (int, float)) else None

        # LCP
        audits = lighthouse.get("audits", {})
        lcp_audit = audits.get("largest-contentful-paint", {})
        lcp_ms = lcp_audit.get("numericValue")
        lcp_int = int(lcp_ms) if isinstance(lcp_ms, (int, float)) else None

        return PageSpeedResult(
            available=True,
            performance_score=score_int,
            lcp_ms=lcp_int,
        )
    except httpx.TimeoutException:
        return PageSpeedResult(available=False, error="timeout")
    except Exception as e:  # noqa: BLE001
        return PageSpeedResult(available=False, error=f"err:{type(e).__name__}")
