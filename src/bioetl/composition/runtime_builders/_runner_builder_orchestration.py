"""Private orchestration helpers for runtime runner builder leaf module."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders._runner_builder_support import (
    validate_artifact_recorder_attachment as _validate_artifact_recorder_attachment,
)
from bioetl.composition.runtime_builders._runner_factory_compat import (
    create_runner_from_factory as _create_runner_from_factory,
)
from bioetl.composition.runtime_builders.ledger_collaborator import (
    PipelineRunnerProtocol,
    attach_control_plane_collaborators,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs as _RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


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
    return _create_runner_from_factory(
        factory=factory,
        ctx=ctx,
        inputs=inputs,
    )


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
