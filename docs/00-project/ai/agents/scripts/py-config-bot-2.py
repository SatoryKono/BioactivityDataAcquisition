#!/usr/bin/env python3
"""Validate unified pipeline and composite configs against JSON schemas.

In addition to JSON Schema checks, this script performs normalized invariants
checks for runtime-critical fields (e.g., deterministic ``sort_by``), using
``configs/base/pipeline.yaml`` defaults merged with entity ``pipeline`` payload.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema
except ImportError:
    sys.stderr.write("ERROR: jsonschema not installed. Run: pip install jsonschema\n")
    sys.exit(2)


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load JSON Schema from file."""
    if not schema_path.exists():
        sys.stderr.write(f"ERROR: Schema file not found: {schema_path}\n")
        sys.exit(2)
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _find_entity_files(entities_dir: Path) -> list[Path]:
    return [
        p
        for p in sorted(entities_dir.rglob("*.yaml"))
        if not p.name.startswith("_") and not _is_legacy_composite_entity_stub(p)
    ]


def _find_composite_files(composites_dir: Path) -> list[Path]:
    return [
        p for p in sorted(composites_dir.glob("*.yaml")) if not p.name.startswith("_")
    ]


def _is_legacy_composite_entity_stub(config_path: Path) -> bool:
    """Return True for historical composite-shaped entity payloads, if any remain.

    Composite runtime is sourced from ``configs/composites/*.yaml``. This helper
    now acts as a defensive guard in case an old composite-shaped entity file is
    reintroduced under ``configs/entities``.
    """
    try:
        payload = _load_yaml_payload(config_path)
    except yaml.YAMLError:
        return False
    if payload is None:
        return False
    provider = str(payload.get("provider") or config_path.parent.name).strip().lower()
    return provider == "composite"


def _validate_yaml_schema(payload: Any, schema: dict[str, Any]) -> tuple[bool, str]:
    try:
        jsonschema.validate(payload, schema)
        return True, ""
    except jsonschema.ValidationError as exc:
        path = ".".join(str(part) for part in exc.path)
        suffix = f" at {path}" if path else ""
        return False, f"Schema validation: {exc.message}{suffix}"


def _deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dicts with override precedence."""
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(current, value)
            continue
        merged[key] = value
    return merged


def _load_base_pipeline_defaults(configs_root: Path) -> dict[str, Any]:
    """Load consolidated base pipeline defaults from configs/base/pipeline.yaml."""
    base_path = configs_root / "base" / "pipeline.yaml"
    if not base_path.exists():
        return {}
    payload = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _build_normalized_pipeline_payload(
    entity_payload: dict[str, Any],
    pipeline_payload: dict[str, Any],
    base_pipeline_defaults: dict[str, Any],
) -> dict[str, Any]:
    """Build runtime-like normalized pipeline payload for invariants checks.

    Merge order:
    1. base defaults (configs/base/pipeline.yaml)
    2. entity pipeline section (configs/entities/*/*.yaml::pipeline)
    3. top-level provider/entity fallbacks from entity YAML (if missing)
    """
    normalized = _deep_merge_dicts(base_pipeline_defaults, pipeline_payload)

    provider = entity_payload.get("provider")
    entity = entity_payload.get("entity")
    if provider and not normalized.get("provider"):
        normalized["provider"] = provider
    if entity and not normalized.get("entity_type"):
        normalized["entity_type"] = entity

    return normalized


def _validate_pipeline_payload(pipeline_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("pipeline_name", "provider", "entity_type", "business_primary_keys")
    for key in required:
        if key not in pipeline_payload:
            errors.append(f"Missing pipeline key: {key}")

    keys = pipeline_payload.get("business_primary_keys")
    if not isinstance(keys, list) or not keys:
        errors.append("pipeline.business_primary_keys must be a non-empty list")
    return errors


def _validate_runtime_normalized_invariants(
    pipeline_payload: dict[str, Any],
) -> list[str]:
    """Validate runtime-critical invariants after base/default normalization."""
    errors: list[str] = []

    sink = pipeline_payload.get("sink", {})
    if not isinstance(sink, dict):
        errors.append("pipeline.sink must be a mapping after normalization")
        return errors

    errors.extend(_validate_silver_runtime_format(sink))
    for layer in ("silver", "gold"):
        errors.extend(_validate_enabled_sink_layer(layer, sink.get(layer)))
    return errors


def _validate_silver_runtime_format(sink: dict[str, Any]) -> list[str]:
    """Validate runtime format requirement for the silver sink."""
    silver_cfg = sink.get("silver")
    if not isinstance(silver_cfg, dict) or not silver_cfg.get("enabled", True):
        return []
    silver_format = silver_cfg.get("format")
    if silver_format == "delta":
        return []
    return [f"sink.silver.format must be 'delta' for runtime (got: {silver_format!r})"]


def _validate_enabled_sink_layer(layer: str, layer_cfg: Any) -> list[str]:
    """Validate one enabled sink layer after runtime normalization."""
    if not isinstance(layer_cfg, dict):
        return [f"sink.{layer} must be a mapping after normalization"]
    if not layer_cfg.get("enabled", True):
        return []
    sort_by = layer_cfg.get("sort_by")
    if not isinstance(sort_by, list) or not sort_by:
        return [f"sink.{layer}.sort_by must be a non-empty list after normalization"]
    errors: list[str] = []
    normalized_columns = [str(col).strip() for col in sort_by]
    if any(not col for col in normalized_columns):
        errors.append(f"sink.{layer}.sort_by contains empty column names")
    if len(normalized_columns) != len(set(normalized_columns)):
        errors.append(f"sink.{layer}.sort_by contains duplicate columns")
    return errors


def _validate_entity_config_sections(entity_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for section in ("pipeline", "schema", "quality", "filters", "contracts"):
        if section not in entity_payload:
            errors.append(f"Missing required top-level section: {section}")
    return errors


def _validate_provider_entity_consistency(entity_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    provider = entity_payload.get("provider")
    entity = entity_payload.get("entity")
    pipeline = entity_payload.get("pipeline")
    if not isinstance(pipeline, dict):
        return errors

    pipeline_provider = pipeline.get("provider")
    pipeline_entity = pipeline.get("entity_type")
    if provider and pipeline_provider and provider != pipeline_provider:
        errors.append(
            f"provider mismatch: top-level '{provider}' vs pipeline '{pipeline_provider}'"
        )
    if entity and pipeline_entity and entity != pipeline_entity:
        errors.append(
            f"entity mismatch: top-level '{entity}' vs pipeline '{pipeline_entity}'"
        )
    return errors


def _validate_sink_paths_and_sort(pipeline_payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []

    provider = pipeline_payload.get("provider", "")
    entity = pipeline_payload.get("entity_type", "")
    expected_suffix = f"{provider}/{entity}" if provider and entity else ""
    sink = pipeline_payload.get("sink", {})
    if not isinstance(sink, dict):
        return warnings

    for layer in ("bronze", "silver", "gold"):
        layer_cfg = sink.get(layer, {})
        if not isinstance(layer_cfg, dict):
            continue
        layer_path = layer_cfg.get("path", "")
        if expected_suffix and isinstance(layer_path, str) and layer_path:
            if not layer_path.endswith(expected_suffix):
                warnings.append(
                    f"sink.{layer}.path should end with '{expected_suffix}', got: {layer_path}"
                )

    return warnings


def _load_yaml_payload(config_path: Path) -> dict[str, Any] | None:
    """Load a YAML mapping payload from disk."""
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else None


def _append_prefixed(messages: list[str], prefix: Path, items: list[str]) -> None:
    """Append validation messages with a config path prefix."""
    messages.extend(f"{prefix}: {item}" for item in items)


def _process_entity_config(
    config_path: Path,
    *,
    verbose: bool,
    pipeline_schema: dict[str, Any],
    base_pipeline_defaults: dict[str, Any],
    skip_runtime_normalized_check: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Validate one entity config and append findings to shared collections."""
    if verbose:
        sys.stdout.write(f"Checking entity: {config_path}\n")
    try:
        payload = _load_yaml_payload(config_path)
    except yaml.YAMLError as exc:
        errors.append(f"{config_path}: YAML parse error: {exc}")
        return
    if payload is None:
        errors.append(f"{config_path}: entity config must be a YAML mapping")
        return
    _append_prefixed(errors, config_path, _validate_entity_config_sections(payload))
    _append_prefixed(
        errors, config_path, _validate_provider_entity_consistency(payload)
    )
    pipeline_payload = payload.get("pipeline")
    if not isinstance(pipeline_payload, dict):
        errors.append(f"{config_path}: missing or invalid 'pipeline' section")
        return
    valid_pipeline, pipeline_schema_error = _validate_yaml_schema(
        pipeline_payload, pipeline_schema
    )
    if not valid_pipeline:
        errors.append(f"{config_path}: {pipeline_schema_error}")
    _append_prefixed(errors, config_path, _validate_pipeline_payload(pipeline_payload))
    normalized_payload = _build_normalized_pipeline_payload(
        payload,
        pipeline_payload,
        base_pipeline_defaults,
    )
    if not skip_runtime_normalized_check:
        _append_prefixed(
            errors,
            config_path,
            _validate_runtime_normalized_invariants(normalized_payload),
        )
    _append_prefixed(
        warnings, config_path, _validate_sink_paths_and_sort(normalized_payload)
    )


def _process_composite_config(
    config_path: Path,
    *,
    verbose: bool,
    composite_schema: dict[str, Any],
    errors: list[str],
) -> None:
    """Validate one composite config and append findings."""
    if verbose:
        sys.stdout.write(f"Checking composite: {config_path}\n")
    try:
        payload = _load_yaml_payload(config_path)
    except yaml.YAMLError as exc:
        errors.append(f"{config_path}: YAML parse error: {exc}")
        return
    if payload is None:
        errors.append(f"{config_path}: composite config must be a YAML mapping")
        return
    valid, err_msg = _validate_yaml_schema(payload, composite_schema)
    if not valid:
        errors.append(f"{config_path}: {err_msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate unified pipeline configs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (path hierarchy checks)",
    )
    parser.add_argument(
        "--skip-runtime-normalized-check",
        action="store_true",
        help="Skip runtime-normalized invariants check (not recommended).",
    )
    args = parser.parse_args()

    configs_root = Path("configs")
    schema_dir = Path("configs/_schema")
    pipeline_schema = load_schema(schema_dir / "pipeline.json")
    composite_schema = load_schema(schema_dir / "composite.json")
    base_pipeline_defaults = _load_base_pipeline_defaults(configs_root)

    entity_files = _find_entity_files(Path("configs/entities"))
    composite_files = _find_composite_files(Path("configs/composites"))

    errors: list[str] = []
    warnings: list[str] = []

    for config_path in entity_files:
        _process_entity_config(
            config_path,
            verbose=args.verbose,
            pipeline_schema=pipeline_schema,
            base_pipeline_defaults=base_pipeline_defaults,
            skip_runtime_normalized_check=args.skip_runtime_normalized_check,
            errors=errors,
            warnings=warnings,
        )

    for config_path in composite_files:
        _process_composite_config(
            config_path,
            verbose=args.verbose,
            composite_schema=composite_schema,
            errors=errors,
        )

    if errors:
        sys.stderr.write("\nERRORS:\n")
        for err in errors:
            sys.stderr.write(f"  {err}\n")

    if warnings:
        sys.stdout.write("\nWARNINGS:\n")
        for warn in warnings:
            sys.stdout.write(f"  {warn}\n")

    total = len(entity_files) + len(composite_files)
    if not errors and not warnings:
        sys.stdout.write(f"OK: all {total} configs validated\n")
        return 0

    if errors:
        return 1

    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
