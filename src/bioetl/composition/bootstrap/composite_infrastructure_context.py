"""Shared context object for composite bootstrap infrastructure primitives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable

from bioetl.domain.ports import (
    ClockPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    PipelineControlPlaneArtifacts,
    TracingPort,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.domain.value_objects.run_context import RunContext

from bioetl.application.ports.storage import CompositeRuntimeStorageProtocol


@dataclass(frozen=True, slots=True)
class CompositeInfrastructureContext:
    """Bundle of infrastructure primitives required by composite bootstrap."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: CompositeRuntimeStorageProtocol
    lock: LockPort
    clock: ClockPort | None = None
    storage_for_manifest: (
        Callable[[PipelineControlPlaneArtifacts], CompositeRuntimeStorageProtocol]
        | None
    ) = None


def build_manifest_storage_factory(
    *,
    run_context: RunContext,
    storage_bootstrapper: Callable[..., CompositeRuntimeStorageProtocol],
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
    settings: Settings,
) -> Callable[[PipelineControlPlaneArtifacts | None], CompositeRuntimeStorageProtocol]:
    """Bind storage to the original run identity and optional manifest anchors."""

    def build(
        artifacts: PipelineControlPlaneArtifacts | None,
    ) -> CompositeRuntimeStorageProtocol:
        context = (
            run_context
            if artifacts is None
            else replace(
                run_context,
                manifest_id=artifacts.manifest_id,
                config_hash=artifacts.config_hash,
                resolved_config_hash=artifacts.resolved_config_hash,
                effective_config_hash=artifacts.effective_config_hash,
                execution_fingerprint=artifacts.execution_fingerprint,
                dq_contract_compatibility_hash=artifacts.dq_contract_compatibility_hash,
                effective_config_artifact_id=artifacts.effective_config_artifact_id,
                input_snapshot_fingerprint=artifacts.input_snapshot_fingerprint,
            )
        )
        return storage_bootstrapper(
            run_context=context,
            logger=logger,
            metrics=metrics,
            tracing=tracer,
            enable_csv_export=True,
            settings=settings,
        )

    return build


__all__ = [
    "CompositeInfrastructureContext",
    "CompositeRuntimeStorageProtocol",
    "build_manifest_storage_factory",
]
