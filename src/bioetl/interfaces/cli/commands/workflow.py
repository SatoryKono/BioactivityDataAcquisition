"""Declarative workflow CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import click

from bioetl.interfaces.cli.commands import _workflow_command_runtime
from bioetl.interfaces.cli.commands._workflow_composition_seams import (
    get_workflow_execution_service,
    get_workflow_inspection_service,
    load_workflow_config,
)
from bioetl.interfaces.cli.commands._workflow_run_support import (
    _build_workflow_override_config,
    _load_and_apply_workflow_config,
    _validate_run_workflow_options,
)
from bioetl.interfaces.cli.commands._workflow_support import (
    build_status_payload,
    render_status_payload,
    select_workflow_steps,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration import (
    publish_metrics_safely,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ensure_observability_backend_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_argument,
    typed_click_group,
    typed_click_option,
    typed_group_command,
    typed_pass_obj,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "WorkflowCommandOptions",
    "ensure_observability_backend_started",
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "load_workflow_config",
    "workflow",
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
    def from_click_kwargs(cls, raw: dict[str, Any]) -> WorkflowCommandOptions:
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
            vacuum_retention_days=cast(
                int | None, raw.get("vacuum_retention_days")
            ),
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
            replay_of_manifest_id=cast(
                str | None, raw.get("replay_of_manifest_id")
            ),
            enable_tracing=cast(bool | None, raw.get("enable_tracing")),
            debug_export_enabled=cast(
                bool | None, raw.get("debug_export_enabled")
            ),
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
                raw.get("ensure_observability_backend", True)
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


@typed_click_group()
def workflow() -> None:
    """Run and inspect declarative workflows."""


@typed_group_command(workflow, "run")
@typed_click_argument("name")
@typed_click_option(
    "--dry-run",
    is_flag=True,
    help=(
        "Enable workflow dry-run. Pipeline steps run in dry-run mode and "
        "destructive transform steps switch to preview/no-op semantics."
    ),
)
@typed_click_option(
    "--only-steps",
    help="Comma-separated subset of step IDs to execute with required dependencies",
)
@typed_click_option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    help="Override workflow pipeline run_type for this execution",
)
@typed_click_option(
    "--start-offset",
    type=int,
    help="Override pipeline start_offset for workflow pipeline steps",
)
@typed_click_option(
    "--limit",
    type=int,
    help="Override pipeline record limit for workflow pipeline steps",
)
@typed_click_option(
    "--input-csv",
    type=click.Path(exists=True),
    help="Path to CSV file with filter IDs for workflow pipeline steps",
)
@typed_click_option(
    "--filter-column",
    type=str,
    help="Override CSV filter column for workflow pipeline steps",
)
@typed_click_option(
    "--filter-field",
    type=str,
    help="Override source filter field for workflow pipeline steps",
)
@typed_click_option(
    "--vacuum-after-run",
    is_flag=True,
    default=None,
    help="Override Delta VACUUM execution after successful workflow pipeline steps",
)
@typed_click_option(
    "--vacuum-retention-days",
    type=int,
    help="Override Delta VACUUM retention for workflow pipeline steps",
)
@typed_click_option(
    "--log-level",
    type=str,
    help="Override log level for workflow pipeline steps",
)
@typed_click_option(
    "--ignore-yaml-filter",
    is_flag=True,
    default=None,
    help="Ignore YAML filter defaults for workflow pipeline steps",
)
@typed_click_option(
    "--skip-gold",
    is_flag=True,
    default=None,
    help="Skip Gold writes for workflow pipeline steps",
)
@typed_click_option(
    "--execution-context",
    type=str,
    help="Override execution context for workflow pipeline steps",
)
@typed_click_option(
    "--use-cached-bronze/--no-cached-bronze",
    default=None,
    help="Override Bronze cache usage for workflow pipeline steps",
)
@typed_click_option(
    "--cached-bronze-path",
    type=click.Path(exists=True),
    help="Explicit Bronze cache path for workflow pipeline steps",
)
@typed_click_option(
    "--cached-bronze-date",
    type=str,
    help="Bronze cache date filter for workflow pipeline steps",
)
@typed_click_option(
    "--exact-replay/--no-exact-replay",
    "exact_replay",
    default=None,
    help="Override strict exact replay request for workflow pipeline steps",
)
@typed_click_option(
    "--required-persistence-profile",
    type=click.Choice(["degraded_observable", "replay_ready", "forensic_grade"]),
    default=None,
    help="Override required control-plane persistence profile for workflow steps",
)
@typed_click_option(
    "--replay-of-run-id",
    type=str,
    help="Explicit parent run_id for exact replay workflow pipeline steps",
)
@typed_click_option(
    "--replay-of-manifest-id",
    type=str,
    help="Explicit parent manifest_id for exact replay workflow pipeline steps",
)
@typed_click_option(
    "--tracing/--no-tracing",
    "enable_tracing",
    default=None,
    help="Override distributed tracing for workflow pipeline steps",
)
@typed_click_option(
    "--debug-export/--no-debug-export",
    "debug_export_enabled",
    default=None,
    help="Persist a per-run debug audit pack for workflow pipeline steps",
)
@typed_click_option(
    "--debug-export-format",
    "debug_export_formats",
    multiple=True,
    type=click.Choice(["csv", "xlsx"]),
    default=("csv", "xlsx"),
    help="Repeatable debug-export formats for workflow pipeline steps",
    show_default=True,
)
@typed_click_option(
    "--debug-export-dir",
    type=click.Path(),
    help="Override the debug-export root directory for workflow pipeline steps",
)
@typed_click_option(
    "--resume-last",
    is_flag=True,
    help="Resume the latest incomplete or failed execution for this workflow",
)
@typed_click_option(
    "--resume-manifest-id",
    type=str,
    help="Resume one specific workflow execution state selected by manifest_id",
)
@typed_click_option(
    "--resume-run-id",
    type=click.UUID,
    help="Resume one specific workflow execution state selected by workflow run_id",
)
@typed_click_option(
    "--force-steps",
    help="Comma-separated step IDs to force even when resume would normally skip them",
)
@typed_click_option(
    "--repair-steps",
    help="Comma-separated step IDs to explicitly repair before resume proceeds",
)
@typed_click_option(
    "--incremental",
    is_flag=True,
    default=False,
    help="Auto-increment start_offset from last successful execution. "
    "Cannot be used with resume selectors or --start-offset.",
)
@typed_click_option(
    "--ensure-observability-backend/--no-ensure-observability-backend",
    "ensure_observability_backend",
    default=True,
    help="Auto-start a detached Quarantine Explorer backend for Grafana ID/detail panels.",
    show_default=True,
)
@typed_click_option(
    "--observability-backend-port",
    type=int,
    default=DEFAULT_HEALTH_SERVER_PORT,
    help="Port for the detached Quarantine Explorer backend used by Grafana ID/detail panels.",
    show_default=True,
)
@typed_pass_obj
def run_workflow_command(
    registry: PipelineRegistry | None,
    name: str,
    **raw_options: object,
) -> None:
    """Execute one declarative workflow config sequentially.

    Click injects option values into ``raw_options``; they are packed into
    :class:`WorkflowCommandOptions` to stay under the Sonar S107 parameter budget.
    """
    options = WorkflowCommandOptions.from_click_kwargs(
        cast(dict[str, Any], raw_options)
    )
    _validate_run_workflow_options(
        incremental=options.incremental,
        resume_last=options.resume_last,
        resume_manifest_id=options.resume_manifest_id,
        resume_run_id=options.resume_run_id,
        start_offset=options.start_offset,
    )
    config = _load_and_apply_workflow_config(
        load_workflow_config_fn=load_workflow_config,
        name=name,
        only_steps=options.only_steps,
        override_config=_build_workflow_override_config(
            options.as_override_mapping(name=name)
        ),
    )
    execution_kwargs = _workflow_command_runtime.build_workflow_execution_kwargs(
        get_workflow_execution_service_fn=get_workflow_execution_service,
        ensure_metrics_server_started_fn=ensure_metrics_server_started,
        publish_metrics_safely_fn=publish_metrics_safely,
        config=config,
        registry=registry,
        dry_run=options.dry_run,
        only_steps=options.only_steps,
        resume_last=options.resume_last,
        resume_manifest_id=options.resume_manifest_id,
        resume_run_id=options.resume_run_id,
        force_steps=options.force_steps,
        repair_steps=options.repair_steps,
        incremental=options.incremental,
    )
    _workflow_command_runtime.execute_workflow_with_backend(
        config=config,
        execution_kwargs=execution_kwargs,
        dry_run=options.dry_run,
        only_steps=options.only_steps,
        resume_last=options.resume_last,
        ensure_observability_backend=options.ensure_observability_backend,
        observability_backend_port=options.observability_backend_port,
    )


@typed_group_command(workflow, "status")
@typed_click_argument("name")
@typed_click_option(
    "--only-steps",
    help="Comma-separated subset of step IDs to inspect with required dependencies",
)
@typed_click_option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
@typed_click_option("--run-id", help="Inspect one specific workflow run ID")
def workflow_status_command(
    name: str,
    only_steps: str | None,
    output_format: str,
    run_id: str | None,
) -> None:
    """Show workflow status with durable execution details when available."""
    try:
        config = select_workflow_steps(load_workflow_config(name), only_steps)
    except (FileNotFoundError, ValueError) as exc:
        echo_error("Workflow configuration error", str(exc))
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR) from exc
    inspection = (
        get_workflow_inspection_service().inspect_run_id(run_id)
        if run_id is not None
        else get_workflow_inspection_service().inspect_latest(config.name)
    )
    payload = build_status_payload(
        config,
        only_steps=only_steps,
        inspection=inspection,
    )
    emit_inspection_payload(payload, output_format, text_renderer=render_status_payload)
