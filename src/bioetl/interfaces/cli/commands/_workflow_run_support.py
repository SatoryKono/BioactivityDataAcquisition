"""Run-command helpers for declarative workflow CLI."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import UUID

import click

from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    resolve_effective_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_reproducibility_family_profile,
)
from bioetl.domain.types import RunID
from bioetl.interfaces.cli.commands._workflow_support import (
    WorkflowRunOptionsConfig,
    apply_cli_override_config,
    build_workflow_run_options_override_from_mapping,
    parse_only_steps,
    select_workflow_steps,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

_WORKFLOW_PUBLICATION_METRIC_NAMES = (
    "bioetl_workflow_expected",
    "bioetl_workflow_pipeline_expected",
    "bioetl_workflow_runs",
    "bioetl_workflow_runs_total",
    "bioetl_workflow_runs_created",
    "bioetl_workflow_current_status",
    "bioetl_workflow_step_events",
    "bioetl_workflow_step_events_total",
    "bioetl_workflow_step_events_created",
    "bioetl_workflow_step_duration_seconds",
    "bioetl_workflow_step_duration_seconds_bucket",
    "bioetl_workflow_step_duration_seconds_count",
    "bioetl_workflow_step_duration_seconds_sum",
    "bioetl_workflow_step_duration_seconds_created",
)

_WORKFLOW_PLANNED_PUBLICATION_METRIC_NAMES = (
    "bioetl_workflow_expected",
    "bioetl_workflow_pipeline_expected",
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.workflow.execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.workflow_runner_service import (
        WorkflowRunExecutionResult,
    )
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig


class _WorkflowExecutionServiceResolver(Protocol):
    """Callable boundary for resolving the workflow execution service."""

    def __call__(
        self,
        registry: PipelineRegistry | None = None,
    ) -> WorkflowExecutionService: ...


class _MetricsPublisher(Protocol):
    """Callable boundary for best-effort workflow metrics publication."""

    def __call__(
        self,
        run_label: str = "bioetl",
        *,
        pipeline_name: str | None = None,
        run_type: str | None = None,
        grouping_key_extra: Mapping[str, str] | None = None,
        metric_names: tuple[str, ...] | None = None,
    ) -> object: ...


__all__ = [
    "_build_workflow_override_config",
    "_execute_workflow_and_publish_metrics",
    "_handle_workflow_result",
    "_load_and_apply_workflow_config",
    "_validate_run_workflow_options",
    "_WorkflowExecutionServiceResolver",
    "_MetricsPublisher",
]


def _validate_run_workflow_options(
    *,
    incremental: bool,
    resume_last: bool,
    resume_manifest_id: str | None,
    resume_run_id: UUID | None,
    start_offset: int | None,
) -> None:
    """Validate mutually exclusive workflow run options."""
    explicit_resume_requested = (
        resume_last or resume_manifest_id is not None or resume_run_id is not None
    )
    if resume_last and resume_manifest_id is not None:
        echo_error(
            "Invalid options",
            "--resume-last cannot be used together with --resume-manifest-id",
        )
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR)
    if resume_last and resume_run_id is not None:
        echo_error(
            "Invalid options",
            "--resume-last cannot be used together with --resume-run-id",
        )
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR)
    if resume_manifest_id is not None and resume_run_id is not None:
        echo_error(
            "Invalid options",
            "--resume-manifest-id cannot be used together with --resume-run-id",
        )
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR)
    if incremental and explicit_resume_requested:
        echo_error(
            "Invalid options",
            "--incremental cannot be used together with resume selectors",
        )
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR)
    if incremental and start_offset is not None:
        echo_error(
            "Invalid options",
            "--incremental cannot be used when --start-offset is explicitly set. "
            "Either use --incremental for auto-increment or --start-offset for "
            "manual control.",
        )
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR)


def _build_workflow_override_config(
    values: Mapping[str, object],
) -> WorkflowRunOptionsConfig:
    """Build one workflow override config for config loading/application."""
    return build_workflow_run_options_override_from_mapping(values)


def _load_and_apply_workflow_config(
    *,
    load_workflow_config_fn: Callable[[str], WorkflowConfig],
    name: str,
    only_steps: str | None,
    override_config: WorkflowRunOptionsConfig,
) -> WorkflowConfig:
    """Load workflow config and apply CLI overrides."""
    try:
        config = load_workflow_config_fn(name)
        config = select_workflow_steps(config, only_steps)
        config = apply_cli_override_config(config, override_config)
        _validate_workflow_pipeline_replay_prerequisites(config)
        return config
    except (FileNotFoundError, ValueError) as exc:
        echo_error("Workflow configuration error", str(exc))
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR) from exc


def _execute_workflow_and_publish_metrics(
    *,
    get_workflow_execution_service_fn: _WorkflowExecutionServiceResolver,
    ensure_metrics_server_started_fn: Callable[[], object],
    publish_metrics_safely_fn: _MetricsPublisher,
    config: WorkflowConfig,
    registry: PipelineRegistry | None,
    dry_run: bool,
    only_steps: str | None,
    resume_last: bool,
    resume_manifest_id: str | None,
    resume_run_id: UUID | None,
    force_steps: str | None,
    repair_steps: str | None,
    incremental: bool,
) -> WorkflowRunExecutionResult:
    """Execute workflow and publish metrics."""
    parsed_force_steps = parse_only_steps(force_steps) or ()
    parsed_repair_steps = parse_only_steps(repair_steps) or ()
    workflow_execution_service = get_workflow_execution_service_fn(registry=registry)
    if not dry_run:
        ensure_metrics_server_started_fn()
        _record_expected_pipeline_metrics(workflow_execution_service, config)
        publish_metrics_safely_fn(
            run_label="bioetl",
            metric_names=_WORKFLOW_PLANNED_PUBLICATION_METRIC_NAMES,
        )
    result = asyncio.run(
        workflow_execution_service.run_workflow(
            config,
            launch_context={"only_steps": list(parse_only_steps(only_steps) or ())},
            resume_last=resume_last,
            resume_manifest_id=resume_manifest_id,
            resume_run_id=RunID(resume_run_id) if resume_run_id is not None else None,
            force_steps=parsed_force_steps,
            repair_steps=parsed_repair_steps,
            incremental=incremental,
        )
    )
    if dry_run:
        return result

    pipeline_name = _workflow_metrics_pipeline_name(config)
    run_type = _workflow_metrics_run_type(config)
    grouping_key_extra = (
        {"workflow_run_id": result.workflow_run_id}
        if result.workflow_run_id is not None
        else None
    )
    metric_names = _WORKFLOW_PUBLICATION_METRIC_NAMES if pipeline_name is None else None
    publish_metrics_safely_fn(
        run_label="bioetl",
        pipeline_name=pipeline_name,
        run_type=run_type,
        grouping_key_extra=grouping_key_extra,
        metric_names=metric_names,
    )
    return result


def _record_expected_pipeline_metrics(
    workflow_execution_service: WorkflowExecutionService,
    config: WorkflowConfig,
) -> None:
    """Record planned workflow pipeline selector scopes."""
    workflow_execution_service.record_expected_pipeline_metrics(config)


def _handle_workflow_result(result: WorkflowRunExecutionResult) -> None:
    """Handle workflow execution result and exit with appropriate code."""
    if result.status == "success":
        raise click.exceptions.Exit(ExitCode.OK)
    error_message = _workflow_failure_message(result)
    echo_error("Workflow failed", error_message)
    raise click.exceptions.Exit(ExitCode.PIPELINE_ERROR)


def _workflow_metrics_pipeline_name(config: WorkflowConfig) -> str | None:
    """Resolve a Pushgateway-safe pipeline grouping label for workflows."""
    single_pipeline_name = getattr(config, "single_pipeline_name", None)
    if isinstance(single_pipeline_name, str) and single_pipeline_name:
        return single_pipeline_name
    return None


def _workflow_metrics_run_type(config: WorkflowConfig) -> str | None:
    """Resolve the effective workflow run_type for metrics publication."""
    single_pipeline_name = getattr(config, "single_pipeline_name", None)
    if not isinstance(single_pipeline_name, str) or not single_pipeline_name:
        return None
    defaults = getattr(config, "defaults", None)
    default_run_type = getattr(defaults, "run_type", None)
    if isinstance(default_run_type, str) and default_run_type:
        return default_run_type
    run_type_context = getattr(config, "run_type_context", None)
    if isinstance(run_type_context, str) and run_type_context:
        return run_type_context
    return "incremental"


def _workflow_failure_message(result: WorkflowRunExecutionResult) -> str:
    """Extract one human-readable failure message from a workflow result."""
    top_level_error = getattr(result, "error_message", None)
    if isinstance(top_level_error, str) and top_level_error:
        return top_level_error
    steps = getattr(result, "steps", ())
    for step in steps:
        error_message = getattr(step, "error_message", None)
        if isinstance(error_message, str) and error_message:
            return error_message
    return "Unknown error"


def _validate_workflow_pipeline_replay_prerequisites(config: WorkflowConfig) -> None:
    """Fail fast when workflow pipeline steps request strict replay without snapshots."""
    for step in config.pipeline_steps:
        exact_replay = _resolve_step_option(config, step, "exact_replay")
        use_cached_bronze = _resolve_step_option(config, step, "use_cached_bronze")
        configured_profile = (
            _resolve_step_option(
                config,
                step,
                "required_persistence_profile",
            )
            or DEFAULT_REQUIRED_PERSISTENCE_PROFILE
        )
        required_profile = _resolve_workflow_step_required_profile(
            step=step,
            configured_profile=str(configured_profile),
            exact_replay=bool(exact_replay),
        )

        if bool(exact_replay) and not bool(use_cached_bronze):
            raise ValueError(
                f"Workflow step '{step.step_id}' currently requires "
                "--use-cached-bronze with snapshot-backed Bronze inputs when "
                "--exact-replay is enabled"
            )

        if str(required_profile) in STRICT_PERSISTENCE_PROFILES and not bool(
            use_cached_bronze
        ):
            raise ValueError(
                f"Workflow step '{step.step_id}' requests required_persistence_profile="
                f"'{required_profile}', which requires immutable snapshot-backed "
                "Bronze inputs. Use --use-cached-bronze "
                "(optionally with --cached-bronze-path/--cached-bronze-date)."
            )


def _resolve_workflow_step_required_profile(
    *,
    step: WorkflowStepConfig,
    configured_profile: str,
    exact_replay: bool,
) -> str:
    """Resolve one workflow step profile against the published family floor."""
    pipeline_name = getattr(step, "pipeline_name", None)
    if not isinstance(pipeline_name, str) or "_" not in pipeline_name:
        return configured_profile
    provider, entity = pipeline_name.split("_", 1)
    execution_context: Literal["source", "composite"] = (
        "composite" if provider == "composite" else "source"
    )
    profile = resolve_reproducibility_family_profile(
        provider=provider,
        entity=entity,
        contract_ref=f"{provider}.{entity}",
        execution_context=execution_context,
    )
    return resolve_effective_required_persistence_profile(
        configured_required_profile=configured_profile,
        family_default_profile=profile.default_required_persistence_profile,
        exact_replay_requested=exact_replay,
        allow_degraded_opt_down=configured_profile == "degraded_observable",
    )


def _resolve_step_option(
    config: WorkflowConfig,
    step: WorkflowStepConfig,
    field_name: Literal[
        "exact_replay",
        "use_cached_bronze",
        "required_persistence_profile",
    ],
) -> bool | str | None:
    """Resolve one workflow step run option with workflow defaults fallback."""
    if field_name == "exact_replay":
        step_value = step.run_options.exact_replay
        return step_value if step_value is not None else config.defaults.exact_replay
    if field_name == "use_cached_bronze":
        step_value = step.run_options.use_cached_bronze
        return (
            step_value if step_value is not None else config.defaults.use_cached_bronze
        )
    profile_value = step.run_options.required_persistence_profile
    if profile_value is not None:
        return profile_value
    return config.defaults.required_persistence_profile
