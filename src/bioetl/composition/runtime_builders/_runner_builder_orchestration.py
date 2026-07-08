"""Private orchestration helpers for runtime runner builder leaf module."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.composition.pipeline_runner_request import (
    build_pipeline_create_runner_request,
)
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders._runner_control_plane_artifact_policy import (
    validate_artifact_recorder_attachment as _validate_artifact_recorder_attachment,
)
from bioetl.composition.runtime_builders.ledger_collaborator import (
    PipelineRunnerProtocol,
    attach_control_plane_collaborators,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from bioetl.domain.ports import PipelineControlPlaneArtifacts

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import (
        RunnerInputs as _RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import (
        ExecutionObservabilityPort,
        SettingsPort,
    )
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class RunnerFactoryBootstrap:
    registry: PipelineRegistry
    factory: object


def bootstrap_runner_factory(
    *,
    pipeline_name: str,
    registry: PipelineRegistry | None,
    create_registry_fn: Callable[[], PipelineRegistry] = create_registry,
    ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
    register_all_pipelines_fn: Callable[..., None],
) -> RunnerFactoryBootstrap:
    """Initialize registry once and resolve the canonical runner factory."""
    effective_registry = registry if registry is not None else create_registry_fn()
    ensure_providers_loaded_fn()
    register_all_pipelines_fn(registry=effective_registry)
    return RunnerFactoryBootstrap(
        registry=effective_registry,
        factory=effective_registry.get(pipeline_name).factory,
    )


def create_runner(
    *,
    factory: object,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunnerProtocol:
    """Create the runtime runner from the registered factory seam."""
    request = build_pipeline_create_runner_request(
        run_id=ctx.run_id,
        runtime=inputs.runtime_config,
        started_at=getattr(ctx, "started_at", MISSING_RUNTIME_TIMESTAMP),
        settings=cast("SettingsPort", inputs.settings),
        observability=cast(
            "ExecutionObservabilityPort",
            inputs.observability,
        ),
        control_plane=PipelineControlPlaneArtifacts(
            manifest_id=getattr(ctx, "manifest_id", None),
            execution_fingerprint=getattr(ctx, "execution_fingerprint", None),
            config_hash=getattr(ctx, "config_hash", None),
            resolved_config_hash=getattr(ctx, "resolved_config_hash", None),
            effective_config_hash=getattr(ctx, "effective_config_hash", None),
            dq_contract_compatibility_hash=getattr(
                ctx, "dq_contract_compatibility_hash", None
            ),
            effective_config_artifact_id=getattr(
                ctx, "effective_config_artifact_id", None
            ),
            replay_of_run_id=getattr(ctx, "replay_of_run_id", None),
            replay_of_manifest_id=getattr(ctx, "replay_of_manifest_id", None),
            input_snapshot_fingerprint=getattr(ctx, "input_snapshot_fingerprint", None),
        ),
        filter_config=inputs.filter_config,
        config=cast("PipelineYamlConfig", inputs.yaml_config),
        cached_bronze=inputs.cached_bronze,
    )
    return cast("PipelineRunnerProtocol", factory.create_runner(request))


def attach_runner_control_plane_collaborators(
    *,
    runner: PipelineRunnerProtocol,
    required_profile: str,
    run_ledger_service: RunLedgerService | None,
) -> None:
    """Attach optional control-plane collaborators and validate closure."""
    if run_ledger_service is None:
        _validate_artifact_recorder_attachment(
            required_profile=required_profile,
            candidate_count=0,
            attached_count=0,
            missing_attach_method_count=0,
            failed_count=0,
        )
        return
    attachment_result = attach_control_plane_collaborators(
        runner,
        run_ledger_service,
    )
    _validate_artifact_recorder_attachment(
        required_profile=required_profile,
        candidate_count=attachment_result.candidate_count,
        attached_count=attachment_result.attached_count,
        missing_attach_method_count=attachment_result.missing_attach_method_count,
        failed_count=attachment_result.failed_count,
    )
