# run.py
&quot;&quot;&quot;
Apex Market Intelligence - Entry Point

Run dari command line:
    python run.py

Atau di GitHub Actions, di-trigger otomatis lewat .github/workflows/research.yml
&quot;&quot;&quot;
from __future__ import annotations
import asyncio
import sys
import traceback


def _print_banner() -&gt; None:
    print(&quot;=&quot; * 64)
    print(&quot;  APEX MARKET INTELLIGENCE - Lead Qualification Pipeline&quot;)
    print(&quot;  Built by Idin Iskandar&quot;)
    print(&quot;=&quot; * 64)


def _print_env_status() -&gt; None:
    &quot;&quot;&quot;Print which optional integrations are active.&quot;&quot;&quot;
    from src.config import PAGESPEED_API_KEY, IDINCODE_API

    print(&quot;\n[ENV CHECK]&quot;)
    print(f&quot;  PAGESPEED_API_KEY : {&apos;✅ SET&apos; if PAGESPEED_API_KEY else &apos;⚠️  MISSING (PageSpeed akan di-skip)&apos;}&quot;)
    print(f&quot;  IDINCODE_API      : {&apos;✅ SET&apos; if IDINCODE_API else &apos;⚠️  MISSING (Claude analyst akan di-skip, pakai fallback)&apos;}&quot;)
    print()


async def _async_main() -&gt; int:
    &quot;&quot;&quot;Async entry point. Return exit code.&quot;&quot;&quot;
    from src.pipeline import run_pipeline

    try:
        summary = await run_pipeline(targets_path=&quot;targets.yaml&quot;)
    except FileNotFoundError as e:
        print(f&quot;\n❌ FILE NOT FOUND: {e}&quot;)
        print(&quot;   Pastikan targets.yaml ada di root repo.&quot;)
        return 2

    # Print final summary
    print(&quot;\n&quot; + &quot;=&quot; * 64)
    print(&quot;  PIPELINE COMPLETE&quot;)
    print(&quot;=&quot; * 64)
    print(f&quot;  Total targets       : {summary.get(&apos;total_targets&apos;, 0)}&quot;)
    print(f&quot;  Reachable           : {summary.get(&apos;reachable&apos;, 0)}&quot;)
    print(f&quot;  Qualified leads     : {summary.get(&apos;qualified_count&apos;, 0)}&quot;)
    print(f&quot;  Output files        : {summary.get(&apos;output_files&apos;, 0)}&quot;)
    print(f&quot;  Duration            : {summary.get(&apos;duration_sec&apos;, 0):.1f}s&quot;)

    output_paths = summary.get(&quot;output_paths&quot;, [])
    if output_paths:
        print(&quot;\n  Generated CSVs:&quot;)
        for p in output_paths:
            print(f&quot;    📄 {p}&quot;)

    print()
    return 0 if summary.get(&quot;qualified_count&quot;, 0) &gt;= 0 else 1


def main() -&gt; int:
    &quot;&quot;&quot;Sync wrapper for asyncio.&quot;&quot;&quot;
    _print_banner()
    _print_env_status()

    try:
        return asyncio.run(_async_main())
    except KeyboardInterrupt:
        print(&quot;\n⚠️  Interrupted by user&quot;)
        return 130
    except Exception as e:  # noqa: BLE001
        print(f&quot;\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}&quot;)
        print(&quot;\n--- Traceback ---&quot;)
        traceback.print_exc()
        return 1


if __name__ == &quot;__main__&quot;:
    sys.exit(main())
