#!/usr/bin/env python3
"""Pre-commit hook: validate CI invariants for configs/** directory.

Checks:
  INV-CFG-001  No legacy naming (document->publication, dq/->quality/, filter/->filters/)
  INV-CFG-002  Schema / DQ / filter / source files exist for every pipeline
  INV-CFG-003  loading_strategy is null or 'full_scan_only'
  INV-CFG-004  Providers requiring auth declare API key / mailto env vars
  INV-CFG-005  No unknown top-level keys
  INV-CFG-006  pipeline_name == {provider}_{entity_type}

Usage:
    python scripts/check_config_invariants.py [--verbose]

Exit codes:
    0 - All invariants pass
    1 - Violations found

Pre-commit integration:
    See .pre-commit-config.yaml hook 'check-config-invariants'.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"
PIPELINES_DIR = CONFIGS_DIR / "pipelines"
SOURCES_DIR = CONFIGS_DIR / "sources"
QUALITY_DIR = CONFIGS_DIR / "quality"
FILTERS_DIR = CONFIGS_DIR / "filters"
SCHEMAS_DIR = CONFIGS_DIR / "schemas"

# --- Legacy names (ADR-024) ---
LEGACY_ENTITY_NAMES = {"document", "document_similarity", "document_term"}
LEGACY_PATH_FRAGMENTS = [
    ("../../dq/", "../../quality/"),
    ("../../filter/", "../../filters/"),
]

# --- Auth requirements ---
PROVIDER_AUTH_REQUIREMENTS: dict[str, list[str]] = {
    "openalex": ["mailto"],
    "crossref": ["mailto"],
    "pubmed": ["api_key_env", "email_env"],
}

VALID_LOADING_STRATEGIES = {"full_scan_only"}

# --- Allowed top-level keys ---
PIPELINE_ALLOWED_KEYS = {
    "pipeline_name",
    "provider",
    "entity_type",
    "version",
    "description",
    "batch_size",
    "filter_batch_size",
    "checkpoint_interval",
    "primary_keys",
    "silver_table",
    "gold_table",
    "loading_strategy",
    "source",
    "sink",
    "dq_config_file",
    "dq_overrides",
    "circuit_breaker",
    "filter_config_file",
    "filter_rules",
    "column_groups_file",
    "data_schema_file",
    "column_groups",
    "input_filter",
    "silver_filters",
    "gold_filters",
    "maintenance",
    "transform",
    "extraction_params",
    "page_size_override",
}
COMPOSITE_ALLOWED_KEYS = {
    "composite",
    "gold_filters",
    "silver_filters",
    "filter_config_file",
    "filter_rules",
    "maintenance",
}
SOURCE_ALLOWED_KEYS = {"source", "entities", "entity_notes"}
QUALITY_ALLOWED_KEYS = {
    "version",
    "provider",
    "entity",
    "thresholds",
    "strict_validation",
    "invalid_record_policy",
    "field_validations",
    "cross_field_validations",
    "conditional_validations",
    "report",
    "required_fields",
}
FILTER_ALLOWED_KEYS = {
    "version",
    "provider",
    "entity",
    "input_filter",
    "silver_filters",
    "gold_filters",
    "extraction_params",
    "batch_size",
    "page_size",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _deep_string_search(obj: Any, fragment: str) -> bool:
    if isinstance(obj, str):
        return fragment in obj
    if isinstance(obj, dict):
        return any(_deep_string_search(v, fragment) for v in obj.values())
    if isinstance(obj, list):
        return any(_deep_string_search(item, fragment) for item in obj)
    return False


def _pipeline_configs() -> list[Path]:
    return sorted(
        p for p in PIPELINES_DIR.rglob("*.yaml") if not p.name.startswith("_")
    )


def check_inv_001(verbose: bool) -> list[str]:
    """INV-CFG-001: No legacy naming."""
    errors: list[str] = []
    for path in _pipeline_configs():
        data = _load_yaml(path)
        entity = data.get("entity_type", "")
        if entity in LEGACY_ENTITY_NAMES:
            errors.append(f"INV-CFG-001 {_rel(path)}: entity_type={entity!r} is legacy")
        for legacy, canonical in LEGACY_PATH_FRAGMENTS:
            if _deep_string_search(data, legacy):
                errors.append(
                    f"INV-CFG-001 {_rel(path)}: legacy path {legacy!r} "
                    f"-> use {canonical!r}"
                )
    if verbose and not errors:
        sys.stdout.write("  INV-CFG-001: PASS (no legacy naming)\n")
    return errors


def check_inv_002(verbose: bool) -> list[str]:
    """INV-CFG-002: Companion config files exist."""
    errors: list[str] = []
    providers_checked: set[str] = set()

    for path in _pipeline_configs():
        if "composite" in path.parts:
            continue
        data = _load_yaml(path)
        provider = data.get("provider", path.parent.name)
        entity = data.get("entity_type", path.stem)

        # Schema
        schema = SCHEMAS_DIR / provider / f"{entity}.yaml"
        if not schema.exists():
            errors.append(f"INV-CFG-002 {_rel(path)}: missing {_rel(schema)}")

        # Quality
        dq = QUALITY_DIR / "entities" / provider / f"{entity}.yaml"
        if not dq.exists():
            errors.append(f"INV-CFG-002 {_rel(path)}: missing {_rel(dq)}")

        # Filter
        flt = FILTERS_DIR / "entities" / provider / f"{entity}.yaml"
        if not flt.exists():
            errors.append(f"INV-CFG-002 {_rel(path)}: missing {_rel(flt)}")

        # Source (once per provider)
        if provider not in providers_checked:
            providers_checked.add(provider)
            src = SOURCES_DIR / f"{provider}.yaml"
            if not src.exists():
                errors.append(f"INV-CFG-002: missing {_rel(src)}")

    if verbose and not errors:
        sys.stdout.write("  INV-CFG-002: PASS (all companion files exist)\n")
    return errors


def check_inv_003(verbose: bool) -> list[str]:
    """INV-CFG-003: Valid loading_strategy."""
    errors: list[str] = []
    for path in _pipeline_configs():
        data = _load_yaml(path)
        strategy = data.get("loading_strategy")
        if strategy is not None and strategy not in VALID_LOADING_STRATEGIES:
            errors.append(
                f"INV-CFG-003 {_rel(path)}: loading_strategy={strategy!r} "
                f"invalid (allowed: {VALID_LOADING_STRATEGIES})"
            )
    if verbose and not errors:
        sys.stdout.write("  INV-CFG-003: PASS (loading_strategy values valid)\n")
    return errors


def check_inv_004(verbose: bool) -> list[str]:
    """INV-CFG-004: Provider auth requirements."""
    errors: list[str] = []
    for provider, keys in PROVIDER_AUTH_REQUIREMENTS.items():
        src_path = SOURCES_DIR / f"{provider}.yaml"
        if not src_path.exists():
            continue
        text = src_path.read_text(encoding="utf-8")
        found = [k for k in keys if k in text]
        if not found:
            errors.append(
                f"INV-CFG-004 configs/sources/{provider}.yaml: "
                f"must declare at least one of {keys}"
            )
    if verbose and not errors:
        sys.stdout.write("  INV-CFG-004: PASS (auth requirements met)\n")
    return errors


def check_inv_005(verbose: bool) -> list[str]:
    """INV-CFG-005: No unknown top-level keys."""
    errors: list[str] = []

    # Pipeline configs
    for path in _pipeline_configs():
        data = _load_yaml(path)
        is_composite = "composite" in path.parts
        allowed = COMPOSITE_ALLOWED_KEYS if is_composite else PIPELINE_ALLOWED_KEYS
        unknown = set(data.keys()) - allowed
        if unknown:
            errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")

    # Source configs
    for path in sorted(SOURCES_DIR.glob("*.yaml")):
        data = _load_yaml(path)
        unknown = set(data.keys()) - SOURCE_ALLOWED_KEYS
        if unknown:
            errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")

    # Quality configs (skip defaults)
    for path in sorted(QUALITY_DIR.rglob("*.yaml")):
        if path.name.startswith("_"):
            continue
        data = _load_yaml(path)
        unknown = set(data.keys()) - QUALITY_ALLOWED_KEYS
        if unknown:
            errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")

    # Filter configs (skip defaults)
    for path in sorted(FILTERS_DIR.rglob("*.yaml")):
        if path.name.startswith("_"):
            continue
        data = _load_yaml(path)
        unknown = set(data.keys()) - FILTER_ALLOWED_KEYS
        if unknown:
            errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")

    if verbose and not errors:
        sys.stdout.write("  INV-CFG-005: PASS (no unknown keys)\n")
    return errors


def check_inv_006(verbose: bool) -> list[str]:
    """INV-CFG-006: pipeline_name == {provider}_{entity_type}."""
    errors: list[str] = []
    for path in _pipeline_configs():
        if "composite" in path.parts:
            continue
        data = _load_yaml(path)
        name = data.get("pipeline_name", "")
        provider = data.get("provider", "")
        entity = data.get("entity_type", "")
        expected = f"{provider}_{entity}"
        if name != expected:
            errors.append(
                f"INV-CFG-006 {_rel(path)}: pipeline_name={name!r} "
                f"!= expected {expected!r}"
            )
    if verbose and not errors:
        sys.stdout.write("  INV-CFG-006: PASS (pipeline_name convention)\n")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CI invariants for configs/**"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    all_errors: list[str] = []
    for check_fn in [
        check_inv_001,
        check_inv_002,
        check_inv_003,
        check_inv_004,
        check_inv_005,
        check_inv_006,
    ]:
        all_errors.extend(check_fn(args.verbose))

    if all_errors:
        sys.stderr.write(f"\n{len(all_errors)} config invariant violation(s):\n")
        for err in all_errors:
            sys.stderr.write(f"  {err}\n")
        return 1

    count = len(list(_pipeline_configs()))
    sys.stdout.write(f"All config invariants pass ({count} pipeline configs checked)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
