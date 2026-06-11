# run.py
"""
Apex Market Intelligence - Entry Point

Run dari command line:
    python run.py

Atau di GitHub Actions, di-trigger otomatis lewat .github/workflows/research.yml
"""
from __future__ import annotations
import asyncio
import sys
import traceback


def _print_banner() -> None:
    print("=" * 64)
    print("  APEX MARKET INTELLIGENCE - Lead Qualification Pipeline")
    print("  Built by Idin Iskandar")
    print("=" * 64)


def _print_env_status() -> None:
    """Print which optional integrations are active."""
    from src.config import PAGESPEED_API_KEY, IDINCODE_API

    print("\n[ENV CHECK]")
    ps_status = "SET" if PAGESPEED_API_KEY else "MISSING (PageSpeed akan di-skip)"
    ai_status = "SET" if IDINCODE_API else "MISSING (Claude analyst akan di-skip, pakai fallback)"
    print(f"  PAGESPEED_API_KEY : {ps_status}")
    print(f"  IDINCODE_API      : {ai_status}")
    print()


async def _async_main() -> int:
    """Async entry point. Return exit code."""
    from src.pipeline import run_pipeline

    try:
        summary = await run_pipeline(targets_path="targets.yaml")
    except FileNotFoundError as e:
        print(f"\n[ERROR] FILE NOT FOUND: {e}")
        print("   Pastikan targets.yaml ada di root repo.")
        return 2

    # Print final summary
    print("\n" + "=" * 64)
    print("  PIPELINE COMPLETE")
    print("=" * 64)
    print(f"  Total targets       : {summary.get('total_targets', 0)}")
    print(f"  Reachable           : {summary.get('reachable', 0)}")
    print(f"  Qualified leads     : {summary.get('qualified_count', 0)}")
    print(f"  Output files        : {summary.get('output_files', 0)}")
    print(f"  Duration            : {summary.get('duration_sec', 0):.1f}s")

    output_paths = summary.get("output_paths", [])
    if output_paths:
        print("\n  Generated CSVs:")
        for p in output_paths:
            print(f"    - {p}")

    print()
    return 0 if summary.get("qualified_count", 0) >= 0 else 1


def main() -> int:
    """Sync wrapper for asyncio."""
    _print_banner()
    _print_env_status()

    try:
        return asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\n[WARN] Interrupted by user")
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"\n[ERROR] UNEXPECTED: {type(e).__name__}: {e}")
        print("\n--- Traceback ---")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
