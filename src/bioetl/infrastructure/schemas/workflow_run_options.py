"""Strict workflow run-option overrides and their immutable domain projection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.workflow.config import WorkflowRunOptionsConfig


class WorkflowRunOptionsSchema(BaseModel):
    """Strict partial schema for run-option overrides in workflow YAML."""

    model_config = ConfigDict(extra="forbid")

    run_type: str | None = None
    resume: bool | None = None
    start_offset: int | None = None
    limit: int | None = None
    reconciliation_mode: Literal["complete-reference", "selected-snapshot"] | None = (
        None
    )
    dry_run: bool | None = None
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    filter_ids: list[str] | None = None
    multi_filter_ids: dict[str, list[str]] | None = None
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
    required_persistence_profile: (
        Literal["degraded_observable", "replay_ready", "forensic_grade"] | None
    ) = None
    enable_tracing: bool | None = None
    debug_export_enabled: bool | None = None
    debug_export_formats: list[str] | None = None
    debug_export_dir: str | None = None
    workflow_id: str | None = None
    no_control_plane_archive: bool | None = None

    def to_domain(self) -> WorkflowRunOptionsConfig:
        """Convert validated overrides into immutable domain config."""
        multi_filter_ids = self.multi_filter_ids
        return WorkflowRunOptionsConfig(
            run_type=self.run_type,
            resume=self.resume,
            start_offset=self.start_offset,
            limit=self.limit,
            reconciliation_mode=self.reconciliation_mode,
            dry_run=self.dry_run,
            input_csv=self.input_csv,
            filter_column=self.filter_column,
            filter_field=self.filter_field,
            filter_ids=tuple(self.filter_ids) if self.filter_ids is not None else None,
            multi_filter_ids=(
                {key: tuple(values) for key, values in multi_filter_ids.items()}
                if multi_filter_ids is not None
                else None
            ),
            fallback_column=self.fallback_column,
            fallback_mapping=(
                dict(self.fallback_mapping)
                if self.fallback_mapping is not None
                else None
            ),
            vacuum_after_run=self.vacuum_after_run,
            vacuum_retention_days=self.vacuum_retention_days,
            log_level=self.log_level,
            ignore_yaml_filter=self.ignore_yaml_filter,
            skip_gold=self.skip_gold,
            execution_context=self.execution_context,
            use_cached_bronze=self.use_cached_bronze,
            cached_bronze_path=self.cached_bronze_path,
            cached_bronze_date=self.cached_bronze_date,
            replay_of_run_id=self.replay_of_run_id,
            replay_of_manifest_id=self.replay_of_manifest_id,
            resume_run_id=self.resume_run_id,
            resume_manifest_id=self.resume_manifest_id,
            exact_replay=self.exact_replay,
            required_persistence_profile=self.required_persistence_profile,
            enable_tracing=self.enable_tracing,
            debug_export_enabled=self.debug_export_enabled,
            debug_export_formats=(
                tuple(self.debug_export_formats)
                if self.debug_export_formats is not None
                else None
            ),
            debug_export_dir=self.debug_export_dir,
            workflow_id=self.workflow_id,
            no_control_plane_archive=self.no_control_plane_archive,
        )


class WorkflowDefaultsSchema(BaseModel):
    """Root defaults applied to workflow steps."""

    model_config = ConfigDict(extra="forbid")

    run_options: WorkflowRunOptionsSchema = Field(
        default_factory=WorkflowRunOptionsSchema
    )

    def to_domain(self) -> WorkflowRunOptionsConfig:
        """Convert workflow defaults to immutable domain config."""
        return self.run_options.to_domain()
