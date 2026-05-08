"""Declarative workflow CLI commands."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import click

from bioetl.domain.workflow import WorkflowConfig
from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands._workflow_support import (
    apply_cli_overrides,
    build_status_payload,
    parse_only_steps,
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
    "--force-steps",
    help="Comma-separated step IDs to force even when resume would normally skip them",
)
@click.option(
    "--repair-steps",
    help="Comma-separated step IDs to explicitly repair before resume proceeds",
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
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    enable_tracing: bool | None,
    resume_last: bool,
    force_steps: str | None,
    repair_steps: str | None,
) -> None:
    """Execute one declarative workflow config sequentially."""
    try:
        config = load_workflow_config(name)
        config = select_workflow_steps(config, only_steps)
        config = apply_cli_overrides(
            config,
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
            replay_of_run_id=replay_of_run_id,
            replay_of_manifest_id=replay_of_manifest_id,
            enable_tracing=enable_tracing,
        )
    except (FileNotFoundError, ValueError) as exc:
        echo_error("Workflow configuration error", str(exc))
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR) from exc

    parsed_force_steps = parse_only_steps(force_steps) or ()
    parsed_repair_steps = parse_only_steps(repair_steps) or ()
    ensure_metrics_server_started()
    result = asyncio.run(
        get_workflow_execution_service(registry=registry).run_workflow(
            config,
            launch_context={"only_steps": list(parse_only_steps(only_steps) or ())},
            resume_last=resume_last,
            force_steps=parsed_force_steps,
            repair_steps=parsed_repair_steps,
        )
    )
    publish_metrics_safely(
        run_label="bioetl",
        pipeline_name=f"workflow_{config.name}",
        run_type=config.defaults.run_type,
        grouping_key_extra=(
            {"workflow_run_id": result.workflow_run_id}
            if result.workflow_run_id is not None
            else None
        ),
    )
    render_run_result(
        config,
        result,
        dry_run=dry_run,
        only_steps=only_steps,
        resume_last=resume_last,
    )
    if result.status == "failed":
        raise click.exceptions.Exit(ExitCode.PIPELINE_ERROR)


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
