#!/usr/bin/env python3
"""Validate unified pipeline and composite configs against JSON schemas."""

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
    return [p for p in sorted(entities_dir.rglob("*.yaml")) if not p.name.startswith("_")]


def _find_composite_files(composites_dir: Path) -> list[Path]:
    return [p for p in sorted(composites_dir.glob("*.yaml")) if not p.name.startswith("_")]


def _validate_yaml_schema(
    payload: Any, schema: dict[str, Any]
) -> tuple[bool, str]:
    try:
        jsonschema.validate(payload, schema)
        return True, ""
    except jsonschema.ValidationError as exc:
        path = ".".join(str(part) for part in exc.path)
        suffix = f" at {path}" if path else ""
        return False, f"Schema validation: {exc.message}{suffix}"


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

    for layer in ("silver", "gold"):
        if layer not in sink:
            continue
        layer_cfg = sink.get(layer, {})
        if isinstance(layer_cfg, dict) and "sort_by" not in layer_cfg:
            warnings.append(f"sink.{layer}.sort_by missing (ADR-014 determinism)")

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate unified pipeline configs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (path hierarchy, sort_by)",
    )
    args = parser.parse_args()

    schema_dir = Path("configs/_schema")
    composite_schema = load_schema(schema_dir / "composite.json")

    entity_files = _find_entity_files(Path("configs/entities"))
    composite_files = _find_composite_files(Path("configs/composites"))

    errors: list[str] = []
    warnings: list[str] = []

    for config_path in entity_files:
        if args.verbose:
            sys.stdout.write(f"Checking entity: {config_path}\n")

        try:
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"{config_path}: YAML parse error: {exc}")
            continue

        if not isinstance(payload, dict):
            errors.append(f"{config_path}: entity config must be a YAML mapping")
            continue

        for err in _validate_entity_config_sections(payload):
            errors.append(f"{config_path}: {err}")

        for err in _validate_provider_entity_consistency(payload):
            errors.append(f"{config_path}: {err}")

        pipeline_payload = payload.get("pipeline")
        if not isinstance(pipeline_payload, dict):
            errors.append(f"{config_path}: missing or invalid 'pipeline' section")
            continue

        for err in _validate_pipeline_payload(pipeline_payload):
            errors.append(f"{config_path}: {err}")

        for warn in _validate_sink_paths_and_sort(pipeline_payload):
            warnings.append(f"{config_path}: {warn}")

    for config_path in composite_files:
        if args.verbose:
            sys.stdout.write(f"Checking composite: {config_path}\n")
        try:
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"{config_path}: YAML parse error: {exc}")
            continue

        valid, err_msg = _validate_yaml_schema(payload, composite_schema)
        if not valid:
            errors.append(f"{config_path}: {err_msg}")

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
