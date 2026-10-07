"""Shared context object for composite bootstrap infrastructure primitives."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from bioetl.application.ports.storage import CompositeRuntimeStorageProtocol
from bioetl.application.services.run_reports.source_identity import (
    load_repository_source_environment as _parse_repository_source_environment,
    repository_env_candidate_paths,
)
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    current_protein_class_target_type_mapping,
    is_protein_class_target_type_mapping_initialized,
)
from bioetl.domain.ports import (
    ClockPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    PipelineControlPlaneArtifacts,
    TracingPort,
)
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config.repository_source_environment import (
    read_repository_env_text,
)
from bioetl.infrastructure.config.settings_api import Settings


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


def load_repository_source_environment(
    root: str | Path,
    *,
    names: Iterable[str],
    process_environment: Mapping[str, object] | None = None,
) -> dict[str, str]:
    """Read whitelisted repository env files and return a parsed mapping."""

    root_path = Path(root)
    process = process_environment or {}
    paths = repository_env_candidate_paths(root_path, process)
    file_texts = {str(path): read_repository_env_text(path) for path in paths}
    return _parse_repository_source_environment(
        root_path,
        names=names,
        process_environment=process,
        file_texts=file_texts,
    )


def current_target_protein_classification_mapping() -> (
    ProteinClassTargetTypeMappingData | None
):
    """Return the installed protein-class mapping, or None before install."""

    if not is_protein_class_target_type_mapping_initialized():
        return None
    return current_protein_class_target_type_mapping()


__all__ = [
    "CompositeInfrastructureContext",
    "CompositeRuntimeStorageProtocol",
    "build_manifest_storage_factory",
    "current_target_protein_classification_mapping",
    "load_repository_source_environment",
]
