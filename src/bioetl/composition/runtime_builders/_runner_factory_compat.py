"""Private factory compatibility helpers for runtime runner construction."""

from __future__ import annotations

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


def create_runtime_runner_from_factory(
    *,
    factory: PipelineFactoryPort,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunnerProtocol:
    """Create a runtime runner via the canonical request contract."""
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
            replay_of_run_id=getattr(ctx, "replay_of_run_id", None),
            replay_of_manifest_id=getattr(ctx, "replay_of_manifest_id", None),
            input_snapshot_fingerprint=getattr(
                ctx, "input_snapshot_fingerprint", None
            ),
        ),
        filter_config=inputs.filter_config,
        config=cast("PipelineYamlConfig", inputs.yaml_config),
        cached_bronze=inputs.cached_bronze,
    )
    return cast("PipelineRunnerProtocol", factory.create_runner(request))
