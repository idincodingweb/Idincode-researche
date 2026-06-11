# === Tambahkan di tests/test_enrichers.py ===
import httpx
from src.models import Target
from src.enrichers.fetcher import fetch_site
from src.enrichers.orchestrator import enrich_target, enrich_all


def _mock_client(handler) -> httpx.AsyncClient:
    """Bikin AsyncClient yang request-nya di-intercept handler (no real network)."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_site_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            html := None,  # placeholder, diganti di bawah
        ) if False else httpx.Response(
            200,
            text="<html><script src='fbevents.js'></script></html>",
            headers={"X-Shopify-Stage": "production"},
        )

    async with _mock_client(handler) as client:
        res = await fetch_site(client, "https://example.com")
    assert res.ok is True
    assert res.status_code == 200
    assert "fbevents.js" in res.html
    assert res.response_ms is not None


async def test_fetch_site_handles_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    async with _mock_client(handler) as client:
        res = await fetch_site(client, "https://dead-domain.test")
    assert res.ok is False
    assert res.error is not None
    assert res.html == ""


async def test_enrich_target_combines_signals():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "<html>"
                "<script src='https://connect.facebook.net/en_US/fbevents.js'></script>"
                "<link href='/wp-content/plugins/woocommerce/x.css'>"
                "</html>"
            ),
            headers={"Content-Type": "text/html"},
        )

    target = Target(domain="example.com", niche="luxury_fitness", category_name="Test")
    async with _mock_client(handler) as client:
        # api_key=None → pagespeed otomatis skip
        res = await enrich_target(client, target, api_key=None)

    assert res.reachable is True
    assert res.has_meta_pixel is True
    assert res.platform == "WooCommerce"
    assert res.pagespeed_available is False
    assert res.pagespeed_score is None


async def test_enrich_target_unreachable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    target = Target(domain="dead.test", niche="medical_high_ticket", category_name="Test")
    async with _mock_client(handler) as client:
        res = await enrich_target(client, target, api_key=None)

    assert res.reachable is False
    assert res.has_meta_pixel is False
    assert res.platform is None
    assert res.error is not None
