"""Immutable workflow run-options configuration."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, cast

from bioetl.domain.types import JsonDict
from bioetl.domain.workflow._run_options_support import (
    prefer_override,
    prefer_stricter_persistence_profile,
    serialize_workflow_run_option_value,
)


@dataclass(frozen=True, slots=True)
class WorkflowRunOptionsConfig:
    """Partial run-options contract allowed in workflow YAML."""

    run_type: str | None = None
    resume: bool | None = None
    start_offset: int | None = None
    limit: int | None = None
    dry_run: bool | None = None
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    filter_ids: tuple[str, ...] | None = None
    multi_filter_ids: dict[str, tuple[str, ...]] | None = None
    fallback_column: str | None = None
    fallback_mapping: dict[str, str] | None = None
    vacuum_after_run: bool | None = None
    vacuum_retention_days: int | None = None
    log_level: str | None = None
    ignore_yaml_filter: bool | None = None
    skip_gold: bool | None = None
    execution_context: str | None = None
    use_cached_bronze: bool | None = None
    cached_bronze_path: str | None = None
    cached_bronze_date: str | None = None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    resume_run_id: str | None = None
    resume_manifest_id: str | None = None
    exact_replay: bool | None = None
    required_persistence_profile: str | None = None
    enable_tracing: bool | None = None
    debug_export_enabled: bool | None = None
    debug_export_formats: tuple[str, ...] | None = None
    debug_export_dir: str | None = None
    workflow_id: str | None = None
    no_control_plane_archive: bool | None = None

    def __post_init__(self) -> None:
        if self.multi_filter_ids is not None:
            object.__setattr__(
                self,
                "multi_filter_ids",
                {key: tuple(value) for key, value in self.multi_filter_ids.items()},
            )
        if self.fallback_mapping is not None:
            object.__setattr__(
                self,
                "fallback_mapping",
                dict(self.fallback_mapping),
            )

    def merged_with(
        self, override: WorkflowRunOptionsConfig
    ) -> WorkflowRunOptionsConfig:
        """Return a merged config where non-null override values win."""
        values: dict[str, object] = {
            field.name: prefer_override(
                getattr(self, field.name), getattr(override, field.name)
            )
            for field in fields(self)
        }
        values["required_persistence_profile"] = prefer_stricter_persistence_profile(
            self.required_persistence_profile,
            override.required_persistence_profile,
        )
        # Dynamic per-field merge uses dataclass field names.
        return WorkflowRunOptionsConfig(**cast("Any", values))

    def to_mapping(self) -> JsonDict:
        """Return non-null options as a plain mapping."""
        result: JsonDict = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            result[field.name] = serialize_workflow_run_option_value(field.name, value)
        return result
