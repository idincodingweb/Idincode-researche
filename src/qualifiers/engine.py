# src/qualifiers/engine.py
from __future__ import annotations
from src.models import EnrichmentResult, QualifiedLead, QualifierConfig
from src.qualifiers.config import get_config


def _score_reachable(result: EnrichmentResult) -> float:
    """
    Biner: reachable = 1.0, else 0.0.
    (Ya, ini simple, tapi important: lead nggak reachable = waste time.)
    """
    return 1.0 if result.reachable else 0.0


def _score_platform(result: EnrichmentResult, required: set[str]) -> float:
    """
    Kalau ada required_platforms:
      - match exact = 1.0
      - unknown platform + reachable = 0.5 (could be custom, give benefit)
      - nggak match = 0.0
    Kalau nggak ada requirement = 0.5 (neutral, siapa aja OK)
    """
    if not required:
        return 0.5 if result.reachable else 0.0
    
    if result.platform in required:
        return 1.0
    elif result.platform is None and result.reachable:
        # Unknown, tapi site reachable — bisa custom. Ambil setengah kredit.
        return 0.5
    else:
        return 0.0


def _score_pixels(result: EnrichmentResult) -> float:
    """
    Pixel = sinyal sophistication + retargeting capability.
    - Ada 3+ pixel type = 1.0 (sophisticated)
    - Ada 1-2 = 0.6 (moderate)
    - Nol = 0.0
    
    (Ini heuristic, tapi bener: brand yang invest di tracking = serious operator)
    """
    pixel_count = sum([
        result.has_meta_pixel,
        result.has_tiktok_pixel,
        result.has_ga4,
        result.has_gtm,
    ])
    
    if pixel_count >= 3:
        return 1.0
    elif pixel_count >= 1:
        return 0.6
    else:
        return 0.0


def _score_pagespeed(result: EnrichmentResult) -> float:
    """
    PageSpeed score (0-100) normalized ke 0.0-1.0.
    Kalau unavailable:
      - Jangan hardcode 0 (unfair, mungkin ada reason legitimate—API key nggak ada)
      - Return 0.5 (neutral: nggak ada info, tapi juga nggak negative)
    """
    if not result.pagespeed_available:
        return 0.5
    
    if result.pagespeed_score is None:
        return 0.5
    
    return min(result.pagespeed_score / 100.0, 1.0)


def qualify(
    results: list[EnrichmentResult],
) -> list[QualifiedLead]:
    """
    Qualify batch: threshold + score semua, sort descending score.
    """
    qualified = []
    
    for result in results:
        config = get_config(result.niche)
        
        # === THRESHOLD GATES ===
        # Gate 1: Reachable
        if not result.reachable:
            continue
        
        # Gate 2: Response time (too slow = bad UX)
        if result.response_ms and result.response_ms > config.min_response_ms:
            continue
        
        # Gate 3: Required platform
        if config.required_platforms and result.platform not in config.required_platforms:
            # Exception: unknown platform + reachable = give benefit (might be custom)
            if result.platform is not None:
                continue
        
        # Gate 4: PageSpeed (kalau diperlukan)
        if config.min_pagespeed_score is not None:
            if not result.pagespeed_available or result.pagespeed_score is None:
                # Missing data when required — skip
                continue
            if result.pagespeed_score < config.min_pagespeed_score:
                continue
        
        # === SCORING (Weighted Average) ===
        score_reachable = _score_reachable(result)
        score_platform = _score_platform(result, config.required_platforms)
        score_pixels = _score_pixels(result)
        score_pagespeed = _score_pagespeed(result)
        
        # Weighted sum (normalize by total weight)
        weighted_sum = (
            score_reachable * config.weight_reachable
            + score_platform * config.weight_platform
            + score_pixels * config.weight_pixels
            + score_pagespeed * config.weight_pagespeed
        )
        final_score = weighted_sum / config.total_weight
        
        # Breakdown buat transparency (sales team bisa liat kenapa score segini)
        breakdown = {
            "reachable": round(score_reachable * config.weight_reachable / config.total_weight, 3),
            "platform": round(score_platform * config.weight_platform / config.total_weight, 3),
            "pixels": round(score_pixels * config.weight_pixels / config.total_weight, 3),
            "pagespeed": round(score_pagespeed * config.weight_pagespeed / config.total_weight, 3),
        }
        
        qualified.append(QualifiedLead(
            domain=result.domain,
            niche=result.niche,
            category_name=result.category_name,
            score=round(final_score, 3),
            score_breakdown=breakdown,
            response_ms=result.response_ms,
            platform=result.platform,
            has_any_pixel=any([
                result.has_meta_pixel,
                result.has_tiktok_pixel,
                result.has_ga4,
                result.has_gtm,
            ]),
            pagespeed_score=result.pagespeed_score,
            extra=dict(result.extra),
        ))
    
    # Sort descending score (highest potential first)
    qualified.sort(key=lambda x: x.score, reverse=True)
    return qualified
