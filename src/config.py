# src/config.py
from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

# Network
CONCURRENCY = 10                          # Parallel HTTP requests
REQUEST_TIMEOUT = 15.0                    # Per-request timeout (s)
PAGESPEED_TIMEOUT = 30.0                  # PageSpeed API can be slow

# API Keys
PAGESPEED_API_KEY: str | None = os.getenv("PAGESPEED_API_KEY") or None
IDINCODE_API: str | None = os.getenv("IDINCODE_API") or None  # kie.ai Claude key

# Kie.ai endpoint (OpenAI-compatible Claude)
KIE_AI_BASE_URL = "https://api.kie.ai/v1"
KIE_AI_MODEL = "claude-sonnet-4-5-20250929"  # ganti sesuai model yang lo punya akses

# Output
OUTPUT_DIR = "output"
