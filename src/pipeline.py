# src/pipeline.py
"""Main orchestrator: load → enrich → qualify → analyze → export."""
from __future__ import annotations

import asyncio

from src.analyst import enrich_with_ai_analyst
from src.enrichers import enrich_all
from src.export import export_tiered
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

    # 3. Filter unreachable BEFORE scoring (penting!)
    reachable = [e for e in enrichments if e.reachable]
    unreachable = [e for e in enrichments if not e.reachable]

    if unreachable:
        print(f"\n[pipeline] ⚠️  {len(unreachable)} domains unreachable:")
        # Group by fail reason
        reasons: dict[str, int] = {}
        for e in unreachable:
            reason = e.fail_reason or "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"   - {reason}: {count}")

    if not reachable:
        print("\n[pipeline] ❌ FATAL: 0 reachable domains. Check targets.yaml.")
        print("[pipeline]    Common causes:")
        print("[pipeline]    - Domain placeholder belum diganti dengan real domain")
        print("[pipeline]    - DNS belum propagate")
        print("[pipeline]    - GitHub Actions diblok ke domain target")
        # JANGAN exit 1, biarkan pipeline continue dengan empty CSV
        # supaya artifact tetap ada untuk debugging
        export_tiered([], output_dir="output")
        return

    # 4. Qualify (scoring)
    print(f"\n[pipeline] Scoring {len(reachable)} reachable leads...")
    qualified = [qualify_lead(e) for e in reachable]

    # 5. AI Analyst (with fallback)
    qualified = await enrich_with_ai_analyst(qualified)

    # 6. Sort by score (descending)
    qualified.sort(key=lambda x: x.score, reverse=True)

    # 7. Export tiered
    export_tiered(qualified, output_dir="output")

    print("\n" + "=" * 60)
    print("✅ Pipeline complete!")
    print("=" * 60)


def main() -> None:
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
