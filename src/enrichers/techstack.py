# src/enrichers/techstack.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class TechStackResult:
    platform: str | None  # 'Shopify', 'WooCommerce', 'WordPress', 'Wix', dll.

def detect_platform(html: str, headers: dict[str, str]) -> TechStackResult:
    """
    Deteksi platform kombinasi dari HTTP Headers dan HTML source.
    """
    # 1. Cek dari HTTP Headers (Paling akurat)
    headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
    
    if "x-shopify-stage" in headers_lower or "shopify" in headers_lower.get("x-powered-by", ""):
        return TechStackResult(platform="Shopify")
    
    if "x-wix-request-id" in headers_lower:
        return TechStackResult(platform="Wix")

    # 2. Cek dari HTML Footprint (Fallback)
    html_lower = html.lower()
    
    if "cdn.shopify.com" in html_lower:
        return TechStackResult(platform="Shopify")
        
    if "wp-content/plugins/woocommerce" in html_lower:
        return TechStackResult(platform="WooCommerce")
        
    if "wp-content/themes/" in html_lower or "wp-includes/" in html_lower:
        return TechStackResult(platform="WordPress")
        
    if "static.wixstatic.com" in html_lower:
        return TechStackResult(platform="Wix")
        
    if "squarespace.com" in html_lower:
        return TechStackResult(platform="Squarespace")

    return TechStackResult(platform=None)
