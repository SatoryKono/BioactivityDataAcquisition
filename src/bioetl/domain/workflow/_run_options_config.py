"""Immutable workflow run-options configuration."""

from __future__ import annotations

from dataclasses import dataclass, fields

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
        return WorkflowRunOptionsConfig(
            run_type=prefer_override(self.run_type, override.run_type),
            resume=prefer_override(self.resume, override.resume),
            start_offset=prefer_override(self.start_offset, override.start_offset),
            limit=prefer_override(self.limit, override.limit),
            dry_run=prefer_override(self.dry_run, override.dry_run),
            input_csv=prefer_override(self.input_csv, override.input_csv),
            filter_column=prefer_override(
                self.filter_column,
                override.filter_column,
            ),
            filter_field=prefer_override(self.filter_field, override.filter_field),
            filter_ids=prefer_override(self.filter_ids, override.filter_ids),
            multi_filter_ids=prefer_override(
                self.multi_filter_ids,
                override.multi_filter_ids,
            ),
            fallback_column=prefer_override(
                self.fallback_column,
                override.fallback_column,
            ),
            fallback_mapping=prefer_override(
                self.fallback_mapping,
                override.fallback_mapping,
            ),
            vacuum_after_run=prefer_override(
                self.vacuum_after_run,
                override.vacuum_after_run,
            ),
            vacuum_retention_days=prefer_override(
                self.vacuum_retention_days,
                override.vacuum_retention_days,
            ),
            log_level=prefer_override(self.log_level, override.log_level),
            ignore_yaml_filter=prefer_override(
                self.ignore_yaml_filter,
                override.ignore_yaml_filter,
            ),
            skip_gold=prefer_override(self.skip_gold, override.skip_gold),
            execution_context=prefer_override(
                self.execution_context,
                override.execution_context,
            ),
            use_cached_bronze=prefer_override(
                self.use_cached_bronze,
                override.use_cached_bronze,
            ),
            cached_bronze_path=prefer_override(
                self.cached_bronze_path,
                override.cached_bronze_path,
            ),
            cached_bronze_date=prefer_override(
                self.cached_bronze_date,
                override.cached_bronze_date,
            ),
            replay_of_run_id=prefer_override(
                self.replay_of_run_id,
                override.replay_of_run_id,
            ),
            replay_of_manifest_id=prefer_override(
                self.replay_of_manifest_id,
                override.replay_of_manifest_id,
            ),
            resume_run_id=prefer_override(
                self.resume_run_id,
                override.resume_run_id,
            ),
            resume_manifest_id=prefer_override(
                self.resume_manifest_id,
                override.resume_manifest_id,
            ),
            exact_replay=prefer_override(self.exact_replay, override.exact_replay),
            required_persistence_profile=prefer_stricter_persistence_profile(
                self.required_persistence_profile,
                override.required_persistence_profile,
            ),
            enable_tracing=prefer_override(
                self.enable_tracing,
                override.enable_tracing,
            ),
            debug_export_enabled=prefer_override(
                self.debug_export_enabled,
                override.debug_export_enabled,
            ),
            debug_export_formats=prefer_override(
                self.debug_export_formats,
                override.debug_export_formats,
            ),
            debug_export_dir=prefer_override(
                self.debug_export_dir,
                override.debug_export_dir,
            ),
            workflow_id=prefer_override(self.workflow_id, override.workflow_id),
        )

    def to_mapping(self) -> JsonDict:
        """Return non-null options as a plain mapping."""
        result: JsonDict = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            result[field.name] = serialize_workflow_run_option_value(field.name, value)
        return result
