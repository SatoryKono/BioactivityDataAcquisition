#!/usr/bin/env python3
"""Pre-commit hook: validate CI invariants for configs/** directory.

Checks:
  INV-CFG-001  No legacy naming (document->publication, dq/->quality/, filter/->filters/)
  INV-CFG-002  Unified entity sections exist and provider/entity declarations are consistent
  INV-CFG-003  loading_strategy is null or 'full_scan_only'
  INV-CFG-004  Providers requiring auth declare API key / mailto env vars
  INV-CFG-005  No unknown keys in unified entity/composite/provider configs
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
ENTITIES_DIR = CONFIGS_DIR / "entities"
COMPOSITES_DIR = CONFIGS_DIR / "composites"
PROVIDERS_DIR = CONFIGS_DIR / "providers"

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

# --- Allowed keys ---
PIPELINE_ALLOWED_KEYS = {
    "pipeline_name",
    "provider",
    "entity_type",
    "version",
    "description",
    "batch_size",
    "filter_batch_size",
    "checkpoint_interval",
    "business_primary_keys",
    "technical_primary_key",
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
    "schema_file",
}
ENTITY_ALLOWED_KEYS = {
    "version",
    "provider",
    "entity",
    "pipeline",
    "schema",
    "quality",
    "filters",
    "contracts",
    "hash_policy",
}
COMPOSITE_ALLOWED_KEYS = {
    "composite",
    "gold_filters",
    "silver_filters",
    "filter_config_file",
    "filter_rules",
    "maintenance",
}
PROVIDER_ALLOWED_KEYS = {
    "version",
    "provider",
    "source",
    "quality",
    "filters",
    "entities",
    "entity_notes",
}
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
    "key_nullability",
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
CONTRACT_ALLOWED_KEYS = {
    "primary_key",
    "merge_keys",
    "rename_map",
    "hash_include",
    "hash_exclude",
}
REQUIRED_ENTITY_SECTIONS = {"pipeline", "schema", "quality", "filters", "contracts"}


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


def _entity_configs() -> list[Path]:
    return sorted(
        p for p in ENTITIES_DIR.rglob("*.yaml") if not p.name.startswith("_")
    )


def _provider_configs() -> list[Path]:
    return sorted(
        p for p in PROVIDERS_DIR.glob("*.yaml") if not p.name.startswith("_")
    )


def _composite_configs() -> list[Path]:
    return sorted(
        p for p in COMPOSITES_DIR.glob("*.yaml") if not p.name.startswith("_")
    )


def check_inv_001(verbose: bool) -> list[str]:
    """INV-CFG-001: No legacy naming."""
    errors: list[str] = []
    all_config_paths = [*_entity_configs(), *_provider_configs(), *_composite_configs()]
    for path in all_config_paths:
        data = _load_yaml(path)
        entity = ""
        pipeline = data.get("pipeline")
        if isinstance(pipeline, dict):
            entity = str(pipeline.get("entity_type", ""))
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
    """INV-CFG-002: Unified entity sections and provider declarations are consistent."""
    errors: list[str] = []

    provider_data_by_name = {
        path.stem: _load_yaml(path) for path in _provider_configs()
    }
    declared_pairs: set[tuple[str, str]] = set()
    for provider, pdata in provider_data_by_name.items():
        entities = pdata.get("entities")
        if not isinstance(entities, list) or not entities:
            errors.append(
                f"INV-CFG-002 configs/providers/{provider}.yaml: missing/non-list entities"
            )
            continue
        for entity in entities:
            declared_pairs.add((provider, str(entity)))

    actual_pairs: set[tuple[str, str]] = set()
    for path in _entity_configs():
        provider = path.parent.name
        entity = path.stem
        actual_pairs.add((provider, entity))

        data = _load_yaml(path)
        missing_sections = REQUIRED_ENTITY_SECTIONS - set(data.keys())
        if missing_sections:
            errors.append(
                f"INV-CFG-002 {_rel(path)}: missing sections {sorted(missing_sections)}"
            )

        if not (PROVIDERS_DIR / f"{provider}.yaml").exists():
            errors.append(
                f"INV-CFG-002 {_rel(path)}: missing provider config "
                f"configs/providers/{provider}.yaml"
            )

        if provider in provider_data_by_name:
            entities = provider_data_by_name[provider].get("entities")
            if isinstance(entities, list) and entity not in {str(e) for e in entities}:
                errors.append(
                    f"INV-CFG-002 {_rel(path)}: entity {entity!r} not declared in "
                    f"configs/providers/{provider}.yaml entities[]"
                )

    undeclared = actual_pairs - declared_pairs
    for provider, entity in sorted(undeclared):
        errors.append(
            f"INV-CFG-002 configs/entities/{provider}/{entity}.yaml: missing declaration "
            f"in configs/providers/{provider}.yaml entities[]"
        )

    missing_files = declared_pairs - actual_pairs
    for provider, entity in sorted(missing_files):
        errors.append(
            f"INV-CFG-002 configs/providers/{provider}.yaml: declared entity "
            f"{entity!r} has no file configs/entities/{provider}/{entity}.yaml"
        )

    if verbose and not errors:
        sys.stdout.write("  INV-CFG-002: PASS (entity/provider declarations consistent)\n")
    return errors


def check_inv_003(verbose: bool) -> list[str]:
    """INV-CFG-003: Valid loading_strategy."""
    errors: list[str] = []
    for path in _entity_configs():
        data = _load_yaml(path)
        pipeline = data.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        strategy = pipeline.get("loading_strategy")
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
        src_path = PROVIDERS_DIR / f"{provider}.yaml"
        if not src_path.exists():
            continue
        data = _load_yaml(src_path)
        source = data.get("source")
        provider_config = (
            source.get("provider_config")
            if isinstance(source, dict)
            and isinstance(source.get("provider_config"), dict)
            else {}
        )
        found = [
            key
            for key in keys
            if key in provider_config
            and provider_config.get(key) not in ("", None, [], {})
        ]
        if not found:
            errors.append(
                f"INV-CFG-004 configs/providers/{provider}.yaml: "
                f"must declare at least one of {keys}"
            )
    if verbose and not errors:
        sys.stdout.write("  INV-CFG-004: PASS (auth requirements met)\n")
    return errors


def check_inv_005(verbose: bool) -> list[str]:
    """INV-CFG-005: No unknown keys in unified entity/composite/provider configs."""
    errors: list[str] = []

    # Entity configs
    for path in _entity_configs():
        data = _load_yaml(path)
        unknown = set(data.keys()) - ENTITY_ALLOWED_KEYS
        if unknown:
            errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")

        pipeline = data.get("pipeline")
        if isinstance(pipeline, dict):
            unknown_pipeline = set(pipeline.keys()) - PIPELINE_ALLOWED_KEYS
            if unknown_pipeline:
                errors.append(
                    f"INV-CFG-005 {_rel(path)}: unknown pipeline keys {unknown_pipeline}"
                )

        quality = data.get("quality")
        if isinstance(quality, dict):
            unknown_quality = set(quality.keys()) - QUALITY_ALLOWED_KEYS
            if unknown_quality:
                errors.append(
                    f"INV-CFG-005 {_rel(path)}: unknown quality keys {unknown_quality}"
                )

        filters = data.get("filters")
        if isinstance(filters, dict):
            unknown_filters = set(filters.keys()) - FILTER_ALLOWED_KEYS
            if unknown_filters:
                errors.append(
                    f"INV-CFG-005 {_rel(path)}: unknown filters keys {unknown_filters}"
                )

        contracts = data.get("contracts")
        if isinstance(contracts, dict):
            unknown_contracts = set(contracts.keys()) - CONTRACT_ALLOWED_KEYS
            if unknown_contracts:
                errors.append(
                    f"INV-CFG-005 {_rel(path)}: unknown contracts keys {unknown_contracts}"
                )

    # Provider configs
    for path in _provider_configs():
        data = _load_yaml(path)
        unknown = set(data.keys()) - PROVIDER_ALLOWED_KEYS
        if unknown:
            errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")

        quality = data.get("quality")
        if isinstance(quality, dict):
            unknown_quality = set(quality.keys()) - QUALITY_ALLOWED_KEYS
            if unknown_quality:
                errors.append(
                    f"INV-CFG-005 {_rel(path)}: unknown provider quality keys "
                    f"{unknown_quality}"
                )

        filters = data.get("filters")
        if isinstance(filters, dict):
            unknown_filters = set(filters.keys()) - FILTER_ALLOWED_KEYS
            if unknown_filters:
                errors.append(
                    f"INV-CFG-005 {_rel(path)}: unknown provider filters keys "
                    f"{unknown_filters}"
                )

    # Composite configs
    for path in _composite_configs():
        data = _load_yaml(path)
        unknown = set(data.keys()) - COMPOSITE_ALLOWED_KEYS
        if unknown:
            errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")

    if verbose and not errors:
        sys.stdout.write("  INV-CFG-005: PASS (no unknown keys)\n")
    return errors


def check_inv_006(verbose: bool) -> list[str]:
    """INV-CFG-006: pipeline_name == {provider}_{entity_type}."""
    errors: list[str] = []
    for path in _entity_configs():
        data = _load_yaml(path)
        pipeline = data.get("pipeline")
        if not isinstance(pipeline, dict):
            continue

        name = pipeline.get("pipeline_name", "")
        provider = pipeline.get("provider", data.get("provider", ""))
        entity = pipeline.get("entity_type", data.get("entity", ""))
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

    count = len(list(_entity_configs()))
    sys.stdout.write(f"All config invariants pass ({count} pipeline configs checked)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
