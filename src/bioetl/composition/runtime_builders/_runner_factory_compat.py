"""Private factory compatibility helpers for runtime runner construction."""

from __future__ import annotations

from collections.abc import Callable
from inspect import Parameter, signature
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from bioetl.domain.ports import (
    PipelineControlPlaneArtifacts,
    PipelineCreateRunnerRequest,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.ledger_collaborator import (
        PipelineRunnerProtocol,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import (
        ExecutionObservabilityPort,
        PipelineFactoryPort,
        SettingsPort,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
    )


def create_runner_from_factory(
    *,
    factory: PipelineFactoryPort,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunnerProtocol:
    """Create a runtime runner via request or legacy keyword compatibility."""
    request = PipelineCreateRunnerRequest(
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
        ),
        filter_config=inputs.filter_config,
        config=cast("PipelineYamlConfig", inputs.yaml_config),
        cached_bronze=inputs.cached_bronze,
    )
    create_runner = factory.create_runner
    parameters = signature(create_runner).parameters.values()
    accepts_kwargs = any(
        parameter.kind == Parameter.VAR_KEYWORD for parameter in parameters
    )
    accepts_request = "request" in signature(create_runner).parameters
    if not accepts_request and accepts_kwargs:
        compatibility_create_runner = cast(
            "Callable[..., PipelineRunnerProtocol]",
            create_runner,
        )
        control_plane = request.control_plane
        return compatibility_create_runner(
            run_id=request.run_id,
            runtime=request.runtime,
            started_at=request.started_at,
            settings=request.settings,
            observability=request.observability,
            manifest_id=control_plane.manifest_id,
            execution_fingerprint=control_plane.execution_fingerprint,
            config_hash=control_plane.config_hash,
            resolved_config_hash=control_plane.resolved_config_hash,
            effective_config_hash=control_plane.effective_config_hash,
            dq_contract_compatibility_hash=(
                control_plane.dq_contract_compatibility_hash
            ),
            effective_config_artifact_id=(control_plane.effective_config_artifact_id),
            filter_config=request.filter_config,
            config=request.config,
            cached_bronze=request.cached_bronze,
        )
    return cast("PipelineRunnerProtocol", create_runner(request))
