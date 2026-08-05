"""Packed Click option values for ``workflow run`` (python:S107)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)

__all__ = [
    "WorkflowCommandOptions",
]


@dataclass(frozen=True, slots=True)
class WorkflowCommandOptions:
    """Packed Click option values for ``workflow run`` (python:S107)."""

    dry_run: bool
    only_steps: str | None
    run_type: str | None
    start_offset: int | None
    limit: int | None
    input_csv: str | None
    filter_column: str | None
    filter_field: str | None
    vacuum_after_run: bool | None
    vacuum_retention_days: int | None
    log_level: str | None
    ignore_yaml_filter: bool | None
    skip_gold: bool | None
    execution_context: str | None
    use_cached_bronze: bool | None
    cached_bronze_path: str | None
    cached_bronze_date: str | None
    exact_replay: bool | None
    required_persistence_profile: str | None
    replay_of_run_id: str | None
    replay_of_manifest_id: str | None
    enable_tracing: bool | None
    debug_export_enabled: bool | None
    debug_export_formats: tuple[str, ...]
    debug_export_dir: str | None
    resume_last: bool
    resume_manifest_id: str | None
    resume_run_id: UUID | None
    force_steps: str | None
    repair_steps: str | None
    incremental: bool
    ensure_observability_backend: bool
    observability_backend_port: int

    @classmethod
    def from_click_kwargs(
        cls,
        raw: dict[str, Any],  # Any: Click injects heterogeneous option values
    ) -> WorkflowCommandOptions:
        """Build options from Click-injected keyword arguments."""
        return cls(
            dry_run=bool(raw["dry_run"]),
            only_steps=cast(str | None, raw.get("only_steps")),
            run_type=cast(str | None, raw.get("run_type")),
            start_offset=cast(int | None, raw.get("start_offset")),
            limit=cast(int | None, raw.get("limit")),
            input_csv=cast(str | None, raw.get("input_csv")),
            filter_column=cast(str | None, raw.get("filter_column")),
            filter_field=cast(str | None, raw.get("filter_field")),
            vacuum_after_run=cast(bool | None, raw.get("vacuum_after_run")),
            vacuum_retention_days=cast(int | None, raw.get("vacuum_retention_days")),
            log_level=cast(str | None, raw.get("log_level")),
            ignore_yaml_filter=cast(bool | None, raw.get("ignore_yaml_filter")),
            skip_gold=cast(bool | None, raw.get("skip_gold")),
            execution_context=cast(str | None, raw.get("execution_context")),
            use_cached_bronze=cast(bool | None, raw.get("use_cached_bronze")),
            cached_bronze_path=cast(str | None, raw.get("cached_bronze_path")),
            cached_bronze_date=cast(str | None, raw.get("cached_bronze_date")),
            exact_replay=cast(bool | None, raw.get("exact_replay")),
            required_persistence_profile=cast(
                str | None, raw.get("required_persistence_profile")
            ),
            replay_of_run_id=cast(str | None, raw.get("replay_of_run_id")),
            replay_of_manifest_id=cast(str | None, raw.get("replay_of_manifest_id")),
            enable_tracing=cast(bool | None, raw.get("enable_tracing")),
            debug_export_enabled=cast(bool | None, raw.get("debug_export_enabled")),
            debug_export_formats=cast(
                tuple[str, ...], raw.get("debug_export_formats", ())
            ),
            debug_export_dir=cast(str | None, raw.get("debug_export_dir")),
            resume_last=bool(raw.get("resume_last", False)),
            resume_manifest_id=cast(str | None, raw.get("resume_manifest_id")),
            resume_run_id=cast(UUID | None, raw.get("resume_run_id")),
            force_steps=cast(str | None, raw.get("force_steps")),
            repair_steps=cast(str | None, raw.get("repair_steps")),
            incremental=bool(raw.get("incremental", False)),
            ensure_observability_backend=bool(
                raw.get("ensure_observability_backend", False)
            ),
            observability_backend_port=int(
                raw.get("observability_backend_port", DEFAULT_HEALTH_SERVER_PORT)
            ),
        )

    def as_override_mapping(self, *, name: str) -> dict[str, object]:
        """Expose option values for workflow override config builders."""
        return {
            "name": name,
            "dry_run": self.dry_run,
            "only_steps": self.only_steps,
            "run_type": self.run_type,
            "start_offset": self.start_offset,
            "limit": self.limit,
            "input_csv": self.input_csv,
            "filter_column": self.filter_column,
            "filter_field": self.filter_field,
            "vacuum_after_run": self.vacuum_after_run,
            "vacuum_retention_days": self.vacuum_retention_days,
            "log_level": self.log_level,
            "ignore_yaml_filter": self.ignore_yaml_filter,
            "skip_gold": self.skip_gold,
            "execution_context": self.execution_context,
            "use_cached_bronze": self.use_cached_bronze,
            "cached_bronze_path": self.cached_bronze_path,
            "cached_bronze_date": self.cached_bronze_date,
            "exact_replay": self.exact_replay,
            "required_persistence_profile": self.required_persistence_profile,
            "replay_of_run_id": self.replay_of_run_id,
            "replay_of_manifest_id": self.replay_of_manifest_id,
            "enable_tracing": self.enable_tracing,
            "debug_export_enabled": self.debug_export_enabled,
            "debug_export_formats": self.debug_export_formats,
            "debug_export_dir": self.debug_export_dir,
            "resume_last": self.resume_last,
            "resume_manifest_id": self.resume_manifest_id,
            "resume_run_id": self.resume_run_id,
            "force_steps": self.force_steps,
            "repair_steps": self.repair_steps,
            "incremental": self.incremental,
            "ensure_observability_backend": self.ensure_observability_backend,
            "observability_backend_port": self.observability_backend_port,
        }
