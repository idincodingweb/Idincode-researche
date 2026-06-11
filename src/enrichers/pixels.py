# src/enrichers/pixels.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class PixelResult:
    has_meta: bool
    has_tiktok: bool
    has_ga4: bool
    has_gtm: bool

    @property
    def has_any_tracking(self) -> bool:
        return self.has_meta or self.has_tiktok or self.has_ga4 or self.has_gtm

def detect_pixels_in_html(html: str) -> PixelResult:
    """
    Scan HTML untuk footprint tracking script populer.
    Ini pure function, gampang di-test.
    """
    html_lower = html.lower()
    
    # Meta (Facebook) Pixel
    has_meta = "fbevents.js" in html_lower or "connect.facebook.net" in html_lower
    
    # TikTok Pixel
    has_tiktok = "analytics.tiktok.com/i18n/pixel" in html_lower or "ttq.load" in html_lower
    
    # Google Analytics 4 (gtag)
    has_ga4 = "googletagmanager.com/gtag/js" in html_lower
    
    # Google Tag Manager (sering dipakai buat hide pixel lain)
    has_gtm = "googletagmanager.com/gtm.js" in html_lower

    return PixelResult(
        has_meta=has_meta,
        has_tiktok=has_tiktok,
        has_ga4=has_ga4,
        has_gtm=has_gtm
    )
