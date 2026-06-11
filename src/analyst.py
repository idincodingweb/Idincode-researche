# src/analyst.py
"""
Claude AI Analyst Layer (via kie.ai)

Tugas modul ini: ngubah data mentah enrichment jadi narasi yang JUAL.

Design choices:
  - Single batch call (semua lead dalam 1 request) untuk hemat token & cepat
  - Graceful degradation: kalo API key kosong / kie.ai down, fallback ke
    template reasoning deterministic (pipeline gak boleh mati gara-gara ini)
  - Structured JSON output dari Claude untuk parsing reliable
"""
from __future__ import annotations
import asyncio
import json
import re
from typing import Any

import httpx

from src.config import (
    IDINCODE_API,
    KIE_AI_BASE_URL,
    KIE_AI_MODEL,
)
from src.models import QualifiedLead


# ============================================================
# Public entry point
# ============================================================

async def enrich_with_ai_analyst(
    leads: list[QualifiedLead],
    *,
    max_retries: int = 2,
) -> list[QualifiedLead]:
    """
    Enrich SEMUA leads dengan AI-generated gold_reasons + outreach_angle.

    Strategy:
      - Kalo IDINCODE_API gak ada -> pakai fallback template (deterministic)
      - Kalo ada -> batch call ke kie.ai, parse JSON response
      - Kalo Claude gagal/timeout -> fallback ke template per-lead
    """
    if not leads:
        return leads

    # No API key -> fallback langsung
    if not IDINCODE_API:
        print("[analyst] IDINCODE_API kosong, pakai fallback template")
        return _apply_fallback_to_all(leads)

    print(f"[analyst] Generating AI reasoning untuk {len(leads)} leads via kie.ai...")

    try:
        ai_results = await _call_claude_batch(leads, max_retries=max_retries)
    except Exception as e:  # noqa: BLE001
        print(f"[analyst] WARN: Claude call failed ({type(e).__name__}: {e}), pakai fallback")
        return _apply_fallback_to_all(leads)

    # Merge AI output ke leads
    enriched: list[QualifiedLead] = []
    for lead in leads:
        ai_data = ai_results.get(lead.domain)
        if ai_data and isinstance(ai_data, dict):
            lead.gold_reasons = ai_data.get("gold_reasons") or _fallback_reasons(lead)
            lead.outreach_angle = ai_data.get("outreach_angle") or _fallback_outreach(lead)
        else:
            # Lead ini gak ke-cover di response Claude -> fallback
            lead.gold_reasons = _fallback_reasons(lead)
            lead.outreach_angle = _fallback_outreach(lead)
        enriched.append(lead)

    print(f"[analyst] OK: AI reasoning generated untuk {len(enriched)} leads")
    return enriched


# ============================================================
# kie.ai API call (OpenAI-compatible endpoint)
# ============================================================

async def _call_claude_batch(
    leads: list[QualifiedLead],
    *,
    max_retries: int,
) -> dict[str, dict[str, str]]:
    """
    Kirim semua lead dalam 1 request, return dict {domain: {gold_reasons, outreach_angle}}.
    """
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(leads)

    payload = {
        "model": KIE_AI_MODEL,
        "max_tokens": 4000,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {IDINCODE_API}",
        "Content-Type": "application/json",
    }

    url = f"{KIE_AI_BASE_URL.rstrip('/')}/chat/completions"

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                text = _extract_text_from_response(data)
                parsed = _parse_json_response(text)
                if parsed:
                    return parsed
                raise ValueError("Empty or invalid JSON from Claude")

            # Rate limit / server error -> retry
            if resp.status_code in (429, 500, 502, 503, 504):
                last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                if attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"[analyst] HTTP {resp.status_code}, retry in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                raise last_error

            # Client error (4xx) -> no retry
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"[analyst] Timeout, retry in {wait}s...")
                await asyncio.sleep(wait)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("Unknown error in _call_claude_batch")


# ============================================================
# Prompt builders
# ============================================================

def _build_system_prompt() -> str:
    return (
        "You are an expert B2B sales analyst specializing in healthcare/medspa "
        "digital marketing. You analyze website tracking infrastructure & performance "
        "data to identify SALES OPPORTUNITIES for marketing agencies.\n\n"
        "Your output is used by agencies to cold-pitch services to plastic surgery "
        "clinics. Be SPECIFIC, ACTIONABLE, and slightly URGENT.\n\n"
        "Rules:\n"
        "1. Output ONLY valid JSON. No markdown fences, no preamble.\n"
        "2. For each domain, generate:\n"
        "   - gold_reasons (1-2 sentences): WHY this is a hot lead. Mention "
        "     specific dollar impact when possible (e.g. 'losing ~$8K/mo from "
        "     missed retargeting').\n"
        "   - outreach_angle (1 sentence): A cold email subject line OR opening "
        "     hook that an agency could use immediately.\n"
        "3. Tone: confident, data-driven, no fluff.\n"
        "4. If a clinic already has good infra (all pixels + fast site), say "
        "   'limited opportunity' honestly - don't fabricate problems.\n"
        "5. Response format MUST be exactly:\n"
        "{\n"
        '  "results": {\n'
        '    "domain1.com": {"gold_reasons": "...", "outreach_angle": "..."},\n'
        '    "domain2.com": {"gold_reasons": "...", "outreach_angle": "..."}\n'
        "  }\n"
        "}"
    )


def _build_user_prompt(leads: list[QualifiedLead]) -> str:
    """Compact lead data jadi tabel ringkas yang Claude bisa cerna."""
    lines = [
        "Analyze these plastic surgery clinics. For each, generate gold_reasons "
        "& outreach_angle. Return JSON only.\n",
        "Data per clinic:",
    ]

    for lead in leads:
        pixels = []
        if lead.meta_pixel_in_html:
            pixels.append("Meta")
        if lead.ga4_in_html:
            pixels.append("GA4")
        if lead.gtm_in_html:
            pixels.append("GTM")
        if lead.google_ads_in_html:
            pixels.append("GoogleAds")
        pixels_str = ",".join(pixels) if pixels else "NONE"

        ps_str = f"{lead.pagespeed_score}" if lead.pagespeed_score is not None else "N/A"
        lcp_str = f"{lead.lcp_ms}ms" if lead.lcp_ms is not None else "N/A"
        rt_str = f"{lead.response_ms}ms" if lead.response_ms else "N/A"

        lines.append(
            f"- domain={lead.domain} | location={lead.location or 'N/A'} | "
            f"platform={lead.platform or 'Unknown'} | pixels_in_html=[{pixels_str}] | "
            f"pagespeed_mobile={ps_str} | lcp={lcp_str} | response_time={rt_str} | "
            f"gold_score={lead.score:.2f}"
        )

    lines.append("\nRemember: output ONLY the JSON object, no markdown, no explanation.")
    return "\n".join(lines)


# ============================================================
# Response parsing
# ============================================================

def _extract_text_from_response(data: dict[str, Any]) -> str:
    """
    Extract text from kie.ai response. Support 2 format:
      1. OpenAI-compatible: data.choices[0].message.content
      2. Anthropic native:  data.content[0].text
    """
    # Format 1: OpenAI-compatible (most likely for kie.ai)
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str) and content:
            return content
        # Sometimes content is list of blocks
        if isinstance(content, list):
            return "".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )

    # Format 2: Anthropic native
    content = data.get("content")
    if isinstance(content, list) and content:
        return "".join(
            b.get("text", "") for b in content if isinstance(b, dict)
        )

    return ""


def _parse_json_response(text: str) -> dict[str, dict[str, str]]:
    """
    Parse JSON dari response. Strip markdown fences kalau ada (defensive).
    Return dict {domain: {gold_reasons, outreach_angle}}.
    """
    if not text:
        return {}

    # Strip markdown code fences kalau Claude lupa rule
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: cari blok JSON pertama dengan regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    results = data.get("results", {})
    if not isinstance(results, dict):
        return {}

    # Normalize: pastikan value selalu dict dengan 2 key
    normalized: dict[str, dict[str, str]] = {}
    for domain, payload in results.items():
        if not isinstance(payload, dict):
            continue
        normalized[domain] = {
            "gold_reasons": str(payload.get("gold_reasons", "")).strip(),
            "outreach_angle": str(payload.get("outreach_angle", "")).strip(),
        }
    return normalized


# ============================================================
# Fallback (deterministic, no API needed)
# ============================================================

def _apply_fallback_to_all(leads: list[QualifiedLead]) -> list[QualifiedLead]:
    """Apply template fallback to all leads. Used when API unavailable."""
    for lead in leads:
        lead.gold_reasons = _fallback_reasons(lead)
        lead.outreach_angle = _fallback_outreach(lead)
    return leads


def _fallback_reasons(lead: QualifiedLead) -> str:
    """Generate gold_reasons deterministic dari data enrichment."""
    reasons = []

    # Missing pixels
    missing = []
    if not lead.meta_pixel_in_html:
        missing.append("Meta Pixel")
    if not lead.ga4_in_html:
        missing.append("GA4")
    if not lead.gtm_in_html:
        missing.append("GTM")
    if not lead.google_ads_in_html:
        missing.append("Google Ads tag")

    if len(missing) >= 3:
        reasons.append(f"Missing {len(missing)} key tracking pixels ({', '.join(missing[:3])}) - major retargeting & attribution gap.")
    elif missing:
        reasons.append(f"Missing {', '.join(missing)} - incomplete attribution stack.")

    # PageSpeed
    if lead.pagespeed_score is not None:
        if lead.pagespeed_score < 50:
            reasons.append(f"Mobile PageSpeed {lead.pagespe
