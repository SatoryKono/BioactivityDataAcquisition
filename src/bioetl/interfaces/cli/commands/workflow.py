"""Declarative workflow CLI commands."""

from __future__ import annotations

from uuid import UUID
from typing import TYPE_CHECKING

import click

from bioetl.domain.workflow import WorkflowConfig
from bioetl.interfaces.cli.commands._workflow_run_support import (
    _execute_workflow_and_publish_metrics,
    _handle_workflow_result,
    _load_and_apply_workflow_config,
    _validate_run_workflow_options,
)
from bioetl.interfaces.cli.commands._workflow_support import (
    build_status_payload,
    render_run_result,
    render_status_payload,
    select_workflow_steps,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration import (
    publish_metrics_safely,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.workflow_execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.control_plane.workflow_inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "load_workflow_config",
    "workflow",
]


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load one declarative workflow config through composition seams."""
    from bioetl.composition.control_plane_api import load_workflow_config as _impl

    return _impl(name)


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
) -> WorkflowExecutionService:
    """Resolve workflow execution orchestration through composition seams."""
    from bioetl.composition.control_plane_api import (
        get_workflow_execution_service as _impl,
    )

    return _impl(registry=registry)


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Resolve workflow inspection through composition seams."""
    from bioetl.composition.control_plane_api import (
        get_workflow_inspection_service as _impl,
    )

    return _impl()


@click.group()
def workflow() -> None:
    """Run and inspect declarative workflows."""


@workflow.command("run")
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Enable dry-run for pipeline steps")
@click.option(
    "--only-steps",
    help="Comma-separated subset of step IDs to execute with required dependencies",
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    help="Override workflow pipeline run_type for this execution",
)
@click.option(
    "--start-offset",
    type=int,
    help="Override pipeline start_offset for workflow pipeline steps",
)
@click.option(
    "--limit",
    type=int,
    help="Override pipeline record limit for workflow pipeline steps",
)
@click.option(
    "--input-csv",
    type=click.Path(exists=True),
    help="Path to CSV file with filter IDs for workflow pipeline steps",
)
@click.option(
    "--filter-column",
    type=str,
    help="Override CSV filter column for workflow pipeline steps",
)
@click.option(
    "--filter-field",
    type=str,
    help="Override source filter field for workflow pipeline steps",
)
@click.option(
    "--vacuum-after-run",
    is_flag=True,
    default=None,
    help="Override Delta VACUUM execution after successful workflow pipeline steps",
)
@click.option(
    "--vacuum-retention-days",
    type=int,
    help="Override Delta VACUUM retention for workflow pipeline steps",
)
@click.option(
    "--log-level",
    type=str,
    help="Override log level for workflow pipeline steps",
)
@click.option(
    "--ignore-yaml-filter",
    is_flag=True,
    default=None,
    help="Ignore YAML filter defaults for workflow pipeline steps",
)
@click.option(
    "--skip-gold",
    is_flag=True,
    default=None,
    help="Skip Gold writes for workflow pipeline steps",
)
@click.option(
    "--execution-context",
    type=str,
    help="Override execution context for workflow pipeline steps",
)
@click.option(
    "--use-cached-bronze/--no-cached-bronze",
    default=None,
    help="Override Bronze cache usage for workflow pipeline steps",
)
@click.option(
    "--cached-bronze-path",
    type=click.Path(exists=True),
    help="Explicit Bronze cache path for workflow pipeline steps",
)
@click.option(
    "--cached-bronze-date",
    type=str,
    help="Bronze cache date filter for workflow pipeline steps",
)
@click.option(
    "--exact-replay/--no-exact-replay",
    "exact_replay",
    default=None,
    help="Override strict exact replay request for workflow pipeline steps",
)
@click.option(
    "--required-persistence-profile",
    type=click.Choice(["degraded_observable", "replay_ready", "forensic_grade"]),
    default=None,
    help="Override required control-plane persistence profile for workflow steps",
)
@click.option(
    "--replay-of-run-id",
    type=str,
    help="Explicit parent run_id for exact replay workflow pipeline steps",
)
@click.option(
    "--replay-of-manifest-id",
    type=str,
    help="Explicit parent manifest_id for exact replay workflow pipeline steps",
)
@click.option(
    "--tracing/--no-tracing",
    "enable_tracing",
    default=None,
    help="Override distributed tracing for workflow pipeline steps",
)
@click.option(
    "--resume-last",
    is_flag=True,
    help="Resume the latest incomplete or failed execution for this workflow",
)
@click.option(
    "--resume-manifest-id",
    type=str,
    help="Resume one specific workflow execution state selected by manifest_id",
)
@click.option(
    "--resume-run-id",
    type=click.UUID,
    help="Resume one specific workflow execution state selected by workflow run_id",
)
@click.option(
    "--force-steps",
    help="Comma-separated step IDs to force even when resume would normally skip them",
)
@click.option(
    "--repair-steps",
    help="Comma-separated step IDs to explicitly repair before resume proceeds",
)
@click.option(
    "--incremental",
    is_flag=True,
    default=False,
    help="Auto-increment start_offset from last successful execution. "
    "Cannot be used with resume selectors or --start-offset.",
)
@click.pass_obj
def run_workflow_command(
    registry: PipelineRegistry | None,
    name: str,
    dry_run: bool,
    only_steps: str | None,
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
    resume_last: bool,
    resume_manifest_id: str | None,
    resume_run_id: UUID | None,
    force_steps: str | None,
    repair_steps: str | None,
    incremental: bool,
) -> None:
    """Execute one declarative workflow config sequentially."""
    _validate_run_workflow_options(
        incremental=incremental,
        resume_last=resume_last,
        resume_manifest_id=resume_manifest_id,
        resume_run_id=resume_run_id,
        start_offset=start_offset,
    )
    config = _load_and_apply_workflow_config(
        load_workflow_config_fn=load_workflow_config,
        name=name,
        only_steps=only_steps,
        dry_run=dry_run,
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
    )
    result = _execute_workflow_and_publish_metrics(
        get_workflow_execution_service_fn=get_workflow_execution_service,
        ensure_metrics_server_started_fn=ensure_metrics_server_started,
        publish_metrics_safely_fn=publish_metrics_safely,
        config=config,
        registry=registry,
        dry_run=dry_run,
        only_steps=only_steps,
        resume_last=resume_last,
        resume_manifest_id=resume_manifest_id,
        resume_run_id=resume_run_id,
        force_steps=force_steps,
        repair_steps=repair_steps,
        incremental=incremental,
    )
    render_run_result(
        config,
        result,
        dry_run=dry_run,
        only_steps=only_steps,
        resume_last=resume_last,
    )
    _handle_workflow_result(result)


@workflow.command("status")
@click.argument("name")
@click.option(
    "--only-steps",
    help="Comma-separated subset of step IDs to inspect with required dependencies",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
@click.option("--run-id", help="Inspect one specific workflow run ID")
def workflow_status_command(
    name: str,
    only_steps: str | None,
    output_format: str,
    run_id: str | None,
) -> None:
    """Show workflow status with durable execution details when available."""
    try:
        config = load_workflow_config(name)
        config = select_workflow_steps(config, only_steps)
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
    emit_inspection_payload(
        payload,
        output_format,
        text_renderer=render_status_payload,
    )
