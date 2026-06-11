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
# Kie.ai endpoint (Anthropic-native style dengan prefix /claude/)
# CATATAN: Endpoint kie.ai BUKAN OpenAI-compatible.
# Path-nya kustom: /claude/v1/messages (bukan /v1/messages atau /v1/chat/completions)
# ============================================================
KIE_AI_BASE_URL: str = "https://api.kie.ai"
KIE_AI_MESSAGES_PATH: str = "/claude/v1/messages"

# Model name sesuai naming kie.ai (tanpa suffix tanggal)
# Kalau model ini gak available, coba: claude-haiku-4-5, claude-sonnet-4, dll
KIE_AI_MODEL: str = "claude-sonnet-4-5"

# Extended thinking: false untuk batch processing (speed > deep reasoning)
KIE_AI_THINKING: bool = False

# ============================================================
# Output
# ============================================================
OUTPUT_DIR: str = "output"

# ============================================================
# Export Tiering
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
