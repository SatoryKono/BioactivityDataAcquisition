#!/usr/bin/env python3
"""Pre-commit hook: validate CI invariants for configs/** directory.

Checks:
  INV-CFG-000  All config governance YAML parses cleanly
  INV-CFG-001  No legacy naming (document->publication, dq/->quality/, filter/->filters/)
  INV-CFG-002  Unified entity sections exist and provider/entity declarations are consistent
  INV-CFG-003  loading_strategy is null or 'full_scan_only'
  INV-CFG-004  Providers with config-bound auth declare named environment references
  INV-CFG-005  No unknown keys in unified entity/composite/provider configs
  INV-CFG-006  pipeline_name == {provider}_{entity_type}
  INV-CFG-008  Provider/entity/section config versions use explicit SemVer scopes
  INV-CFG-009  Composite entity contracts carry complete schema/filter/contract sections
  INV-CFG-010  Provider configs use named env indirection instead of ${...} interpolation

Usage:
    python -m scripts.schema check-invariants [--verbose]

Exit codes:
    0 - All invariants pass
    1 - Violations found

Pre-commit integration:
    See .pre-commit-config.yaml hook 'check-config-invariants'.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence, Set
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.config.config_ci_contract import (
    COMPOSITE_ALLOWED_KEYS,
    CONTRACT_ALLOWED_KEYS,
    ENTITY_ALLOWED_KEYS,
    FILTER_ALLOWED_KEYS,
    LEGACY_ENTITY_NAMES,
    LEGACY_PATH_FRAGMENTS,
    PIPELINE_ALLOWED_KEYS,
    PROVIDER_ALLOWED_KEYS,
    PROVIDER_AUTH_REQUIREMENTS,
    QUALITY_ALLOWED_KEYS,
    REQUIRED_ENTITY_SECTIONS,
    VALID_LOADING_STRATEGIES,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIGS_DIR = PROJECT_ROOT / "configs"
CONTRACTS_DIR = CONFIGS_DIR / "contracts"
ENTITIES_DIR = CONFIGS_DIR / "entities"
COMPOSITES_DIR = CONFIGS_DIR / "composites"
PROVIDERS_DIR = CONFIGS_DIR / "providers"
YAML_GLOB = "*.yaml"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _deep_string_search(obj: Any, fragment: str) -> bool:
    if isinstance(obj, str):
        return fragment in obj
    if isinstance(obj, dict):
        return any(_deep_string_search(v, fragment) for v in obj.values())
    if isinstance(obj, list):
        return any(_deep_string_search(item, fragment) for item in obj)
    return False


def _provider_entity_configs() -> list[Path]:
    return sorted(
        p
        for p in ENTITIES_DIR.rglob(YAML_GLOB)
        if not p.name.startswith("_") and p.parent.name != "composite"
    )


def _composite_entity_configs() -> list[Path]:
    return sorted(
        p
        for p in (ENTITIES_DIR / "composite").glob(YAML_GLOB)
        if not p.name.startswith("_")
    )


def _entity_configs() -> list[Path]:
    return [*_provider_entity_configs(), *_composite_entity_configs()]


def _provider_configs() -> list[Path]:
    return sorted(
        p for p in PROVIDERS_DIR.glob(YAML_GLOB) if not p.name.startswith("_")
    )


def _composite_configs() -> list[Path]:
    return sorted(
        p for p in COMPOSITES_DIR.glob(YAML_GLOB) if not p.name.startswith("_")
    )


def _all_config_paths() -> list[Path]:
    return [*_entity_configs(), *_provider_configs(), *_composite_configs()]


def _config_governance_yaml_paths() -> list[Path]:
    return sorted(p for p in CONFIGS_DIR.rglob(YAML_GLOB) if p.is_file())


def check_inv_000(verbose: bool) -> list[str]:
    """INV-CFG-000: all config governance YAML files must parse cleanly."""
    errors: list[str] = []
    for path in _config_governance_yaml_paths():
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"INV-CFG-000 {_rel(path)}: YAML parse error: {exc}")
    if verbose and not errors:
        sys.stdout.write("  INV-CFG-000: PASS (config governance YAML parses)\n")
    return errors


def _provider_declared_pairs(
    provider_data_by_name: dict[str, dict[str, Any]],
    errors: list[str],
) -> set[tuple[str, str]]:
    """Collect declared provider/entity pairs from provider configs."""
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
    return declared_pairs


def _append_entity_config_consistency_errors(
    path: Path,
    *,
    provider_data_by_name: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[str, str]:
    """Validate one entity config and return its provider/entity pair."""
    provider = path.parent.name
    entity = path.stem
    data = _load_yaml(path)
    missing_sections = REQUIRED_ENTITY_SECTIONS - set(data.keys())
    if missing_sections:
        errors.append(
            f"INV-CFG-002 {_rel(path)}: missing sections {sorted(missing_sections)}"
        )

    provider_path = PROVIDERS_DIR / f"{provider}.yaml"
    if not provider_path.exists():
        errors.append(
            f"INV-CFG-002 {_rel(path)}: missing provider config "
            f"configs/providers/{provider}.yaml"
        )
        return provider, entity

    entities = provider_data_by_name.get(provider, {}).get("entities")
    declared_entities = (
        {str(item) for item in entities} if isinstance(entities, list) else set()
    )
    if declared_entities and entity not in declared_entities:
        errors.append(
            f"INV-CFG-002 {_rel(path)}: entity {entity!r} not declared in "
            f"configs/providers/{provider}.yaml entities[]"
        )
    return provider, entity


def check_inv_001(verbose: bool) -> list[str]:
    """INV-CFG-001: No legacy naming."""
    errors: list[str] = []
    for path in _all_config_paths():
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
    declared_pairs = _provider_declared_pairs(provider_data_by_name, errors)

    actual_pairs: set[tuple[str, str]] = set()
    for path in _provider_entity_configs():
        actual_pairs.add(
            _append_entity_config_consistency_errors(
                path,
                provider_data_by_name=provider_data_by_name,
                errors=errors,
            )
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

    for path in _composite_entity_configs():
        data = _load_yaml(path)
        missing_sections = REQUIRED_ENTITY_SECTIONS - set(data)
        if missing_sections:
            errors.append(
                f"INV-CFG-002 {_rel(path)}: missing sections {sorted(missing_sections)}"
            )
        if data.get("provider") != "composite":
            errors.append(f"INV-CFG-002 {_rel(path)}: provider must be 'composite'")
        if data.get("entity") != path.stem:
            errors.append(
                f"INV-CFG-002 {_rel(path)}: entity must match filename {path.stem!r}"
            )
        if not (COMPOSITES_DIR / path.name).exists():
            errors.append(
                f"INV-CFG-002 {_rel(path)}: missing counterpart "
                f"configs/composites/{path.name}"
            )

    if verbose and not errors:
        sys.stdout.write(
            "  INV-CFG-002: PASS (entity/provider declarations consistent)\n"
        )
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
    """INV-CFG-004: Config-bound provider auth requirements."""
    errors: list[str] = []
    for provider, keys in PROVIDER_AUTH_REQUIREMENTS.items():
        src_path = PROVIDERS_DIR / f"{provider}.yaml"
        if not src_path.exists():
            continue
        data = _load_yaml(src_path)
        source = data.get("source")
        provider_config_raw = (
            source.get("provider_config") if isinstance(source, dict) else None
        )
        provider_config = (
            provider_config_raw if isinstance(provider_config_raw, dict) else {}
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


def _append_unknown_key_errors(
    errors: list[str],
    path: Path,
    data: dict[str, Any],
    *,
    top_level_keys: Set[str],
    nested_fields: Sequence[tuple[str, Set[str], str]],
) -> None:
    unknown = set(data.keys()) - top_level_keys
    if unknown:
        errors.append(f"INV-CFG-005 {_rel(path)}: unknown keys {unknown}")
    for field_name, allowed_keys, label in nested_fields:
        nested = data.get(field_name)
        if not isinstance(nested, dict):
            continue
        unknown_nested = set(nested.keys()) - allowed_keys
        if unknown_nested:
            errors.append(
                f"INV-CFG-005 {_rel(path)}: unknown {label} keys {unknown_nested}"
            )


def check_inv_005(verbose: bool) -> list[str]:
    """INV-CFG-005: No unknown keys in unified entity/composite/provider configs."""
    errors: list[str] = []

    for path in _entity_configs():
        data = _load_yaml(path)
        _append_unknown_key_errors(
            errors,
            path,
            data,
            top_level_keys=ENTITY_ALLOWED_KEYS,
            nested_fields=[
                ("pipeline", PIPELINE_ALLOWED_KEYS, "pipeline"),
                ("quality", QUALITY_ALLOWED_KEYS, "quality"),
                ("filters", FILTER_ALLOWED_KEYS, "filters"),
                ("contracts", CONTRACT_ALLOWED_KEYS, "contracts"),
            ],
        )

    for path in _provider_configs():
        data = _load_yaml(path)
        _append_unknown_key_errors(
            errors,
            path,
            data,
            top_level_keys=PROVIDER_ALLOWED_KEYS,
            nested_fields=[
                ("quality", QUALITY_ALLOWED_KEYS, "provider quality"),
                ("filters", FILTER_ALLOWED_KEYS, "provider filters"),
            ],
        )

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


def check_inv_008(verbose: bool) -> list[str]:
    """INV-CFG-008: config version scopes are explicit SemVer values."""
    errors: list[str] = []
    for path in [*_provider_configs(), *_entity_configs()]:
        data = _load_yaml(path)
        version_scopes: list[tuple[str, object]] = [("version", data.get("version"))]
        for section_name in ("quality", "filters"):
            section = data.get(section_name)
            if isinstance(section, dict):
                version_scopes.append(
                    (f"{section_name}.version", section.get("version"))
                )
        for scope, value in version_scopes:
            if not isinstance(value, str) or not SEMVER_RE.fullmatch(value):
                errors.append(
                    f"INV-CFG-008 {_rel(path)}: {scope}={value!r} must use "
                    "MAJOR.MINOR.PATCH"
                )
    if verbose and not errors:
        sys.stdout.write(
            "  INV-CFG-008: PASS (config version scopes use explicit SemVer)\n"
        )
    return errors


def _runtime_composite_column_groups(data: dict[str, Any]) -> object:
    composite = data.get("composite")
    if not isinstance(composite, dict):
        return None
    schema = composite.get("schema")
    if isinstance(schema, dict) and schema.get("column_groups") is not None:
        return schema.get("column_groups")
    merge = composite.get("merge")
    return merge.get("column_groups") if isinstance(merge, dict) else None


def check_inv_009(verbose: bool) -> list[str]:
    """INV-CFG-009: composite entity contracts are complete and schema-aligned."""
    errors: list[str] = []
    for path in _composite_entity_configs():
        data = _load_yaml(path)
        schema = data.get("schema")
        entity_groups = (
            schema.get("column_groups") if isinstance(schema, dict) else None
        )
        runtime_path = COMPOSITES_DIR / path.name
        runtime_groups = (
            _runtime_composite_column_groups(_load_yaml(runtime_path))
            if runtime_path.exists()
            else None
        )
        if not isinstance(entity_groups, list) or not entity_groups:
            errors.append(
                f"INV-CFG-009 {_rel(path)}: schema.column_groups must be non-empty"
            )
        elif entity_groups != runtime_groups:
            errors.append(
                f"INV-CFG-009 {_rel(path)}: schema.column_groups drift from "
                f"configs/composites/{path.name}"
            )

        filters = data.get("filters")
        if not isinstance(filters, dict):
            errors.append(f"INV-CFG-009 {_rel(path)}: filters must be a mapping")
        else:
            for layer in ("silver_filters", "gold_filters"):
                layer_filters = filters.get(layer)
                required_fields = (
                    layer_filters.get("required_fields")
                    if isinstance(layer_filters, dict)
                    else None
                )
                if not isinstance(required_fields, list) or not required_fields:
                    errors.append(
                        f"INV-CFG-009 {_rel(path)}: "
                        f"filters.{layer}.required_fields must be non-empty"
                    )

        pipeline = data.get("pipeline")
        contracts = data.get("contracts")
        pipeline_keys = (
            pipeline.get("business_primary_keys")
            if isinstance(pipeline, dict)
            else None
        )
        contract_keys = (
            contracts.get("primary_key") if isinstance(contracts, dict) else None
        )
        if not isinstance(contract_keys, list) or contract_keys != pipeline_keys:
            errors.append(
                f"INV-CFG-009 {_rel(path)}: contracts.primary_key must match "
                "pipeline.business_primary_keys"
            )
    if verbose and not errors:
        sys.stdout.write(
            "  INV-CFG-009: PASS (composite entity contracts complete and aligned)\n"
        )
    return errors


def check_inv_010(verbose: bool) -> list[str]:
    """INV-CFG-010: provider configs avoid inline environment interpolation."""
    errors: list[str] = []
    for path in _provider_configs():
        if _deep_string_search(_load_yaml(path), "${"):
            errors.append(
                f"INV-CFG-010 {_rel(path)}: replace inline ${{...}} with a "
                "documented placeholder or named *_env indirection key"
            )
    if verbose and not errors:
        sys.stdout.write(
            "  INV-CFG-010: PASS (provider env indirection is declarative)\n"
        )
    return errors


CHECK_FUNCTIONS = (
    check_inv_001,
    check_inv_002,
    check_inv_003,
    check_inv_004,
    check_inv_005,
    check_inv_006,
    check_inv_008,
    check_inv_009,
    check_inv_010,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate CI invariants for configs/**"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    all_errors: list[str] = []
    parse_errors = check_inv_000(args.verbose)
    if parse_errors:
        all_errors.extend(parse_errors)
    else:
        for check_fn in CHECK_FUNCTIONS:
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
