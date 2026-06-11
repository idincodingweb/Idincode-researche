# src/config.py
from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

# Network
CONCURRENCY = 8
REQUEST_TIMEOUT = 15.0
PAGESPEED_TIMEOUT = 30.0

# API Keys (dari environment / GitHub Secrets)
PAGESPEED_API_KEY: str | None = os.getenv("PAGESPEED_API_KEY") or None
IDINCODE_API: str | None = os.getenv("IDINCODE_API") or None

# Kie.ai endpoint (OpenAI-compatible Claude proxy)
KIE_AI_BASE_URL = "https://api.kie.ai/v1"
KIE_AI_MODEL = "claude-sonnet-4-5-20250929"

# Output
OUTPUT_DIR = "output"
