"""Control-plane builders for composite runtime bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    bind_manifest_logger as _bind_manifest_logger,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    build_run_ledger_service as _build_run_ledger_service,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    coerce_run_id as _coerce_run_id,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    compute_composite_input_snapshot_fingerprint as _compute_composite_input_snapshot_fingerprint,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    control_plane_root as _control_plane_root,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    normalize_object as _support_normalize_object,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    resolve_composite_replay_capability as _resolve_composite_replay_capability,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    CompositeControlPlaneBundle,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_composite_effective_config_artifact,
)
from bioetl.composition.runtime_builders.runner_builder_support import (
    validate_required_persistence_profile,
)
from bioetl.composition.services.versioning import get_code_revision_provenance
from bioetl.domain.control_plane.reproducibility_policy import (
    is_critical_reproducibility_runtime,
    legacy_config_hash_from_resolved_config_hash,
    resolve_effective_required_persistence_profile,
)
from bioetl.domain.types import RunType
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort

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
    effective_required_profile = _resolve_composite_required_persistence_profile(
        settings,
        configured_required_profile=required_profile,
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
        exact_replay_execution_context_supported=True,
    )
    return True, ledger_enabled


def bind_manifest_logger(logger: LoggerPort, manifest_id: str | None) -> LoggerPort:
    """Bind ``manifest_id`` into logger context when supported."""
    return _bind_manifest_logger(logger, manifest_id)


def _resolve_composite_required_persistence_profile(
    settings: object,
    *,
    configured_required_profile: object,
) -> str:
    """Resolve composite launches against the published replay-ready default."""
    return resolve_effective_required_persistence_profile(
        configured_required_profile=configured_required_profile,
        family_default_profile="replay_ready",
        critical_runtime=is_critical_reproducibility_runtime(
            runtime_environment=getattr(settings, "env", None),
            debug_mode=getattr(settings, "debug", False),
        ),
    )


def _normalize_object(value: object) -> dict[str, object]:
    """Convert dataclasses/models into stable JSON-safe mappings."""
    return _support_normalize_object(value)


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
    effective_required_profile = _resolve_composite_required_persistence_profile(
        infra_context.settings,
        configured_required_profile=required_profile,
    )
    contract_ref = config.name
    contract_version = getattr(config, "version", "") or ""
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        dq_contract_compatibility_hash,
    ) = create_and_persist_composite_effective_config_artifact(
        pipeline_name=config.name,
        config=config,
        runtime_config=runtime,
        required_persistence_profile=effective_required_profile,
        settings=infra_context.settings,
        logger=infra_context.logger,
        run_id=_coerce_run_id(infra_context.run_id),
    )
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(infra_context.settings, "run_manifest"),
        metrics=infra_context.metrics,
    )
    manifest = RunManifestService(
        manifest_port=manifest_store,
        clock=SystemClock(),
    ).create_manifest(
        _build_composite_manifest_create_request(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
            resolved_config_hash=resolved_config_hash,
            effective_config_hash=effective_config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            contract_ref=contract_ref,
            contract_version=contract_version,
            required_persistence_profile=effective_required_profile,
        )
    )
    run_ledger_service = _build_run_ledger_service(
        manifest_id=manifest.manifest_id,
        ledger_enabled=ledger_enabled,
        infra_context=infra_context,
        pipeline_name=config.name,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
    )
    if run_ledger_service is not None:
        run_ledger_service.record_manifest_created(manifest)
    return CompositeControlPlaneBundle(
        manifest_id=manifest.manifest_id,
        execution_fingerprint=manifest.execution_fingerprint,
        run_ledger_service=run_ledger_service,
        config_hash=legacy_config_hash_from_resolved_config_hash(
            resolved_config_hash or None
        ),
        resolved_config_hash=resolved_config_hash or None,
        effective_config_hash=effective_config_hash or None,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash or None,
        effective_config_artifact_id=effective_config_artifact_id or None,
        input_snapshot_fingerprint=_compute_composite_input_snapshot_fingerprint(
            manifest.source_refs
        ),
        contract_ref=contract_ref,
        contract_version=contract_version or None,
    )


def _build_composite_manifest_create_request(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    resolved_config_hash: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_ref: str,
    contract_version: str,
    required_persistence_profile: str,
) -> RunManifestCreateSpec:
    """Build the manifest creation payload for one composite execution."""
    source_refs = build_composite_source_refs(
        config, runtime=runtime, settings=getattr(infra_context, "settings", None)
    )
    replay_capability = _resolve_composite_replay_capability(
        source_refs=source_refs,
        required_persistence_profile=required_persistence_profile,
    )
    code_revision = get_code_revision_provenance()
    dependency_lock_hash = getattr(code_revision, "dependency_lock_hash", None)
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
        dependency_lock_hash=dependency_lock_hash,
        config_hash=legacy_config_hash_from_resolved_config_hash(
            resolved_config_hash or None
        ),
        resolved_config_hash=resolved_config_hash or None,
        effective_config_hash=effective_config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash or None,
        effective_config_artifact_id=effective_config_artifact_id or None,
        replay_capability=replay_capability,
    )
