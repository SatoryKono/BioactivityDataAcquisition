#!/usr/bin/env python3
"""Audit and validate effective_optional_v1 derived from current config surface.

This script reports and validates the pragmatic v1 optionality model where
field optionality is derived from:
  - filters.silver_filters.required_fields
  - quality.entity_field_validations(type=required)
  - quality.entity_field_validations(type=not_null)
  - quality.key_nullability(nullable=false)

Usage:
    python scripts/schema/validation/audit_effective_optionality.py
    python scripts/schema/validation/audit_effective_optionality.py --pipeline chembl_activity
    python scripts/schema/validation/audit_effective_optionality.py --json
    python scripts/schema/validation/audit_effective_optionality.py --check

Exit codes:
    0 - Audit printed successfully / no violations under --check
    1 - Violations found under --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from bioetl.application.core.base_transformer.optionality import (
    ConfigSurfaceOptionalityResolver,
    OptionalitySource,
    is_framework_managed_field,
)
from bioetl.composition.factories.pipeline._registry_manifest_chembl import (
    CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline._registry_manifest_non_chembl import (
    NON_CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.infrastructure.config.domain_config_resolver import (
    load_domain_pipeline_config,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIGS_DIR = PROJECT_ROOT / "configs"
ENTITIES_DIR = CONFIGS_DIR / "entities"
_SOURCE_ORDER: tuple[OptionalitySource, ...] = (
    "field_policy_optional_false",
    "field_policy_optional_true",
    "silver_required_fields",
    "dq_required_validation",
    "dq_not_null_validation",
    "dq_key_nullability",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _entity_configs() -> list[Path]:
    result: list[Path] = []
    for path in ENTITIES_DIR.rglob("*.yaml"):
        if path.name.startswith("_"):
            continue
        data = _load_yaml(path)
        provider = str(data.get("provider", path.parent.name))
        if provider == "composite":
            continue
        result.append(path)
    return sorted(result)


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _pipeline_name_from_config(config: dict[str, Any], *, path: Path) -> str:
    pipeline = config.get("pipeline")
    if not isinstance(pipeline, dict):
        raise ValueError(f"{_rel(path)}: missing pipeline section")
    pipeline_name = pipeline.get("pipeline_name")
    if not isinstance(pipeline_name, str) or not pipeline_name.strip():
        raise ValueError(f"{_rel(path)}: missing pipeline.pipeline_name")
    return pipeline_name


def _schema_registry() -> dict[str, object]:
    registry: dict[str, object] = {}
    for item in (*CHEMBL_PIPELINE_CONFIGS, *NON_CHEMBL_PIPELINE_CONFIGS):
        if item.pandera_silver_schema is not None:
            registry[item.pipeline_name] = item.pandera_silver_schema
    return registry


def _resolve_pandera_schema(schema_builder: object) -> Any:
    if hasattr(schema_builder, "columns"):
        return schema_builder
    to_schema = getattr(schema_builder, "to_schema", None)
    if callable(to_schema):
        return to_schema()
    raise TypeError(f"Unsupported Pandera schema builder: {schema_builder!r}")


def _logical_type_from_dtype(dtype_name: str) -> str:
    normalized = dtype_name.lower()
    if normalized == "str" or "string" in normalized:
        return "string"
    if normalized.startswith("int"):
        return "integer"
    if normalized.startswith("float"):
        return "float"
    if normalized == "bool":
        return "boolean"
    return "unknown"


def _apply_field_policy_sources(
    config: dict[str, Any],
    *,
    explicit_expected: dict[str, tuple[OptionalitySource, ...]],
) -> None:
    field_policy = config.get("field_policy")
    if not isinstance(field_policy, dict):
        return
    for field_name, policy in field_policy.items():
        if (
            not isinstance(field_name, str)
            or is_framework_managed_field(field_name)
            or not isinstance(policy, dict)
        ):
            continue
        optional = policy.get("optional")
        if optional is True:
            explicit_expected[field_name] = ("field_policy_optional_true",)
        elif optional is False:
            explicit_expected[field_name] = ("field_policy_optional_false",)


def _apply_required_filter_sources(
    config: dict[str, Any],
    *,
    expected: dict[str, set[OptionalitySource]],
) -> None:
    filters = config.get("filters")
    if not isinstance(filters, dict):
        return
    silver_filters = filters.get("silver_filters")
    if not isinstance(silver_filters, dict):
        return
    for field in silver_filters.get("required_fields") or []:
        if isinstance(field, str) and not is_framework_managed_field(field):
            expected.setdefault(field, set()).add("silver_required_fields")


def _quality_validation_source(item: dict[str, Any]) -> OptionalitySource | None:
    validation_type = item.get("type")
    if validation_type == "required":
        return "dq_required_validation"
    if validation_type == "not_null":
        return "dq_not_null_validation"
    return None


def _optional_field_name(item: dict[str, Any]) -> str | None:
    field = item.get("field")
    if not isinstance(field, str) or is_framework_managed_field(field):
        return None
    return field


def _apply_quality_validation_sources(
    config: dict[str, Any],
    *,
    expected: dict[str, set[OptionalitySource]],
) -> None:
    quality = config.get("quality")
    if not isinstance(quality, dict):
        return
    _apply_entity_field_validation_sources(quality, expected=expected)
    _apply_key_nullability_sources(quality, expected=expected)


def _apply_entity_field_validation_sources(
    quality: dict[str, Any],
    *,
    expected: dict[str, set[OptionalitySource]],
) -> None:
    for item in quality.get("entity_field_validations") or []:
        if not isinstance(item, dict):
            continue
        field = _optional_field_name(item)
        if field is None:
            continue
        source = _quality_validation_source(item)
        if source is not None:
            expected.setdefault(field, set()).add(source)


def _apply_key_nullability_sources(
    quality: dict[str, Any],
    *,
    expected: dict[str, set[OptionalitySource]],
) -> None:
    for item in quality.get("key_nullability") or []:
        if not isinstance(item, dict):
            continue
        field = _optional_field_name(item)
        if field is not None and item.get("nullable") is False:
            expected.setdefault(field, set()).add("dq_key_nullability")


def _ordered_expected_sources(
    expected: dict[str, set[OptionalitySource]],
) -> dict[str, tuple[OptionalitySource, ...]]:
    ordered_expected: dict[str, tuple[OptionalitySource, ...]] = {}
    for field, sources in expected.items():
        ordered_expected[field] = tuple(
            source for source in _SOURCE_ORDER if source in sources
        )
    return ordered_expected


def extract_expected_optionality_sources(
    config: dict[str, Any],
) -> dict[str, tuple[OptionalitySource, ...]]:
    """Collect expected optionality source tags directly from raw YAML."""
    explicit_expected: dict[str, tuple[OptionalitySource, ...]] = {}
    expected: dict[str, set[OptionalitySource]] = {}

    _apply_field_policy_sources(config, explicit_expected=explicit_expected)
    _apply_required_filter_sources(config, expected=expected)
    _apply_quality_validation_sources(config, expected=expected)

    ordered_expected = _ordered_expected_sources(expected)
    ordered_expected.update(explicit_expected)
    return ordered_expected


def _pipeline_names_for_paths(config_paths: list[Path]) -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path in config_paths:
        result[path] = _pipeline_name_from_config(_load_yaml(path), path=path)
    return result


def build_optionality_audit_rows(
    pipeline_names: list[str] | None = None,
    *,
    include_framework: bool = False,
) -> list[dict[str, object]]:
    """Build audit rows for effective optionality across one or more pipelines."""
    registry = _schema_registry()
    selected_pipelines = (
        pipeline_names
        if pipeline_names is not None
        else list(_pipeline_names_for_paths(_entity_configs()).values())
    )
    rows: list[dict[str, object]] = []

    for pipeline_name in selected_pipelines:
        schema_builder = registry.get(pipeline_name)
        if schema_builder is None:
            raise ValueError(f"No Pandera Silver schema registered for {pipeline_name}")
        schema = _resolve_pandera_schema(schema_builder)
        domain_config = load_domain_pipeline_config(pipeline_name)
        resolver = ConfigSurfaceOptionalityResolver.from_domain_config(domain_config)

        for field_name, column in schema.columns.items():
            is_framework = is_framework_managed_field(field_name)
            if is_framework and not include_framework:
                continue
            resolved = resolver.resolve(field_name)
            dtype_name = str(column.dtype)
            rows.append(
                {
                    "pipeline": pipeline_name,
                    "field": field_name,
                    "logical_type": _logical_type_from_dtype(dtype_name),
                    "physical_type": dtype_name,
                    "nullable": column.nullable,
                    "optional": resolved.optional,
                    "sources": list(resolved.sources),
                    "is_framework_field": is_framework,
                }
            )

    rows.sort(key=lambda row: (str(row["pipeline"]), str(row["field"])))
    return rows


def collect_optionality_resolution_violations(
    config_paths: list[Path] | None = None,
) -> list[str]:
    """Return invariant violations for effective_optional_v1 resolution."""
    registry = _schema_registry()
    paths = config_paths if config_paths is not None else _entity_configs()
    violations: list[str] = []

    for path in paths:
        config = _load_yaml(path)
        pipeline_name = _pipeline_name_from_config(config, path=path)
        schema_builder = registry.get(pipeline_name)
        if schema_builder is None:
            violations.append(
                f"INV-CFG-008 {_rel(path)}: no Pandera Silver schema registered for "
                f"pipeline {pipeline_name!r}"
            )
            continue

        schema = _resolve_pandera_schema(schema_builder)
        schema_fields = set(schema.columns)
        expected_sources = extract_expected_optionality_sources(config)

        domain_config = load_domain_pipeline_config(pipeline_name)
        resolver = ConfigSurfaceOptionalityResolver.from_domain_config(domain_config)

        for field_name in sorted(schema_fields):
            if is_framework_managed_field(field_name):
                continue
            resolved = resolver.resolve(field_name)
            expected = expected_sources.get(field_name, ("default_optional",))
            expected_optional = expected == ("default_optional",)
            if resolved.optional != expected_optional or resolved.sources != expected:
                violations.append(
                    f"INV-CFG-008 {_rel(path)}::{field_name}: resolved optionality "
                    f"mismatch. expected optional={expected_optional}, "
                    f"sources={list(expected)}; got optional={resolved.optional}, "
                    f"sources={list(resolved.sources)}"
                )

    return violations


def _print_table(rows: list[dict[str, object]]) -> None:
    print("pipeline\tfield\tlogical_type\tphysical_type\tnullable\toptional\tsources")
    for row in rows:
        print(
            f"{row['pipeline']}\t{row['field']}\t{row['logical_type']}\t"
            f"{row['physical_type']}\t{row['nullable']}\t{row['optional']}\t"
            f"{_render_sources(row.get('sources'))}"
        )


def _render_sources(value: object) -> str:
    """Render a validated optionality source sequence."""
    if not isinstance(value, list):
        return ""
    return ",".join(item for item in value if isinstance(item, str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and validate effective_optional_v1 derived from current "
            "entity config surface."
        )
    )
    parser.add_argument(
        "--pipeline",
        action="append",
        dest="pipelines",
        help="Limit audit/check to one or more pipeline names",
    )
    parser.add_argument(
        "--include-framework",
        action="store_true",
        help="Include framework/system-managed fields in audit output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit audit rows as JSON instead of a tabular text report",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate resolved optionality against raw YAML config signals",
    )
    args = parser.parse_args(argv)

    if args.check:
        all_paths = _entity_configs()
        if args.pipelines:
            selected = set(args.pipelines)
            pipeline_by_path = _pipeline_names_for_paths(all_paths)
            paths = [path for path in all_paths if pipeline_by_path[path] in selected]
        else:
            paths = all_paths

        violations = collect_optionality_resolution_violations(paths)
        if violations:
            for violation in violations:
                print(violation, file=sys.stderr)
            return 1
        print(
            "INV-CFG-008: PASS (effective_optional_v1 matches current config surface)"
        )
        return 0

    rows = build_optionality_audit_rows(
        args.pipelines,
        include_framework=args.include_framework,
    )
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
