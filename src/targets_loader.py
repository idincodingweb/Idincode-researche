# src/targets_loader.py
from __future__ import annotations
from pathlib import Path
import yaml

from src.models import Target


def load_targets(path: str | Path = "targets.yaml") -> list[Target]:
    """Parse targets.yaml -> list of Target objects."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"targets.yaml not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    targets: list[Target] = []
    for category in data.get("categories", []):
        cat_name = category.get("name", "")
        niche = category.get("niche", "unknown")
        for t in category.get("targets", []):
            if not isinstance(t, dict) or "domain" not in t:
                continue
            domain = t["domain"].strip()
            extra = {k: v for k, v in t.items() if k != "domain"}
            targets.append(Target(
                domain=domain,
                niche=niche,
                category_name=cat_name,
                extra=extra,
            ))
    return targets
