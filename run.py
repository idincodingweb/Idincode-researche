# run.py
"""Apex Market Intelligence — Lead Qualification Pipeline.

Built by Idin Iskandar.

Usage:
    python run.py                     # default targets.yaml
    python run.py --targets path.yaml # custom path

CI/CD: dipakai di .github/workflows/research.yml
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from src.config import IDINCODE_API, PAGESPEED_API_KEY
from src.pipeline import run_pipeline


def _print_banner() -> None:
    print("=" * 64)
    print("  APEX MARKET INTELLIGENCE - Lead Qualification Pipeline")
    print("  Built by Idin Iskandar")
    print("=" * 64)


def _print_env_status() -> None:
    print("[ENV CHECK]")
    print(f"  PAGESPEED_API_KEY : {'SET' if PAGESPEED_API_KEY else 'MISSING'}")
    print(f"  IDINCODE_API      : {'SET' if IDINCODE_API else 'MISSING'}")


def _print_summary(summary: dict) -> None:
    print("=" * 64)
    print("  PIPELINE COMPLETE")
    print("=" * 64)
    print(f"  Total targets       : {summary['total_targets']}")
    print(f"  Reachable           : {summary['reachable']}")
    print(f"  Qualified leads     : {summary['qualified']}")
    print(f"  Output files        : {len(summary['output_files'])}")
    print(f"  Duration            : {summary['duration_seconds']}s")
    print("  Generated CSVs:")
    for f in summary["output_files"]:
        print(f"    - {f}")


async def _main(yaml_path: str) -> int:
    _print_banner()
    _print_env_status()

    try:
        summary = await run_pipeline(yaml_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[ABORTED] User interrupted.", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"[FATAL] {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    _print_summary(summary)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apex Market Intelligence pipeline"
    )
    parser.add_argument(
        "--targets",
        default="targets.yaml",
        help="Path to targets.yaml (default: targets.yaml)",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(_main(args.targets))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
