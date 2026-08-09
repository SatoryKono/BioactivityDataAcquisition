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
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, cast

import yaml

try:
    import jsonschema
except ImportError:
    sys.stderr.write("ERROR: jsonschema not installed. Run: pip install jsonschema\n")
    sys.exit(2)

from bioetl.domain.workflow import WorkflowStepConfig
from bioetl.infrastructure.config.composite_config_api import load_composite_config
from bioetl.infrastructure.config.config_root import (
    get_default_repo_root,
    resolve_configs_root,
)
from bioetl.infrastructure.config.source_config_loader import (
    normalize_source_config_payload,
    validate_source_config_payload,
)
from bioetl.infrastructure.config.workflow_config_api import load_workflow_config

YAML_GLOB = "*.yaml"


def _canonical_script() -> Path:
    """Return the canonical validate-configs implementation path."""
    return Path(__file__).resolve()


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load JSON Schema from file."""
    if not schema_path.exists():
        sys.stderr.write(f"ERROR: Schema file not found: {schema_path}\n")
        sys.exit(2)
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _find_entity_files(entities_dir: Path) -> list[Path]:
    return [
        p
        for p in sorted(entities_dir.rglob(YAML_GLOB))
        if not p.name.startswith("_")
    ]


def _find_composite_files(composites_dir: Path) -> list[Path]:
    return [
        p for p in sorted(composites_dir.glob(YAML_GLOB)) if not p.name.startswith("_")
    ]


def _find_provider_files(providers_dir: Path) -> list[Path]:
    return [
        p for p in sorted(providers_dir.glob(YAML_GLOB)) if not p.name.startswith("_")
    ]


def _find_workflow_files(workflows_dir: Path) -> list[Path]:
    return [
        p for p in sorted(workflows_dir.glob(YAML_GLOB)) if not p.name.startswith("_")
    ]


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


def _validate_legacy_pipeline_dir_absent(configs_root: Path) -> list[str]:
    """Return a validator error if the retired configs/pipelines tree exists."""
    legacy_dir = configs_root / "pipelines"
    if not legacy_dir.exists():
        return []
    return [
        "Legacy pipeline config directory must remain absent: "
        f"{legacy_dir}. Runtime defaults belong in configs/base/pipeline.yaml "
        "and per-pipeline payloads belong in configs/entities/{provider}/{entity}.yaml."
    ]


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
        if (
            expected_suffix
            and isinstance(layer_path, str)
            and layer_path
            and not layer_path.endswith(expected_suffix)
        ):
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


def _pipeline_name_from_provider_entity(provider: str, entity: str) -> str:
    return f"{provider}_{entity}"


def _known_entity_surfaces(entity_files: Iterable[Path]) -> dict[str, set[str]]:
    known: dict[str, set[str]] = {}
    for path in entity_files:
        provider = path.parent.name
        entity = path.stem
        known.setdefault(provider, set()).add(entity)
    return known


def _known_pipeline_names(entity_files: Iterable[Path]) -> set[str]:
    return {
        _pipeline_name_from_provider_entity(path.parent.name, path.stem)
        for path in entity_files
    }


def _validate_contract_primary_keys(
    entity_payload: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    pipeline = entity_payload.get("pipeline")
    contracts = entity_payload.get("contracts")
    if not isinstance(pipeline, dict) or not isinstance(contracts, dict):
        return errors

    business_primary_keys = pipeline.get("business_primary_keys")
    contract_primary_keys = contracts.get("primary_key")
    if not isinstance(business_primary_keys, list) or not isinstance(
        contract_primary_keys, list
    ):
        return errors

    normalized_pipeline_keys = [str(item).strip() for item in business_primary_keys]
    normalized_contract_keys = [str(item).strip() for item in contract_primary_keys]
    if normalized_pipeline_keys != normalized_contract_keys:
        errors.append(
            "contracts.primary_key must match pipeline.business_primary_keys "
            f"(contracts={normalized_contract_keys}, "
            f"pipeline={normalized_pipeline_keys})"
        )
    return errors


def _validate_entity_path_consistency(
    config_path: Path, payload: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    path_provider = config_path.parent.name
    path_entity = config_path.stem

    payload_provider = payload.get("provider")
    payload_entity = payload.get("entity")
    if payload_provider and payload_provider != path_provider:
        errors.append(
            f"path provider mismatch: path declares '{path_provider}' vs payload '{payload_provider}'"
        )
    if payload_entity and payload_entity != path_entity:
        errors.append(
            f"path entity mismatch: path declares '{path_entity}' vs payload '{payload_entity}'"
        )
    return errors


def _validate_entity_cross_file_references(
    config_path: Path,
    payload: dict[str, Any],
    *,
    known_provider_names: set[str],
) -> list[str]:
    errors = _validate_entity_path_consistency(config_path, payload)
    path_provider = config_path.parent.name
    path_entity = config_path.stem

    if path_provider not in known_provider_names:
        errors.append(
            f"missing provider runtime config: configs/providers/{path_provider}.yaml"
        )

    pipeline = payload.get("pipeline")
    if isinstance(pipeline, dict):
        expected_pipeline_name = _pipeline_name_from_provider_entity(
            path_provider, path_entity
        )
        pipeline_name = pipeline.get("pipeline_name")
        if pipeline_name and pipeline_name != expected_pipeline_name:
            errors.append(
                "pipeline_name mismatch: expected "
                f"'{expected_pipeline_name}' from config path, got '{pipeline_name}'"
            )

    errors.extend(_validate_contract_primary_keys(payload))
    return errors


def _validate_provider_entity_set(
    *,
    provider_name: str,
    declared_entities: object,
    known_entities: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(declared_entities, list) or not declared_entities:
        return ["entities must be a non-empty list"]
    normalized_declared_entities = {str(item).strip() for item in declared_entities}
    if "" in normalized_declared_entities:
        errors.append("entities contains an empty entity name")
    actual_entities = known_entities.get(provider_name, set())
    missing_entity_configs = sorted(normalized_declared_entities - actual_entities)
    unexpected_entity_configs = sorted(actual_entities - normalized_declared_entities)
    if missing_entity_configs:
        errors.append(
            "entities references missing entity configs: "
            + ", ".join(
                f"configs/entities/{provider_name}/{entity}.yaml"
                for entity in missing_entity_configs
            )
        )
    if unexpected_entity_configs:
        errors.append(
            "provider config is missing declared entities present under configs/entities: "
            + ", ".join(unexpected_entity_configs)
        )
    return errors


def _validate_entity_notes(
    entity_notes: object, *, declared_entities: set[str]
) -> list[str]:
    if entity_notes is None:
        return []
    if not isinstance(entity_notes, dict):
        return ["entity_notes must be a mapping when present"]
    note_keys = {str(key).strip() for key in entity_notes}
    extra_notes = sorted(note_keys - declared_entities)
    if not extra_notes:
        return []
    return ["entity_notes contains undeclared entities: " + ", ".join(extra_notes)]


def _validate_provider_cross_file_references(
    config_path: Path,
    payload: dict[str, Any],
    *,
    known_entities: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []
    provider_name = config_path.stem

    top_level_provider = payload.get("provider")
    if top_level_provider != provider_name:
        errors.append(
            f"provider mismatch: filename '{provider_name}' vs top-level '{top_level_provider}'"
        )

    normalized_payload: dict[str, Any] = {"source": payload.get("source", {})}
    for key in ("entities", "entity_notes"):
        if key in payload:
            normalized_payload[key] = payload[key]

    try:
        validated = validate_source_config_payload(
            normalize_source_config_payload(normalized_payload)
        )
    except Exception as exc:
        errors.append(f"provider runtime validation failed: {exc}")
        return errors

    if validated.provider and validated.provider != provider_name:
        errors.append(
            "source.provider_config.provider mismatch: expected "
            f"'{provider_name}', got '{validated.provider}'"
        )

    entity_errors = _validate_provider_entity_set(
        provider_name=provider_name,
        declared_entities=payload.get("entities"),
        known_entities=known_entities,
    )
    errors.extend(entity_errors)
    if any(err.startswith("entities must") for err in entity_errors):
        return errors
    declared = {
        str(item).strip()
        for item in (payload.get("entities") or [])
        if str(item).strip()
    }
    errors.extend(
        _validate_entity_notes(payload.get("entity_notes"), declared_entities=declared)
    )
    return errors


def _validate_composite_cross_file_references(
    composite_name: str,
    *,
    config_dir: Path,
    known_pipeline_names: set[str],
) -> list[str]:
    errors: list[str] = []
    try:
        config = load_composite_config(composite_name, config_dir=config_dir)
    except Exception as exc:
        return [f"composite runtime validation failed: {exc}"]

    expected_name = f"composite_{composite_name}"
    if config.name != expected_name:
        errors.append(
            f"composite.name mismatch: expected '{expected_name}', got '{config.name}'"
        )

    referenced_pipelines = [config.seed.pipeline]
    referenced_pipelines.extend(
        dependency.pipeline for dependency in config.dependencies
    )
    referenced_pipelines.extend(enricher.pipeline for enricher in config.enrichers)
    missing = sorted(
        pipeline_name
        for pipeline_name in referenced_pipelines
        if pipeline_name not in known_pipeline_names
    )
    if missing:
        errors.append("composite references unknown pipelines: " + ", ".join(missing))
    return errors


def _validate_workflow_cross_file_references(
    workflow_name: str,
    *,
    config_dir: Path,
    known_pipeline_names: set[str],
) -> list[str]:
    errors: list[str] = []
    try:
        config = load_workflow_config(workflow_name, config_dir=config_dir)
    except Exception as exc:
        return [f"workflow runtime validation failed: {exc}"]

    if config.name != workflow_name:
        errors.append(
            f"workflow.name mismatch: expected '{workflow_name}', got '{config.name}'"
        )

    missing_pipelines = sorted(
        step.pipeline_name
        for step in config.steps
        if isinstance(step, WorkflowStepConfig)
        and step.pipeline_name not in known_pipeline_names
    )
    if missing_pipelines:
        errors.append(
            "workflow references unknown pipeline steps: "
            + ", ".join(missing_pipelines)
        )
    return errors


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


def _process_provider_config(
    config_path: Path,
    *,
    verbose: bool,
    known_entities: dict[str, set[str]],
    errors: list[str],
) -> None:
    """Validate one provider runtime config and append findings."""
    if verbose:
        sys.stdout.write(f"Checking provider: {config_path}\n")
    try:
        payload = _load_yaml_payload(config_path)
    except yaml.YAMLError as exc:
        errors.append(f"{config_path}: YAML parse error: {exc}")
        return
    if payload is None:
        errors.append(f"{config_path}: provider config must be a YAML mapping")
        return
    _append_prefixed(
        errors,
        config_path,
        _validate_provider_cross_file_references(
            config_path,
            payload,
            known_entities=known_entities,
        ),
    )


def _process_composite_config(
    config_path: Path,
    *,
    verbose: bool,
    composite_schema: dict[str, Any],
    known_pipeline_names: set[str],
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
        return
    _append_prefixed(
        errors,
        config_path,
        _validate_composite_cross_file_references(
            config_path.stem,
            config_dir=config_path.parent,
            known_pipeline_names=known_pipeline_names,
        ),
    )


def _process_workflow_config(
    config_path: Path,
    *,
    verbose: bool,
    known_pipeline_names: set[str],
    errors: list[str],
) -> None:
    """Validate one workflow runtime config and append findings."""
    if verbose:
        sys.stdout.write(f"Checking workflow: {config_path}\n")
    try:
        payload = _load_yaml_payload(config_path)
    except yaml.YAMLError as exc:
        errors.append(f"{config_path}: YAML parse error: {exc}")
        return
    if payload is None:
        errors.append(f"{config_path}: workflow config must be a YAML mapping")
        return
    _append_prefixed(
        errors,
        config_path,
        _validate_workflow_cross_file_references(
            config_path.stem,
            config_dir=config_path.parent,
            known_pipeline_names=known_pipeline_names,
        ),
    )


def _config_validation_depth_summary(configs_root: Path) -> dict[str, int]:
    """Return family counts by declared config validation depth."""
    inventory_path = configs_root / "quality" / "config_validation_surface.yaml"
    if not inventory_path.exists():
        return {}

    payload = yaml.safe_load(inventory_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {}

    families = payload.get("families", [])
    if not isinstance(families, list):
        return {}

    summary: dict[str, int] = {}
    for family in families:
        if not isinstance(family, dict):
            continue
        depth = family.get("validation_depth", "missing")
        depth_name = str(depth).strip() or "missing"
        summary[depth_name] = summary.get(depth_name, 0) + 1
    return dict(sorted(summary.items()))


def _emit_validation_depth_summary(configs_root: Path) -> None:
    """Print config-family validation depth coverage alongside config checks."""
    summary = _config_validation_depth_summary(configs_root)
    if not summary:
        sys.stdout.write("Config validation surface: no family depth inventory found\n")
        return

    rendered = ", ".join(f"{depth}={count}" for depth, count in summary.items())
    sys.stdout.write(f"Config validation surface family depths: {rendered}\n")


def _validate_registry_manifest_surface(configs_root: Path) -> list[str]:
    """Validate the canonical runtime registry manifest against tracked configs."""
    from bioetl.composition.factories.pipeline.config_types import (
        PipelineFactoryConfig,
    )
    from bioetl.composition.factories.pipeline.registry_validation import (
        validate_registry_manifest,
    )

    resolved_configs_root = resolve_configs_root(configs_root)
    if (
        resolved_configs_root.resolve()
        == (get_default_repo_root() / "configs").resolve()
    ):
        from bioetl.composition.factories.pipeline.registry_manifest import (
            PIPELINE_CONFIGS,
        )

        pipeline_configs = PIPELINE_CONFIGS
    else:
        pipeline_configs = _build_local_registry_manifest(
            resolved_configs_root,
            pipeline_config_cls=PipelineFactoryConfig,
        )

    return validate_registry_manifest(
        configs_root=resolved_configs_root,
        pipeline_configs=cast(Iterable[Any], pipeline_configs),
    )


def _build_local_registry_manifest(
    configs_root: Path,
    *,
    pipeline_config_cls: type[Any],
) -> tuple[Any, ...]:
    """Build isolated registry entries for non-canonical config-tree validation."""
    entities_dir = configs_root / "entities"
    entity_files = _find_entity_files(entities_dir) if entities_dir.exists() else []
    entries: list[Any] = []
    for entity_path in entity_files:
        payload: dict[str, Any] = {}
        try:
            loaded_payload = _load_yaml_payload(entity_path)
        except yaml.YAMLError:
            loaded_payload = None
        if loaded_payload is not None:
            payload = loaded_payload

        pipeline_payload = payload.get("pipeline")
        pipeline = pipeline_payload if isinstance(pipeline_payload, dict) else {}
        provider = str(
            payload.get("provider")
            or pipeline.get("provider")
            or entity_path.parent.name
        )
        entity = str(
            payload.get("entity") or pipeline.get("entity_type") or entity_path.stem
        )
        pipeline_name = str(
            pipeline.get("pipeline_name")
            or _pipeline_name_from_provider_entity(provider, entity)
        )
        entries.append(
            pipeline_config_cls(
                pipeline_name=pipeline_name,
                provider=provider,
                entity_type=entity,
                transformer_class="synthetic_config_tree_validation",
                silver_schema=None,
                gold_schema=object(),
                pandera_silver_schema=object(),
            )
        )
    return tuple(entries)


def validate_config_tree(
    configs_root: Path,
    *,
    verbose: bool = False,
    skip_runtime_normalized_check: bool = False,
    registry_validator: Callable[[Path], list[str]] | None = None,
) -> tuple[list[str], list[str], int]:
    """Validate the canonical config tree and return errors, warnings, and count."""
    schema_dir = configs_root / "_schema"
    pipeline_schema = load_schema(schema_dir / "pipeline.json")
    composite_schema = load_schema(schema_dir / "composite.json")
    base_pipeline_defaults = _load_base_pipeline_defaults(configs_root)

    entities_dir = configs_root / "entities"
    composites_dir = configs_root / "composites"
    providers_dir = configs_root / "providers"
    workflows_dir = configs_root / "workflows"

    entity_files = _find_entity_files(entities_dir) if entities_dir.exists() else []
    composite_files = (
        _find_composite_files(composites_dir) if composites_dir.exists() else []
    )
    provider_files = (
        _find_provider_files(providers_dir) if providers_dir.exists() else []
    )
    workflow_files = (
        _find_workflow_files(workflows_dir) if workflows_dir.exists() else []
    )

    known_entities = _known_entity_surfaces(entity_files)
    known_provider_names = set(known_entities)
    known_pipeline_names = _known_pipeline_names(entity_files)

    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(_validate_legacy_pipeline_dir_absent(configs_root))

    for config_path in entity_files:
        _process_entity_config(
            config_path,
            verbose=verbose,
            pipeline_schema=pipeline_schema,
            base_pipeline_defaults=base_pipeline_defaults,
            skip_runtime_normalized_check=skip_runtime_normalized_check,
            errors=errors,
            warnings=warnings,
        )
        try:
            payload = _load_yaml_payload(config_path)
        except yaml.YAMLError:
            payload = None
        if payload is not None:
            _append_prefixed(
                errors,
                config_path,
                _validate_entity_cross_file_references(
                    config_path,
                    payload,
                    known_provider_names=known_provider_names,
                ),
            )

    for config_path in provider_files:
        _process_provider_config(
            config_path,
            verbose=verbose,
            known_entities=known_entities,
            errors=errors,
        )

    for config_path in composite_files:
        _process_composite_config(
            config_path,
            verbose=verbose,
            composite_schema=composite_schema,
            known_pipeline_names=known_pipeline_names,
            errors=errors,
        )

    for config_path in workflow_files:
        _process_workflow_config(
            config_path,
            verbose=verbose,
            known_pipeline_names=known_pipeline_names,
            errors=errors,
        )

    effective_registry_validator = (
        _validate_registry_manifest_surface
        if registry_validator is None
        else registry_validator
    )
    errors.extend(effective_registry_validator(configs_root))

    total = (
        len(entity_files)
        + len(provider_files)
        + len(composite_files)
        + len(workflow_files)
    )
    return errors, warnings, total


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate unified pipeline configs. The tracked YAML config tree is "
            "validated together with the composition-owned pipeline registry "
            "manifest so runtime bindings and config surfaces cannot drift."
        )
    )
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
    parser.add_argument(
        "--configs-root",
        type=Path,
        default=None,
        help=(
            "Explicit configs root. Defaults to the canonical repo-root "
            "configs/ directory used by registry/config validation."
        ),
    )
    args = parser.parse_args()

    configs_root = resolve_configs_root(args.configs_root)
    errors, warnings, total = validate_config_tree(
        configs_root,
        verbose=args.verbose,
        skip_runtime_normalized_check=args.skip_runtime_normalized_check,
    )

    _emit_validation_depth_summary(configs_root)

    if errors:
        sys.stderr.write("\nERRORS:\n")
        for err in errors:
            sys.stderr.write(f"  {err}\n")

    if warnings:
        sys.stdout.write("\nWARNINGS:\n")
        for warn in warnings:
            sys.stdout.write(f"  {warn}\n")

    if not errors and not warnings:
        sys.stdout.write(f"OK: all {total} configs validated\n")
        return 0

    if errors:
        return 1

    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
