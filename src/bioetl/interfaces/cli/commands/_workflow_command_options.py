"""Packed Click option values for ``workflow run`` (python:S107)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from bioetl.interfaces.cli.commands._typed_option_values import (
    option_or_default,
    optional_option,
    require_option,
    string_tuple_option,
)
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
        raw: Mapping[str, object],
    ) -> WorkflowCommandOptions:
        """Build options from Click-injected keyword arguments."""
        return cls(
            dry_run=require_option(raw, "dry_run", bool),
            only_steps=optional_option(raw, "only_steps", str),
            run_type=optional_option(raw, "run_type", str),
            start_offset=optional_option(raw, "start_offset", int),
            limit=optional_option(raw, "limit", int),
            input_csv=optional_option(raw, "input_csv", str),
            filter_column=optional_option(raw, "filter_column", str),
            filter_field=optional_option(raw, "filter_field", str),
            vacuum_after_run=optional_option(raw, "vacuum_after_run", bool),
            vacuum_retention_days=optional_option(raw, "vacuum_retention_days", int),
            log_level=optional_option(raw, "log_level", str),
            ignore_yaml_filter=optional_option(raw, "ignore_yaml_filter", bool),
            skip_gold=optional_option(raw, "skip_gold", bool),
            execution_context=optional_option(raw, "execution_context", str),
            use_cached_bronze=optional_option(raw, "use_cached_bronze", bool),
            cached_bronze_path=optional_option(raw, "cached_bronze_path", str),
            cached_bronze_date=optional_option(raw, "cached_bronze_date", str),
            exact_replay=optional_option(raw, "exact_replay", bool),
            required_persistence_profile=optional_option(
                raw, "required_persistence_profile", str
            ),
            replay_of_run_id=optional_option(raw, "replay_of_run_id", str),
            replay_of_manifest_id=optional_option(raw, "replay_of_manifest_id", str),
            enable_tracing=optional_option(raw, "enable_tracing", bool),
            debug_export_enabled=optional_option(raw, "debug_export_enabled", bool),
            debug_export_formats=string_tuple_option(raw, "debug_export_formats"),
            debug_export_dir=optional_option(raw, "debug_export_dir", str),
            resume_last=option_or_default(raw, "resume_last", False, bool),
            resume_manifest_id=optional_option(raw, "resume_manifest_id", str),
            resume_run_id=optional_option(raw, "resume_run_id", UUID),
            force_steps=optional_option(raw, "force_steps", str),
            repair_steps=optional_option(raw, "repair_steps", str),
            incremental=option_or_default(raw, "incremental", False, bool),
            ensure_observability_backend=option_or_default(
                raw, "ensure_observability_backend", False, bool
            ),
            observability_backend_port=option_or_default(
                raw,
                "observability_backend_port",
                DEFAULT_HEALTH_SERVER_PORT,
                int,
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
