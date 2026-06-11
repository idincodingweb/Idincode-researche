# src/enrichers/techstack.py
from __future__ import annotations
import re

from src.models import TechStack


def detect_platform(html: str, headers: dict[str, str]) -> TechStack:
    if not html and not headers:
        return TechStack(platform=None)

    h = {k.lower(): v for k, v in headers.items()}
    html_l = html.lower() if html else ""

    if "x-shopify-stage" in h or "x-shopid" in h:
        return TechStack(platform="Shopify")
    if "cdn.shopify.com" in html_l:
        return TechStack
