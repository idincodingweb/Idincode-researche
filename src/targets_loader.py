# src/targets_loader.py
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from src.models import Target, Category, TargetsConfig


class TargetsValidationError(Exception):
    """Dilempar kalau targets.yaml gak valid. Berisi SEMUA error sekaligus."""
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        msg = "targets.yaml tidak valid:\n" + "\n".join(f"  ✗ {e}" for e in errors)
        super().__init__(msg)


_NICHE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def normalize_domain(raw: str) -> str:
    """
    Bersihin domain ke bentuk kanonik.
      'https://Equinox.com/'  -> 'equinox.com'
      'www.Barry-s.com'       -> 'barry-s.com'  (www DIPERTAHANKAN? lihat catatan)
    """
    raw = raw.strip().lower()
    # Buang scheme kalau ada (pakai urlparse biar robust)
    if "://" in raw:
        raw = urlparse(raw).netloc or urlparse(raw).path
    # Buang trailing slash, path, query
    raw = raw.split("/")[0].split("?")[0]
    # Buang 'www.' di depan biar dedup konsisten
    if raw.startswith("www."):
        raw = raw[4:]
    return raw.strip()


def _is_valid_domain(domain: str) -> bool:
    """Validasi bentuk domain sederhana (bukan resolve DNS)."""
    if not domain or "." not in domain:
        return False
    # Tolak spasi & karakter jelas-jelas salah
    if any(c in domain for c in " \t\n<>\"'"):
        return False
    return True


def _validate_and_build(data: dict[str, Any]) -> TargetsConfig:
    """Validasi struktur + bangun TargetsConfig. Kumpulin semua error."""
    errors: list[str] = []

    # --- meta ---
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("'meta' wajib ada dan berupa mapping.")
        meta = {}
    generated_by = meta.get("generated_by", "")
    version = str(meta.get("version", ""))
    if not generated_by:
        errors.append("'meta.generated_by' wajib diisi.")

    # --- categories ---
    raw_categories = data.get("categories")
    if not isinstance(raw_categories, list) or not raw_categories:
        errors.append("'categories' wajib berupa list dengan minimal 1 item.")
        raise TargetsValidationError(errors)  # fatal: gak bisa lanjut

    categories: list[Category] = []
    seen_category_names: set[str] = set()
    seen_niches: set[str] = set()

    for idx, raw_cat in enumerate(raw_categories):
        prefix = f"categories[{idx}]"
        if not isinstance(raw_cat, dict):
            errors.append(f"{prefix} harus berupa mapping.")
            continue

        name = raw_cat.get("name", "").strip()
        niche = raw_cat.get("niche", "").strip()

        if not name:
            errors.append(f"{prefix}.name wajib diisi.")
        elif name in seen_category_names:
            errors.append(f"{prefix}.name '{name}' duplikat (harus unik).")
        else:
            seen_category_names.add(name)

        if not niche:
            errors.append(f"{prefix}.niche wajib diisi.")
        elif not _NICHE_PATTERN.match(niche):
            errors.append(
                f"{prefix}.niche '{niche}' harus snake_case "
                f"(huruf kecil, angka, underscore; diawali huruf)."
            )
        elif niche in seen_niches:
            errors.append(
                f"{prefix}.niche '{niche}' duplikat — niche jadi nama file output, harus unik."
            )
        else:
            seen_niches.add(niche)

        # --- targets ---
        raw_targets = raw_cat.get("targets")
        built_targets: list[Target] = []
        if not isinstance(raw_targets, list) or not raw_targets:
            errors.append(f"{prefix}.targets wajib berupa list dengan minimal 1 item.")
        else:
            seen_domains: set[str] = set()
            for t_idx, raw_t in enumerate(raw_targets):
                t_prefix = f"{prefix}.targets[{t_idx}]"
                if not isinstance(raw_t, dict):
                    errors.append(f"{t_prefix} harus berupa mapping.")
                    continue
                raw_domain = raw_t.get("domain", "")
                if not raw_domain:
                    errors.append(f"{t_prefix}.domain wajib diisi.")
                    continue

                domain = normalize_domain(str(raw_domain))
                if not _is_valid_domain(domain):
                    errors.append(f"{t_prefix}.domain '{raw_domain}' tidak valid.")
                    continue
                if domain in seen_domains:
                    errors.append(f"{t_prefix}.domain '{domain}' duplikat dalam kategori ini.")
                    continue
                seen_domains.add(domain)

                # Semua field selain 'domain' masuk ke extra
                extra = {k: v for k, v in raw_t.items() if k != "domain"}
                built_targets.append(
                    Target(domain=domain, niche=niche, category_name=name, extra=extra)
                )

        # --- directories (opsional) ---
        raw_dirs = raw_cat.get("directories", [])
        directories = [str(d) for d in raw_dirs] if isinstance(raw_dirs, list) else []

        # Cuma bangun Category kalau field intinya ada (biar gak nyimpen yang rusak)
        if name and niche and built_targets:
            categories.append(
                Category(name=name, niche=niche, targets=built_targets, directories=directories)
            )

    if errors:
        raise TargetsValidationError(errors)

    return TargetsConfig(
        generated_by=generated_by,
        version=version,
        categories=categories,
    )


def load_targets(path: str | Path = "targets.yaml") -> TargetsConfig:
    """
    Entry point: load + validasi targets.yaml.

    Raises:
        FileNotFoundError: kalau file gak ada.
        TargetsValidationError: kalau isinya gak valid (berisi semua error).
        yaml.YAMLError: kalau YAML-nya rusak secara sintaks.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File target tidak ditemukan: {path.resolve()}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise TargetsValidationError(["Root targets.yaml harus berupa mapping (key-value)."])

    return _validate_and_build(raw)
