# src/pipeline.py
"""Main orchestrator: load → enrich → qualify → analyze → export."""
from __future__ import annotations

import asyncio

from src.analyst import enrich_with_ai_analyst
from src.enrichers import enrich_all
from src.export import export_tiered_csvs  # ← NAMA ASLI, JANGAN DIUBAH
from src.loader import load_targets
from src.qualifier import qualify_lead


async def run_pipeline(targets_path: str = "targets.yaml") -> None:
    print("=" * 60)
    print("🎯 Apex Market Intelligence | By Idincode")
    print("=" * 60)

    # 1. Load targets
    targets = load_targets(targets_path)
    print(f"[pipeline] Loaded {len(targets)} targets from {targets_path}")

    # 2. Enrich (concurrent)
    enrichments = await enrich_all(targets)

    # 3. Filter unreachable BEFORE scoring
    reachable = [e for e in enrichments if getattr(e, "reachable", True)]
    unreachable = [e for e in enrichments if not getattr(e, "reachable", True)]

    if unreachable:
        print(f"\n[pipeline] ⚠️  {len(unreachable)} domains unreachable:")
        reasons: dict[str, int] = {}
        for e in unreachable:
            reason = getattr(e, "fail_reason", None) or "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"   - {reason}: {count}")

    # 4. Handle 0 reachable — JANGAN crash, bikin empty CSV
    if not reachable:
        print("\n[pipeline] ❌ FATAL: 0 reachable domains.")
        print("[pipeline]    Penyebab paling umum:")
        print("[pipeline]    - Domain di targets.yaml masih PLACEHOLDER (cosmetic-newyork1.com dll)")
        print("[pipeline]    - Belum ada real clinic domain")
        # Tetep export empty supaya artifact upload gak fail
        try:
            export_tiered_csvs([])
        except Exception as e:  # noqa: BLE001
            print(f"[pipeline] export empty failed: {e}")
        return

    # 5. Qualify (scoring)
    print(f"\n[pipeline] Scoring {len(reachable)} reachable leads...")
    qualified = [qualify_lead(e) for e in reachable]

    # 6. AI Analyst (with fallback)
    qualified = await enrich_with_ai_analyst(qualified)

    # 7. Sort by score (descending)
    qualified.sort(key=lambda x: x.score, reverse=True)

    # 8. Export tiered
    export_tiered_csvs(qualified)

    print("\n" + "=" * 60)
    print("✅ Pipeline complete!")
    print("=" * 60)


def main() -> None:
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
