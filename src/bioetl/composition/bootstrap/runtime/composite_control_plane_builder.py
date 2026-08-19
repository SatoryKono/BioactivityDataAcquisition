"""Control-plane builders for composite runtime bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
    RunManifestService,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_builder_support import (
    CompositeControlPlaneConfigArtifacts,
    _build_composite_control_plane_config_artifacts,
    _read_composite_control_plane_settings,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_payloads import (
    build_composite_launch_context_snapshot,
    build_composite_planned_artifacts,
    build_composite_resolved_config_snapshot,
    build_composite_runtime_config_snapshot,
    build_composite_source_refs,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    bind_manifest_logger as _bind_manifest_logger,
    build_run_ledger_service as _build_run_ledger_service,
    coerce_run_id as _coerce_run_id,
    compute_composite_input_snapshot_fingerprint as _compute_composite_input_snapshot_fingerprint,
    control_plane_root as _control_plane_root,
    normalize_object as _support_normalize_object,
    resolve_composite_replay_capability as _resolve_composite_replay_capability,
)
from bioetl.composition.bootstrap.runtime.composite_control_plane_bundle import (
    CompositeControlPlaneBundle,
)
from bioetl.composition.occurrence_identity import create_runtime_occurrence_id
from bioetl.composition.runtime_builders.runner_control_plane_assembly import (
    validate_required_persistence_profile,
)
from bioetl.composition.services.versioning import get_code_revision_provenance
from bioetl.domain.control_plane.run_manifest import RunManifest
from bioetl.domain.types import RunType
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
    FileContractEvidenceRecorder,
)
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "bind_manifest_logger",
    "build_composite_control_plane_bundle",
    "resolve_composite_control_plane_flags",
]


def resolve_composite_control_plane_flags(settings: object) -> tuple[bool, bool]:
    """Resolve manifest/ledger feature flags for executable composite runs."""
    _, manifest_enabled, ledger_enabled, _, effective_required_profile = (
        _read_composite_control_plane_settings(settings)
    )
    if not manifest_enabled:
        raise RuntimeError(
            "Composite execution requires run manifests; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    validate_required_persistence_profile(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=effective_required_profile,
        execution_label="Composite execution",
        exact_replay_execution_context_supported=False,
        composite_resume_rich_replay_supported=True,
    )
    return True, ledger_enabled


def bind_manifest_logger(logger: LoggerPort, manifest_id: str | None) -> LoggerPort:
    """Bind ``manifest_id`` into logger context when supported."""
    return _bind_manifest_logger(logger, manifest_id)


def _normalize_object(value: object) -> dict[str, object]:
    """Convert dataclasses/models into stable JSON-safe mappings."""
    return _support_normalize_object(value)


def _build_composite_control_plane_manifest(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    config_artifacts: CompositeControlPlaneConfigArtifacts,
    ledger_enabled: bool,
) -> RunManifest:
    """Create manifest for composite control plane."""
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(infra_context.settings, "run_manifest"),
        metrics=infra_context.metrics,
    )
    return RunManifestService(
        manifest_port=manifest_store,
        metrics=infra_context.metrics,
        clock=SystemClock(),
        contract_evidence_recorder=FileContractEvidenceRecorder(
            base_path=manifest_store.base_path
        ),
        _manifest_id_factory=lambda: create_runtime_occurrence_id(
            "composite_run_manifest"
        ),
    ).create_manifest(
        _build_composite_manifest_create_request(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
            config_artifacts=config_artifacts,
            ledger_enabled=ledger_enabled,
        )
    )


def build_composite_control_plane_bundle(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
) -> CompositeControlPlaneBundle:
    """Materialize manifest/ledger artifacts for one composite execution."""
    _manifest_enabled, ledger_enabled = resolve_composite_control_plane_flags(
        infra_context.settings
    )
    config_artifacts = _build_composite_control_plane_config_artifacts(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
    )
    manifest = _build_composite_control_plane_manifest(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        config_artifacts=config_artifacts,
        ledger_enabled=ledger_enabled,
    )
    run_ledger_service = _build_run_ledger_service(
        manifest_id=manifest.manifest_id,
        ledger_enabled=ledger_enabled,
        infra_context=infra_context,
        pipeline_name=config.name,
        resolved_config_hash=config_artifacts.resolved_config_hash,
        effective_config_hash=config_artifacts.effective_config_hash,
        dq_contract_compatibility_hash=config_artifacts.dq_contract_compatibility_hash,
        effective_config_artifact_id=config_artifacts.effective_config_artifact_id,
        contract_ref=config_artifacts.contract_ref,
        contract_version=config_artifacts.contract_version,
    )
    if run_ledger_service is not None:
        run_ledger_service.record_manifest_created(manifest)
    return CompositeControlPlaneBundle(
        manifest_id=manifest.manifest_id,
        execution_fingerprint=manifest.execution_fingerprint,
        run_ledger_service=run_ledger_service,
        config_hash=config_artifacts.resolved_config_hash,
        resolved_config_hash=config_artifacts.resolved_config_hash or None,
        effective_config_hash=config_artifacts.effective_config_hash or None,
        source_fingerprint=config_artifacts.source_fingerprint or None,
        dq_contract_compatibility_hash=(
            config_artifacts.dq_contract_compatibility_hash or None
        ),
        effective_config_artifact_id=config_artifacts.effective_config_artifact_id
        or None,
        input_snapshot_fingerprint=_compute_composite_input_snapshot_fingerprint(
            manifest.source_refs
        ),
        contract_ref=config_artifacts.contract_ref,
        contract_version=config_artifacts.contract_version or None,
    )


def _build_composite_manifest_create_request(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    config_artifacts: CompositeControlPlaneConfigArtifacts,
    ledger_enabled: bool = True,
) -> RunManifestCreateSpec:
    """Build the manifest creation payload for one composite execution."""
    source_refs = build_composite_source_refs(
        config, runtime=runtime, settings=getattr(infra_context, "settings", None)
    )
    replay_capability = _resolve_composite_replay_capability(
        source_refs=source_refs,
        required_persistence_profile=config_artifacts.effective_required_profile,
        resume_requested=runtime.resume,
    )
    code_revision = get_code_revision_provenance()
    dependency_lock_hash = getattr(code_revision, "dependency_lock_hash", None)
    return RunManifestCreateSpec(
        run_id=_coerce_run_id(infra_context.run_id),
        run_type=RunType.INCREMENTAL,
        pipeline_name=config.name,
        provider="composite",
        entity=config_artifacts.contract_entity,
        launch_context=build_composite_launch_context_snapshot(
            config,
            runtime,
            required_persistence_profile=config_artifacts.effective_required_profile,
            run_ledger_enabled=ledger_enabled,
        ),
        runtime_config=build_composite_runtime_config_snapshot(runtime),
        resolved_config=build_composite_resolved_config_snapshot(config),
        source_refs=source_refs,
        planned_artifacts=build_composite_planned_artifacts(config),
        pipeline_version=config_artifacts.pipeline_version,
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        dependency_lock_hash=dependency_lock_hash,
        config_hash=config_artifacts.resolved_config_hash,
        resolved_config_hash=config_artifacts.resolved_config_hash or None,
        effective_config_hash=config_artifacts.effective_config_hash or None,
        source_fingerprint=config_artifacts.source_fingerprint or None,
        contract_ref=config_artifacts.contract_ref,
        contract_version=config_artifacts.contract_version,
        contract_schema_hash=config_artifacts.contract_schema_hash,
        dq_policy_ref=config_artifacts.dq_policy_ref,
        rule_bundle_version=config_artifacts.rule_bundle_version,
        normalization_profile_ref=config_artifacts.normalization_profile_ref,
        normalization_profile_version=config_artifacts.normalization_profile_version,
        normalization_profile_hash=config_artifacts.normalization_profile_hash,
        dq_contract_compatibility_hash=(
            config_artifacts.dq_contract_compatibility_hash or None
        ),
        effective_config_artifact_id=config_artifacts.effective_config_artifact_id
        or None,
        replay_capability=replay_capability,
    )
