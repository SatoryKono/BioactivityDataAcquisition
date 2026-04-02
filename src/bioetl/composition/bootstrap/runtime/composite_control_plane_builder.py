"""Control-plane builders for composite runtime bootstrap."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.composition.bootstrap.runtime._composite_control_plane_payloads import (
    build_composite_launch_context_snapshot,
    build_composite_planned_artifacts,
    build_composite_source_refs,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    CompositeControlPlaneBundle,
)
from bioetl.composition.services import compute_config_hash
from bioetl.composition.services.versioning import get_git_commit
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import FileRunLedgerStore, FileRunManifestStore

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.composition.bootstrap.runtime.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bind_manifest_logger",
    "build_composite_control_plane_bundle",
    "resolve_composite_control_plane_flags",
]


def resolve_composite_control_plane_flags(settings: object) -> tuple[bool, bool]:
    """Resolve manifest/ledger feature flags with backwards-compatible defaults."""
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    if not manifest_enabled:
        return False, False
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
    manifest_enabled, ledger_enabled = resolve_composite_control_plane_flags(
        infra_context.settings
    )
    if not manifest_enabled:
        return CompositeControlPlaneBundle()

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
        run_ledger_service=run_ledger_service,
        config_hash=config_hash or None,
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
) -> RunManifestCreateRequest:
    """Build the manifest creation payload for one composite execution."""
    return RunManifestCreateRequest(
        run_id=_coerce_run_id(infra_context.run_id),
        run_type=RunType.INCREMENTAL,
        pipeline_name=config.name,
        provider="composite",
        entity=config.name,
        launch_context=build_composite_launch_context_snapshot(config, runtime),
        runtime_config=_normalize_object(runtime),
        resolved_config=_normalize_object(config),
        source_refs=build_composite_source_refs(config),
        planned_artifacts=build_composite_planned_artifacts(config),
        pipeline_version=contract_version or None,
        git_commit=get_git_commit(),
        config_hash=config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
    )


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
        return compute_config_hash(payload)
    except (TypeError, ValueError):
        return ""


def _coerce_run_id(run_id: str) -> RunID:
    """Convert composite runtime run_id string into canonical RunID type."""
    return RunID(UUID(run_id))


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return Path(getattr(settings, "data_dir", "data")) / "output" / "control" / leaf


def _normalize_object(value: object) -> dict[str, object]:
    """Convert dataclasses/models into stable JSON-safe mappings."""
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json", exclude_none=True)
    elif is_dataclass(value) and not isinstance(value, type):
        payload = asdict(value)
    elif hasattr(value, "__dict__"):
        payload = {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
    else:
        payload = {"value": value}
    normalized = _normalize_value(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Composite control-plane payload must normalize to mapping")
    return normalized


def _normalize_value(value: object) -> object:
    """Normalize nested values into JSON-safe primitives."""
    if isinstance(value, dict):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    return value
