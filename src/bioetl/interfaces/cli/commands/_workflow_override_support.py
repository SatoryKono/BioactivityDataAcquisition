"""Workflow CLI run-option override helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from bioetl.domain.workflow import (
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStep,
    WorkflowStepConfig,
)

__all__ = [
    "WorkflowRunOptionsConfig",
    "apply_cli_override_config",
    "apply_cli_overrides",
    "build_workflow_run_options_override",
    "build_workflow_run_options_override_from_mapping",
]

_WORKFLOW_RUN_OPTIONS_OVERRIDE_FIELDS = (
    "dry_run",
    "run_type",
    "start_offset",
    "limit",
    "input_csv",
    "filter_column",
    "filter_field",
    "vacuum_after_run",
    "vacuum_retention_days",
    "log_level",
    "ignore_yaml_filter",
    "skip_gold",
    "execution_context",
    "use_cached_bronze",
    "cached_bronze_path",
    "cached_bronze_date",
    "exact_replay",
    "required_persistence_profile",
    "replay_of_run_id",
    "replay_of_manifest_id",
    "enable_tracing",
    "debug_export_enabled",
    "debug_export_formats",
    "debug_export_dir",
)


def _build_override_values(values: Mapping[str, object]) -> dict[str, object]:
    return {
        field_name: values.get(field_name)
        for field_name in _WORKFLOW_RUN_OPTIONS_OVERRIDE_FIELDS
    }


def _optional_str(values: Mapping[str, object], key: str) -> str | None:
    value = values.get(key)
    return value if isinstance(value, str) else None


def _optional_int(values: Mapping[str, object], key: str) -> int | None:
    value = values.get(key)
    return value if isinstance(value, int) else None


def _optional_bool(values: Mapping[str, object], key: str) -> bool | None:
    value = values.get(key)
    return value if isinstance(value, bool) else None


def _optional_str_tuple(values: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, tuple):
        return ()
    return tuple(str(item) for item in value)


def build_workflow_run_options_override(
    *,
    dry_run: bool,
    run_type: str | None,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    log_level: str | None,
    ignore_yaml_filter: bool | None,
    skip_gold: bool | None,
    execution_context: str | None,
    use_cached_bronze: bool | None,
    cached_bronze_path: str | None,
    cached_bronze_date: str | None,
    exact_replay: bool | None,
    required_persistence_profile: str | None,
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    enable_tracing: bool | None,
    debug_export_enabled: bool | None,
    debug_export_formats: tuple[str, ...],
    debug_export_dir: str | None,
) -> WorkflowRunOptionsConfig:
    """Build one workflow override config from CLI flags."""
    return WorkflowRunOptionsConfig(
        dry_run=True if dry_run else None,
        run_type=run_type,
        start_offset=start_offset,
        limit=limit,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        vacuum_after_run=vacuum_after_run,
        vacuum_retention_days=vacuum_retention_days,
        log_level=log_level,
        ignore_yaml_filter=ignore_yaml_filter,
        skip_gold=skip_gold,
        execution_context=execution_context,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_date=cached_bronze_date,
        exact_replay=exact_replay,
        required_persistence_profile=required_persistence_profile,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        enable_tracing=enable_tracing,
        debug_export_enabled=debug_export_enabled,
        debug_export_formats=debug_export_formats or None,
        debug_export_dir=debug_export_dir,
    )


def build_workflow_run_options_override_from_mapping(
    values: Mapping[str, object],
) -> WorkflowRunOptionsConfig:
    """Build one workflow override config from a CLI/local variable mapping."""
    override_values = _build_override_values(values)
    return build_workflow_run_options_override(
        dry_run=bool(override_values["dry_run"]),
        run_type=_optional_str(override_values, "run_type"),
        start_offset=_optional_int(override_values, "start_offset"),
        limit=_optional_int(override_values, "limit"),
        input_csv=_optional_str(override_values, "input_csv"),
        filter_column=_optional_str(override_values, "filter_column"),
        filter_field=_optional_str(override_values, "filter_field"),
        vacuum_after_run=_optional_bool(override_values, "vacuum_after_run"),
        vacuum_retention_days=_optional_int(
            override_values,
            "vacuum_retention_days",
        ),
        log_level=_optional_str(override_values, "log_level"),
        ignore_yaml_filter=_optional_bool(override_values, "ignore_yaml_filter"),
        skip_gold=_optional_bool(override_values, "skip_gold"),
        execution_context=_optional_str(override_values, "execution_context"),
        use_cached_bronze=_optional_bool(override_values, "use_cached_bronze"),
        cached_bronze_path=_optional_str(override_values, "cached_bronze_path"),
        cached_bronze_date=_optional_str(override_values, "cached_bronze_date"),
        exact_replay=_optional_bool(override_values, "exact_replay"),
        required_persistence_profile=_optional_str(
            override_values,
            "required_persistence_profile",
        ),
        replay_of_run_id=_optional_str(override_values, "replay_of_run_id"),
        replay_of_manifest_id=_optional_str(
            override_values,
            "replay_of_manifest_id",
        ),
        enable_tracing=_optional_bool(override_values, "enable_tracing"),
        debug_export_enabled=_optional_bool(
            override_values,
            "debug_export_enabled",
        ),
        debug_export_formats=_optional_str_tuple(
            override_values,
            "debug_export_formats",
        ),
        debug_export_dir=_optional_str(override_values, "debug_export_dir"),
    )


def apply_cli_override_config(
    config: WorkflowConfig,
    override: WorkflowRunOptionsConfig,
) -> WorkflowConfig:
    """Apply one prebuilt workflow override config to defaults and steps."""
    if not override.to_mapping():
        return config

    updated_steps: list[WorkflowStep] = []
    for step in config.steps:
        if isinstance(step, WorkflowStepConfig):
            updated_steps.append(
                replace(
                    step,
                    run_options=step.run_options.merged_with(override),
                )
            )
            continue
        updated_steps.append(step)

    return replace(
        config,
        defaults=config.defaults.merged_with(override),
        steps=tuple(updated_steps),
    )


def apply_cli_overrides(
    config: WorkflowConfig,
    *,
    dry_run: bool,
    run_type: str | None,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    log_level: str | None,
    ignore_yaml_filter: bool | None,
    skip_gold: bool | None,
    execution_context: str | None,
    use_cached_bronze: bool | None,
    cached_bronze_path: str | None,
    cached_bronze_date: str | None,
    exact_replay: bool | None,
    required_persistence_profile: str | None,
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    enable_tracing: bool | None,
    debug_export_enabled: bool | None,
    debug_export_formats: tuple[str, ...],
    debug_export_dir: str | None,
) -> WorkflowConfig:
    """Apply CLI overrides to workflow defaults and pipeline steps."""
    override = build_workflow_run_options_override_from_mapping(locals())
    return apply_cli_override_config(config, override)
