# src/enrichers/pixels.py
from __future__ import annotations
import re

from src.models import PixelSignals

_META = [
    re.compile(r"connect\.facebook\.net/[^/]+/fbevents\.js", re.I),
    re.compile(r"fbq\s*\(\s*['\"]init['\"]", re.I),
    re.compile(r"facebook-pixel", re.I),
]
_TIKTOK = [
    re.compile(r"analytics\.tiktok\.com", re.I),
    re.compile(r"ttq\.load\s*\(", re.I),
]
_GA4 = [
    re.compile(r"googletagmanager\.com/gtag/js\?id=G-", re.I),
    re.compile(r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]G-", re.I),
]
_GTM = [
    re.compile(r"googletagmanager\.com/gtm\.js\?id=GTM-", re.I),
    re.compile(r"GTM-[A-Z0-9]{4,}", re.I),
]
_GOOGLE_ADS = [
    re.compile(r"googletagmanager\.com/gtag/js\?id=AW-", re.I),
    re.compile(r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"]AW-", re.I),
    re.compile(r"googleadservices\.com", re.I),
]


def _matches_any(html: str, patterns) -> bool:
    return any(p.search(html) for p in patterns)


def detect_pixels(html: str) -> PixelSignals:
    if not html:
        return PixelSignals()
    return PixelSignals(
        has_meta=_matches_any(html, _META),
        has_tiktok=_matches_any(html, _TIKTOK),
        has_ga4=_matches_any(html, _GA4),
        has_gtm=_matches_any(html, _GTM),
        has_google_ads=_matches_any(html, _GOOGLE_ADS),
    )
