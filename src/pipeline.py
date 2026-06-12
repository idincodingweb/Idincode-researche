# src/pipeline.py
"""Main orchestrator: load → enrich → qualify → analyze → export.

Return summary dict dengan struktur yang dipakai run.py:
- total_targets, reachable, qualified, output_files, duration_seconds
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from src.analyst import enrich_with_ai_analyst
from src.enrichers import enrich_all
from src.export import export_tiered_csvs
from src.loader import load_targets
from src.qualifier import qualify_lead


async def run_pipeline(targets_path: str = "targets.yaml") -> dict[str, Any]:
    """Run full pipeline. Return summary dict untuk reporting di run.py.

    Returns:
        {
            "total_targets": int,
            "reachable": int,
            "qualified": int,
            "output_files": list[str],
            "duration_seconds": float,
        }
    """
    start_ts = time.perf_counter()

    print("=" * 60)
    print("🎯 Apex Market Intelligence | By Idincode")
    print("=" * 60)

    # 1. Load targets
    targets = load_targets(targets_path)
    total_targets = len(targets)
    print(f"[pipeline] Loaded {total_targets} targets from {targets_path}")

    # 2. Normalisasi target (handle Target dataclass ATAU dict)
    normalized_targets = []
    for t in targets:
        if hasattr(t, "to_dict"):
            normalized_targets.append(t.to_dict())
        elif isinstance(t, dict):
            normalized_targets.append(t)
        else:
            normalized_targets.append({
                "domain": getattr(t, "domain", ""),
                "location": getattr(t, "location", None),
                "niche": getattr(t, "niche", "default"),
                "category": getattr(t, "category", None),
            })

    # 3. Enrich (concurrent)
    enrichments = await enrich_all(normalized_targets)

    # 4. Filter unreachable BEFORE scoring
    reachable = [e for e in enrichments if getattr(e, "reachable", True)]
    unreachable = [e for e in enrichments if not getattr(e, "reachable", True)]

    if unreachable:
        print(f"\n[pipeline] WARN: {len(unreachable)} domains unreachable:")
        reasons: dict[str, int] = {}
        for e in unreachable:
            reason = getattr(e, "fail_reason", None) or "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"   - {reason}: {count}")

    # 5. Handle 0 reachable
    if not reachable:
        print("\n[pipeline] FATAL: 0 reachable domains.")
        print("[pipeline]    Penyebab paling umum:")
        print("[pipeline]    - Domain di targets.yaml masih PLACEHOLDER")
        print("[pipeline]    - Belum ada real clinic domain")

        output_files: list[str] = []
        try:
            output_files = export_tiered_csvs([])
        except Exception as e:  # noqa: BLE001
            print(f"[pipeline] export empty failed: {e}")

        duration = round(time.perf_counter() - start_ts, 2)
        print("\n" + "=" * 60)
        print("✅ Pipeline complete (no reachable leads)")
        print("=" * 60)

        return {
            "total_targets": total_targets,
            "reachable": 0,
            "qualified": 0,
            "output_files": output_files,
            "duration_seconds": duration,
        }

    # 6. Qualify (scoring)
    print(f"\n[pipeline] Scoring {len(reachable)} reachable leads...")
    qualified = [qualify_lead(e) for e in reachable]

    # 7. AI Analyst (with fallback)
    qualified = await enrich_with_ai_analyst(qualified)

    # 8. Sort by score (descending)
    qualified.sort(key=lambda x: x.score, reverse=True)

    # 9. Export tiered
    output_files = export_tiered_csvs(qualified)

    duration = round(time.perf_counter() - start_ts, 2)

    print("\n" + "=" * 60)
    print("✅ Pipeline complete!")
    print("=" * 60)

    return {
        "total_targets": total_targets,
        "reachable": len(reachable),
        "qualified": len(qualified),
        "output_files": output_files,
        "duration_seconds": duration,
    }


def main() -> None:
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
