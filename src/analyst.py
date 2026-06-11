# src/analyst.py
&quot;&quot;&quot;
Claude AI Analyst Layer (via kie.ai)

Tugas modul ini: ngubah data mentah enrichment jadi narasi yang JUAL.

Contoh transformasi:
  INPUT  : meta_pixel=False, ga4=True, pagespeed=42, response_ms=3200
  OUTPUT :
    gold_reasons    = &quot;Klinik premium tanpa Meta Pixel — kehilangan retargeting
                       audience worth ~$8K/bulan. Mobile speed 42 = bounce rate
                       tinggi di iPhone user (target demografi mereka).&quot;
    outreach_angle  = &quot;Subject: Found 3 tracking gaps in [clinic name]&apos;s funnel —
                       worth a quick chat?&quot;

Design choices:
  - Single batch call (semua lead dalam 1 request) -&gt; hemat token &amp; cepat
  - Graceful degradation: kalo API key kosong / kie.ai down, fallback ke
    template reasoning deterministic (pipeline gak boleh mati gara-gara ini)
  - Structured JSON output dari Claude -&gt; parsing reliable
&quot;&quot;&quot;
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
) -&gt; list[QualifiedLead]:
    &quot;&quot;&quot;
    Enrich SEMUA leads dengan AI-generated gold_reasons + outreach_angle.

    Strategy:
      - Kalo IDINCODE_API gak ada -&gt; pakai fallback template (deterministic)
      - Kalo ada -&gt; batch call ke kie.ai, parse JSON response
      - Kalo Claude gagal/timeout -&gt; fallback ke template per-lead
    &quot;&quot;&quot;
    if not leads:
        return leads

    # No API key -&gt; fallback langsung
    if not IDINCODE_API:
        print(&quot;[analyst] IDINCODE_API kosong, pakai fallback template&quot;)
        return _apply_fallback_to_all(leads)

    print(f&quot;[analyst] Generating AI reasoning untuk {len(leads)} leads via kie.ai...&quot;)

    try:
        ai_results = await _call_claude_batch(leads, max_retries=max_retries)
    except Exception as e:  # noqa: BLE001
        print(f&quot;[analyst] ⚠️  Claude call failed ({type(e).__name__}: {e}), pakai fallback&quot;)
        return _apply_fallback_to_all(leads)

    # Merge AI output ke leads
    enriched: list[QualifiedLead] = []
    for lead in leads:
        ai_data = ai_results.get(lead.domain)
        if ai_data and isinstance(ai_data, dict):
            lead.gold_reasons = ai_data.get(&quot;gold_reasons&quot;) or _fallback_reasons(lead)
            lead.outreach_angle = ai_data.get(&quot;outreach_angle&quot;) or _fallback_outreach(lead)
        else:
            # Lead ini gak ke-cover di response Claude -&gt; fallback
            lead.gold_reasons = _fallback_reasons(lead)
            lead.outreach_angle = _fallback_outreach(lead)
        enriched.append(lead)

    print(f&quot;[analyst] ✅ AI reasoning generated untuk {len(enriched)} leads&quot;)
    return enriched


# ============================================================
# kie.ai API call (OpenAI-compatible endpoint)
# ============================================================

async def _call_claude_batch(
    leads: list[QualifiedLead],
    *,
    max_retries: int,
) -&gt; dict[str, dict[str, str]]:
    &quot;&quot;&quot;
    Kirim semua lead dalam 1 request, return dict {domain: {gold_reasons, outreach_angle}}.
    &quot;&quot;&quot;
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(leads)

    payload = {
        &quot;model&quot;: KIE_AI_MODEL,
        &quot;max_tokens&quot;: 4000,
        &quot;temperature&quot;: 0.4,
        &quot;messages&quot;: [
            {&quot;role&quot;: &quot;system&quot;, &quot;content&quot;: system_prompt},
            {&quot;role&quot;: &quot;user&quot;, &quot;content&quot;: user_prompt},
        ],
    }

    headers = {
        &quot;Authorization&quot;: f&quot;Bearer {IDINCODE_API}&quot;,
        &quot;Content-Type&quot;: &quot;application/json&quot;,
    }

    url = f&quot;{KIE_AI_BASE_URL.rstrip(&apos;/&apos;)}/chat/completions&quot;

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
                raise ValueError(&quot;Empty or invalid JSON from Claude&quot;)

            # Rate limit / server error -&gt; retry
            if resp.status_code in (429, 500, 502, 503, 504):
                last_error = RuntimeError(f&quot;HTTP {resp.status_code}: {resp.text[:200]}&quot;)
                if attempt &lt; max_retries:
                    wait = 2 ** attempt
                    print(f&quot;[analyst] HTTP {resp.status_code}, retry in {wait}s...&quot;)
                    await asyncio.sleep(wait)
                    continue
                raise last_error

            # Client error (4xx) -&gt; no retry
            raise RuntimeError(f&quot;HTTP {resp.status_code}: {resp.text[:200]}&quot;)

        except httpx.TimeoutException as e:
            last_error = e
            if attempt &lt; max_retries:
                wait = 2 ** attempt
                print(f&quot;[analyst] Timeout, retry in {wait}s...&quot;)
                await asyncio.sleep(wait)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError(&quot;Unknown error in _call_claude_batch&quot;)


# ============================================================
# Prompt builders
# ============================================================

def _build_system_prompt() -&gt; str:
    return (
        &quot;You are an expert B2B sales analyst specializing in healthcare/medspa &quot;
        &quot;digital marketing. You analyze website tracking infrastructure &amp; performance &quot;
        &quot;data to identify SALES OPPORTUNITIES for marketing agencies.\n\n&quot;
        &quot;Your output is used by agencies to cold-pitch services to plastic surgery &quot;
        &quot;clinics. Be SPECIFIC, ACTIONABLE, and slightly URGENT.\n\n&quot;
        &quot;Rules:\n&quot;
        &quot;1. Output ONLY valid JSON. No markdown fences, no preamble.\n&quot;
        &quot;2. For each domain, generate:\n&quot;
        &quot;   - gold_reasons (1-2 sentences): WHY this is a hot lead. Mention &quot;
        &quot;     specific dollar impact when possible (e.g. &apos;losing ~$8K/mo from &quot;
        &quot;     missed retargeting&apos;).\n&quot;
        &quot;   - outreach_angle (1 sentence): A cold email subject line OR opening &quot;
        &quot;     hook that an agency could use immediately.\n&quot;
        &quot;3. Tone: confident, data-driven, no fluff.\n&quot;
        &quot;4. If a clinic already has good infra (all pixels + fast site), say &quot;
        &quot;   &apos;limited opportunity&apos; honestly — don&apos;t fabricate problems.\n&quot;
        &quot;5. Response format MUST be exactly:\n&quot;
        &quot;{\n&quot;
        &apos;  &quot;results&quot;: {\n&apos;
        &apos;    &quot;domain1.com&quot;: {&quot;gold_reasons&quot;: &quot;...&quot;, &quot;outreach_angle&quot;: &quot;...&quot;},\n&apos;
        &apos;    &quot;domain2.com&quot;: {&quot;gold_reasons&quot;: &quot;...&quot;, &quot;outreach_angle&quot;: &quot;...&quot;}\n&apos;
        &quot;  }\n&quot;
        &quot;}&quot;
    )


def _build_user_prompt(leads: list[QualifiedLead]) -&gt; str:
    &quot;&quot;&quot;Compact lead data jadi tabel ringkas yang Claude bisa cerna.&quot;&quot;&quot;
    lines = [
        &quot;Analyze these plastic surgery clinics. For each, generate gold_reasons &quot;
        &quot;&amp; outreach_angle. Return JSON only.\n&quot;,
        &quot;Data per clinic:&quot;,
    ]

    for lead in leads:
        pixels = []
        if lead.meta_pixel_in_html:
            pixels.append(&quot;Meta&quot;)
        if lead.ga4_in_html:
            pixels.append(&quot;GA4&quot;)
        if lead.gtm_in_html:
            pixels.append(&quot;GTM&quot;)
        if lead.google_ads_in_html:
            pixels.append(&quot;GoogleAds&quot;)
        pixels_str = &quot;,&quot;.join(pixels) if pixels else &quot;NONE&quot;

        ps_str = (
            f&quot;{lead.pagespeed_score}&quot;
            if lead.pagespeed_score is not None
            else &quot;N/A&quot;
        )
        lcp_str = (
            f&quot;{lead.lcp_ms}ms&quot;
            if lead.lcp_ms is not None
            else &quot;N/A&quot;
        )
        rt_str = f&quot;{lead.response_ms}ms&quot; if lead.response_ms else &quot;N/A&quot;

        lines.append(
            f&quot;- domain={lead.domain} | location={lead.location or &apos;N/A&apos;} | &quot;
            f&quot;platform={lead.platform or &apos;Unknown&apos;} | pixels_in_html=[{pixels_str}] | &quot;
            f&quot;pagespeed_mobile={ps_str} | lcp={lcp_str} | response_time={rt_str} | &quot;
            f&quot;gold_score={lead.score:.2f}&quot;
        )

    lines.append(
        &quot;\nRemember: output ONLY the JSON object, no markdown, no explanation.&quot;
    )
    return &quot;\n&quot;.join(lines)


# ============================================================
# Response parsing
# ============================================================

def _extract_text_from_response(data: dict[str, Any]) -&gt; str:
    &quot;&quot;&quot;
    Extract text from kie.ai response. Support 2 format:
      1. OpenAI-compatible: data.choices[0].message.content
      2. Anthropic native:  data.content[0].text
    &quot;&quot;&quot;
    # Format 1: OpenAI-compatible (most likely for kie.ai)
    choices = data.get(&quot;choices&quot;)
    if isinstance(choices, list) and choices:
        msg = choices[0].get(&quot;message&quot;, {})
        content = msg.get(&quot;content&quot;, &quot;&quot;)
        if isinstance(content, str) and content:
            return content
        # Sometimes content is list of blocks
        if isinstance(content, list):
            return &quot;&quot;.join(
                b.get(&quot;text&quot;, &quot;&quot;) for b in content if isinstance(b, dict)
            )

    # Format 2: An
