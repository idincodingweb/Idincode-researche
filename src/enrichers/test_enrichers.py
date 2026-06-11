# tests/test_enrichers.py
import pytest
from src.enrichers.pixels import detect_pixels_in_html
from src.enrichers.techstack import detect_platform

def test_detect_pixels():
    # Test Meta & GA4
    html_1 = """
    <script src="https://connect.facebook.net/en_US/fbevents.js"></script>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXX"></script>
    """
    res_1 = detect_pixels_in_html(html_1)
    assert res_1.has_meta is True
    assert res_1.has_ga4 is True
    assert res_1.has_tiktok is False
    assert res_1.has_gtm is False
    assert res_1.has_any_tracking is True

    # Test Blank
    html_2 = "<html><body><h1>Hello World</h1></body></html>"
    res_2 = detect_pixels_in_html(html_2)
    assert res_2.has_any_tracking is False

def test_detect_techstack_from_headers():
    html = "<html></html>"
    headers = {"X-Shopify-Stage": "production", "Content-Type": "text/html"}
    res = detect_platform(html, headers)
    assert res.platform == "Shopify"

def test_detect_techstack_from_html():
    html = '<link rel="stylesheet" href="/wp-content/plugins/woocommerce/style.css">'
    headers = {"Content-Type": "text/html"}
    res = detect_platform(html, headers)
    assert res.platform == "WooCommerce"

    html_wix = '<script src="https://static.wixstatic.com/js/main.js"></script>'
    assert detect_platform(html_wix, headers).platform == "Wix"
