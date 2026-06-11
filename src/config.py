# src/config.py
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Network
# ============================================================
CONCURRENCY: int = int(os.getenv("CONCURRENCY", "8"))
REQUEST_TIMEOUT: float = 15.0
PAGESPEED_TIMEOUT: float = 30.0

# ============================================================
# API Keys (dari environment / GitHub Secrets)
# ============================================================
PAGESPEED_API_KEY: str | None = os.getenv("PAGESPEED_API_KEY") or None
IDINCODE_API: str | None = os.getenv("IDINCODE_API") or None

# ============================================================
# Kie.ai endpoint (OpenAI-compatible Claude proxy)
# ============================================================
KIE_AI_BASE_URL: str = "https://api.kie.ai/v1"
KIE_AI_MODEL: str = "claude-sonnet-4-5-20250929"

# ============================================================
# Output
# ============================================================
OUTPUT_DIR: str = "output"

# ============================================================
# Export Tiering (jangan diturunin tanpa alasan bisnis kuat!)
# ============================================================
TIER_CONFIGS: list[dict] = [
    {
        "filename": "leads_starter.csv",
        "min_score": 0.50,
        "limit": 25,
        "label": "Starter ($19)",
    },
    {
        "filename": "leads_pro.csv",
        "min_score": 0.70,
        "limit": 100,
        "label": "Pro ($79)",
    },
    {
        "filename": "leads_premium_gold.csv",
        "min_score": 0.85,
        "limit": 50,
        "label": "Premium Gold ($199)",
    },
]
