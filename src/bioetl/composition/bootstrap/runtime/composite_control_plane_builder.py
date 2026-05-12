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
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    resolve_contract_identity,
)
from bioetl.composition.runtime_builders.runner_builder_support import (
    validate_required_persistence_profile,
)
from bioetl.composition.services.versioning import get_code_revision_provenance
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    is_critical_reproducibility_runtime,
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
        composite_resume_rich_replay_supported=True,
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


def _build_composite_control_plane_config_artifacts(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
) -> tuple[
    str,
    str,
    str,
    str,
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str,
    str,
]:
    """Build configuration and contract artifacts for composite control plane."""
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
    contract_ref, contract_entity = _resolve_composite_contract_coordinates(config)
    (
        _resolved_contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    ) = resolve_contract_identity(
        provider="composite",
        entity=contract_entity,
        strict=effective_required_profile in STRICT_PERSISTENCE_PROFILES,
    )
    pipeline_version = getattr(config, "version", "") or ""
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
    return (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        dq_contract_compatibility_hash,
        contract_ref,
        contract_entity,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
        pipeline_version,
        effective_required_profile,
    )


def _build_composite_control_plane_manifest(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    effective_config_artifact_id: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
    contract_ref: str,
    contract_entity: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    pipeline_version: str | None,
    required_persistence_profile: str,
) -> RunManifest:
    """Create manifest for composite control plane."""
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(infra_context.settings, "run_manifest"),
        metrics=infra_context.metrics,
    )
    return RunManifestService(
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
            contract_schema_hash=contract_schema_hash,
            dq_policy_ref=dq_policy_ref,
            rule_bundle_version=rule_bundle_version,
            pipeline_version=pipeline_version,
            entity=contract_entity,
            required_persistence_profile=required_persistence_profile,
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
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        dq_contract_compatibility_hash,
        contract_ref,
        contract_entity,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
        pipeline_version,
        required_persistence_profile,
    ) = _build_composite_control_plane_config_artifacts(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
    )
    manifest = _build_composite_control_plane_manifest(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        contract_ref=contract_ref,
        contract_entity=contract_entity,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        pipeline_version=pipeline_version,
        required_persistence_profile=required_persistence_profile,
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
        config_hash=resolved_config_hash or None,
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
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    pipeline_version: str | None,
    entity: str,
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
        entity=entity,
        launch_context=build_composite_launch_context_snapshot(
            config,
            runtime,
            required_persistence_profile=required_persistence_profile,
        ),
        runtime_config=build_composite_runtime_config_snapshot(runtime),
        resolved_config=build_composite_resolved_config_snapshot(config),
        source_refs=source_refs,
        planned_artifacts=build_composite_planned_artifacts(config),
        pipeline_version=pipeline_version,
        git_commit=code_revision.git_commit,
        source_revision_state=code_revision.source_revision_state,
        dependency_lock_hash=dependency_lock_hash,
        config_hash=resolved_config_hash or None,
        resolved_config_hash=resolved_config_hash or None,
        effective_config_hash=effective_config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash or None,
        effective_config_artifact_id=effective_config_artifact_id or None,
        replay_capability=replay_capability,
    )


def _resolve_composite_contract_coordinates(
    config: CompositeConfig,
) -> tuple[str, str]:
    """Resolve canonical dotted contract identity for one composite pipeline."""
    pipeline_name = str(getattr(config, "name", "") or "").strip()
    if not pipeline_name:
        raise RuntimeError("Composite config requires a non-empty name")
    entity = (
        pipeline_name.removeprefix("composite_")
        if pipeline_name.startswith("composite_")
        else pipeline_name
    )
    entity = entity.strip()
    if not entity:
        raise RuntimeError(
            f"Composite config name '{pipeline_name}' does not resolve a contract entity"
        )
    return f"composite.{entity}", entity
