# src/enrichers.py
"""Site fetch + pixel detection + platform detection + PageSpeed enrichment."""
from __future__ import annotations

import re
import time
from typing import Optional

import httpx

from src.config import PAGESPEED_API_KEY, PAGESPEED_TIMEOUT, REQUEST_TIMEOUT
from src.models import FetchResult, PixelSignals


_MAX_HTML_BYTES = 2_000_000  # 2MB cap untuk proteksi

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ============================================================
# HTTP Fetch (graceful — gak pernah raise)
# ============================================================
async def fetch_site(
    domain: str,
    *,
    client: httpx.AsyncClient,
) -> FetchResult:
    """Fetch HTML dari domain. Coba HTTPS dulu, fallback ke HTTP."""
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        start = time.perf_counter()
        try:
            resp = await client.get(
                url,
                follow_redirects=True,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": _USER_AGENT},
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            # Cap HTML size
            text = resp.text
            if len(text.encode("utf-8", errors="ignore")) > _MAX_HTML_BYTES:
                text = text[:_MAX_HTML_BYTES]

            return FetchResult(
                domain=domain,
                ok=200 <= resp.status_code < 400,
                status_code=resp.status_code,
                response_ms=elapsed_ms,
                html=text,
                headers={k.lower(): v for k, v in resp.headers.items()},
                final_url=str(resp.url),
                error=None,
            )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            last_error = f"{type(e).__name__}: {e}"
            # Coba scheme berikutnya
            continue
        except Exception as e:  # noqa: BLE001
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return FetchResult(
                domain=domain,
                ok=False,
                status_code=0,
                response_ms=elapsed_ms,
                html="",
                headers={},
                final_url=url,
                error=f"{type(e).__name__}: {e}",
            )

    # Kedua scheme gagal
    return FetchResult(
        domain=domain,
        ok=False,
        status_code=0,
        response_ms=0,
        html="",
        headers={},
        final_url=f"https://{domain}",
        error=last_error if 'last_error' in locals() else "Unknown fetch error",
    )


# ============================================================
# Pixel Detection (regex-based, lowercase HTML)
# ============================================================
_PIXEL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "has_meta_pixel": [
        re.compile(r"fbq\s*\(\s*['\"]init['\"]", re.IGNORECASE),
        re.compile(r"connect\.facebook\.net/[^/]+/fbevents\.js", re.IGNORECASE),
        re.compile(r"facebook\.com/tr\?id=", re.IGNORECASE),
    ],
    "has_tiktok_pixel": [
        re.compile(r"analytics\.tiktok\.com/i18n/pixel", re.IGNORECASE),
        re.compile(r"ttq\.load\s*\(", re.IGNORECASE),
    ],
    "has_ga4": [
        re.compile(r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]G-[A-Z0-9]+", re.IGNORECASE),
        re.compile(r"googletagmanager\.com/gtag/js\?id=G-", re.IGNORECASE),
    ],
    "has_gtm": [
        re.compile(r"googletagmanager\.com/gtm\.js\?id=GTM-", re.IGNORECASE),
        re.compile(r"GTM-[A-Z0-9]{4,}", re.IGNORECASE),
    ],
    "has_google_ads": [
        re.compile(r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]AW-", re.IGNORECASE),
        re.compile(r"googleadservices\.com/pagead/conversion", re.IGNORECASE),
    ],
    "has_hotjar": [
        re.compile(r"static\.hotjar\.com", re.IGNORECASE),
        re.compile(r"hjid\s*:\s*\d+", re.IGNORECASE),
    ],
    "has_clarity": [
        re.compile(r"clarity\.ms/tag/", re.IGNORECASE),
        re.compile(r"clarity\s*\(\s*['\"]set['\"]", re.IGNORECASE),
    ],
    "has_linkedin_insight": [
        re.compile(r"snap\.licdn\.com/li\.lms-analytics", re.IGNORECASE),
        re.compile(r"_linkedin_partner_id", re.IGNORECASE),
    ],
}


def detect_pixels(html: str) -> PixelSignals:
    """Deteksi pixel di HTML. Return PixelSignals."""
    if not html:
        return PixelSignals()

    # Lower-case sekali (perf optimization untuk multiple regex)
    # Tapi kita pake re.IGNORECASE di patterns, jadi gak perlu lowercase.

    signals = PixelSignals()
    for field_name, patterns in _PIXEL_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(html):
                setattr(signals, field_name, True)
                break

    return signals


# ============================================================
# Platform Detection
# ============================================================
def detect_platform(html: str, headers: dict[str, str]) -> Optional[str]:
    """Detect CMS / e-commerce platform. Return name atau None."""
    if not html and not headers:
        return None

    headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
    html_lower = html.lower() if html else ""

    # Shopify (header-based paling reliable)
    if any("shopify" in v for v in headers_lower.values()):
        return "Shopify"
    if "cdn.shopify.com" in html_lower or "shopify.theme" in html_lower:
        return "Shopify"

    # WooCommerce (cek dulu sebelum WordPress)
    if "woocommerce" in html_lower or "wp-content/plugins/woocommerce" in html_lower:
        return "WooCommerce"

    # WordPress
    if "wp-content/" in html_lower or "wp-includes/" in html_lower:
        return "WordPress"
    if "generator" in headers_lower.get("x-powered-by", "").lower():
        if "wordpress" in headers_lower["x-powered-by"].lower():
            return "WordPress"

    # Wix
    if "static.wixstatic.com" in html_lower or "wix.com" in html_lower:
        return "Wix"

    # Squarespace
    if "static1.squarespace.com" in html_lower or "squarespace.com" in html_lower:
        return "Squarespace"

    # Webflow
    if "assets.website-files.com" in html_lower or "webflow.com" in html_lower:
        return "Webflow"

    # Magento
    if "mage/" in html_lower or "magento" in html_lower:
        return "Magento"

    # BigCommerce
    if "bigcommerce.com" in html_lower or "cdn11.bigcommerce.com" in html_lower:
        return "BigCommerce"

    return None


# ============================================================
# PageSpeed API
# ============================================================
async def fetch_pagespeed(
    domain: str,
    *,
    client: httpx.AsyncClient,
) -> dict[str, Optional[float]]:
    """Fetch PageSpeed Insights mobile metrics. Return dict dengan score/lcp/fid/cls."""
    empty = {"pagespeed_score": None, "lcp_ms": None, "fid_ms": None, "cls": None}

    if not PAGESPEED_API_KEY:
        return empty

    url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": f"https://{domain}",
        "key": PAGESPEED_API_KEY,
        "strategy": "mobile",
        "category": "performance",
    }

    try:
        resp = await client.get(url, params=params, timeout=PAGESPEED_TIMEOUT)
        if resp.status_code != 200:
            return empty
        data = resp.json()
    except Exception:  # noqa: BLE001
        return empty

    try:
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        perf = categories.get("performance", {})
        score = perf.get("score")
        score_pct = int(round(score * 100)) if isinstance(score, (int, float)) else None

        audits = lighthouse.get("audits", {})
        lcp_audit = audits.get("largest-contentful-paint", {})
        lcp_ms = lcp_audit.get("numericValue")
        lcp_int = int(lcp_ms) if isinstance(lcp_ms, (int, float)) else None

        fid_audit = audits.get("max-potential-fid", {})
        fid_ms = fid_audit.get("numericValue")
        fid_int = int(fid_ms) if isinstance(fid_ms, (int, float)) else None

        cls_audit = audits.get("cumulative-layout-shift", {})
        cls_val = cls_audit.get("numericValue")
        cls_float = float(cls_val) if isinstance(cls_val, (int, float)) else None

        return {
            "pagespeed_score": score_pct,
            "lcp_ms": lcp_int,
            "fid_ms": fid_int,
            "cls": cls_float,
        }
    except Exception:  # noqa: BLE001
        return empty
