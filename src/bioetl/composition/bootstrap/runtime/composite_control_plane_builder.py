"""Control-plane builders for composite runtime bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
    RunManifestService,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_payloads import (
    build_composite_launch_context_snapshot,
    build_composite_planned_artifacts,
    build_composite_resolved_config_snapshot,
    build_composite_runtime_config_snapshot,
    build_composite_source_refs,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    CompositeControlPlaneBundle,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    control_plane_root as _shared_control_plane_root,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    to_serializable_mapping as _shared_to_serializable_mapping,
)
from bioetl.composition.runtime_builders.runner_builder_support import (
    validate_required_persistence_profile,
)
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_code_revision_provenance,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import FileRunLedgerStore, FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bind_manifest_logger",
    "build_composite_control_plane_bundle",
    "resolve_composite_control_plane_flags",
]


def resolve_composite_control_plane_flags(settings: object) -> tuple[bool, bool]:
    """Resolve manifest/ledger feature flags for executable composite runs."""
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )
    if not manifest_enabled:
        raise RuntimeError(
            "Composite execution requires run manifests; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    validate_required_persistence_profile(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label="Composite execution",
        exact_replay_execution_context_supported=True,
    )
    return True, ledger_enabled


def bind_manifest_logger(logger: LoggerPort, manifest_id: str | None) -> LoggerPort:
    """Bind ``manifest_id`` into logger context when supported."""
    if manifest_id is None:
        return logger
    bind = getattr(logger, "bind", None)
    if not callable(bind):
        return logger
    rebound = bind(manifest_id=manifest_id)
    return cast("LoggerPort", rebound)


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
    control_plane = getattr(
        getattr(infra_context.settings, "pipeline", None), "control_plane", None
    )
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )

    config_hash = _resolve_effective_config_hash(config)
    contract_ref = config.name
    contract_version = getattr(config, "version", "") or ""
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(infra_context.settings, "run_manifest"),
        metrics=infra_context.metrics,
    )
    manifest = RunManifestService(manifest_port=manifest_store).create_manifest(
        _build_composite_manifest_create_request(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
            config_hash=config_hash,
            contract_ref=contract_ref,
            contract_version=contract_version,
            required_persistence_profile=str(required_profile),
        )
    )
    run_ledger_service = _build_run_ledger_service(
        manifest_id=manifest.manifest_id,
        ledger_enabled=ledger_enabled,
        infra_context=infra_context,
        pipeline_name=config.name,
        config_hash=config_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
    )
    if run_ledger_service is not None:
        run_ledger_service.record_manifest_created(manifest)
    return CompositeControlPlaneBundle(
        manifest_id=manifest.manifest_id,
        execution_fingerprint=manifest.execution_fingerprint,
        run_ledger_service=run_ledger_service,
        config_hash=config_hash or None,
        dq_contract_compatibility_hash=(
            manifest.code_provenance.dq_contract_compatibility_hash
        ),
        effective_config_artifact_id=(
            manifest.code_provenance.effective_config_artifact_id
        ),
        contract_ref=contract_ref,
        contract_version=contract_version or None,
    )


def _build_composite_manifest_create_request(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    config_hash: str,
    contract_ref: str,
    contract_version: str,
    required_persistence_profile: str,
) -> RunManifestCreateSpec:
    """Build the manifest creation payload for one composite execution."""
    source_refs = build_composite_source_refs(
        config,
        runtime=runtime,
        settings=getattr(infra_context, "settings", None),
    )
    replay_capability = _resolve_composite_replay_capability(
        source_refs=source_refs,
        required_persistence_profile=required_persistence_profile,
    )
    code_revision = get_code_revision_provenance()
    return RunManifestCreateSpec(
        run_id=_coerce_run_id(infra_context.run_id),
        run_type=RunType.INCREMENTAL,
        pipeline_name=config.name,
        provider="composite",
        entity=config.name,
        launch_context=build_composite_launch_context_snapshot(
            config,
            runtime,
            required_persistence_profile=required_persistence_profile,
        ),
        runtime_config=build_composite_runtime_config_snapshot(runtime),
        resolved_config=build_composite_resolved_config_snapshot(config),
        source_refs=source_refs,
        planned_artifacts=build_composite_planned_artifacts(config),
        pipeline_version=contract_version or None,
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        config_hash=config_hash or None,
        resolved_config_hash=config_hash or None,
        effective_config_hash=config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
        replay_capability=replay_capability,
    )


def _resolve_composite_replay_capability(
    *,
    source_refs: tuple[object, ...],
    required_persistence_profile: str,
) -> ReplayCapability:
    """Return exact capability only when every composite member has snapshots."""
    has_full_snapshot_envelope = bool(source_refs) and all(
        bool(getattr(source_ref, "input_snapshots", ())) for source_ref in source_refs
    )
    if has_full_snapshot_envelope:
        return ReplayCapability.EXACT_REPLAY_SUPPORTED
    if required_persistence_profile in {"replay_ready", "forensic_grade"}:
        raise RuntimeError(
            "Composite execution cannot satisfy required persistence profile "
            f"'{required_persistence_profile}' because the full cached-Bronze "
            "input snapshot envelope was not captured for every seed, "
            "dependency, and enricher pipeline"
        )
    return ReplayCapability.REBUILD_ONLY


def _build_run_ledger_service(
    *,
    manifest_id: str,
    ledger_enabled: bool,
    infra_context: CompositeInfrastructureContext,
    pipeline_name: str,
    config_hash: str,
    contract_ref: str,
    contract_version: str,
) -> RunLedgerService | None:
    """Create composite run-ledger service when feature flag allows it."""
    if not ledger_enabled:
        return None
    return RunLedgerService(
        ledger_port=FileRunLedgerStore(
            base_path=_control_plane_root(infra_context.settings, "run_ledger"),
            metrics=infra_context.metrics,
        ),
        manifest_id=manifest_id,
        run_id=_coerce_run_id(infra_context.run_id),
        pipeline_name=pipeline_name,
        provider="composite",
        entity=pipeline_name,
        run_type=RunType.INCREMENTAL.value,
        resolved_config_hash=config_hash or None,
        effective_config_hash=config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
        composite_run_id=infra_context.run_id,
    )


def _resolve_effective_config_hash(config: CompositeConfig) -> str:
    """Best-effort hash for checkpoint and manifest provenance anchors."""
    try:
        payload = config.to_dict()
    except (AttributeError, TypeError, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    try:
        payload_dict: dict[str, object] = payload
        return compute_config_hash(payload_dict)
    except (TypeError, ValueError):
        return ""


def _coerce_run_id(run_id: str) -> RunID:
    """Convert composite runtime run_id string into canonical RunID type."""
    return RunID(UUID(run_id))


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _shared_control_plane_root(settings, leaf)


def _normalize_object(value: object) -> dict[str, object]:
    """Convert dataclasses/models into stable JSON-safe mappings."""
    return _shared_to_serializable_mapping(value)
