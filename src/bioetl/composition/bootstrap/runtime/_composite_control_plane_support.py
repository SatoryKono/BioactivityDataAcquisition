"""Internal helpers for composite runtime control-plane bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.composition.occurrence_identity import create_runtime_occurrence_id
from bioetl.composition.runtime_builders._run_manifest_refs import (
    control_plane_root as _shared_control_plane_root,
)
from bioetl.composition.snapshot_serialization import (
    to_serializable_mapping as _shared_to_serializable_mapping,
)
from bioetl.domain.control_plane import RunSourceRef
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import FileRunLedgerStore

if TYPE_CHECKING:
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config.settings_api import Settings


def build_run_ledger_service(
    *,
    manifest_id: str,
    ledger_enabled: bool,
    infra_context: CompositeInfrastructureContext,
    pipeline_name: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_ref: str,
    contract_version: str | None,
) -> RunLedgerService | None:
    """Create composite run-ledger service when feature flag allows it."""
    if not ledger_enabled:
        return None
    return RunLedgerService(
        ledger_port=FileRunLedgerStore(
            base_path=control_plane_root(infra_context.settings, "run_ledger"),
            metrics=infra_context.metrics,
        ),
        manifest_id=manifest_id,
        run_id=coerce_run_id(infra_context.run_id),
        pipeline_name=pipeline_name,
        provider="composite",
        entity=pipeline_name,
        run_type=RunType.INCREMENTAL.value,
        resolved_config_hash=resolved_config_hash or None,
        effective_config_hash=effective_config_hash or None,
        contract_ref=contract_ref,
        contract_version=contract_version or None,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash or None,
        effective_config_artifact_id=effective_config_artifact_id or None,
        composite_run_id=infra_context.run_id,
        _entry_id_factory=lambda: create_runtime_occurrence_id(
            "composite_run_ledger_entry"
        ),
        _occurred_at_factory=resolve_runtime_clock(infra_context.clock).now,
    )


def coerce_run_id(run_id: str) -> RunID:
    """Convert composite runtime run_id string into canonical RunID type."""
    return RunID(UUID(run_id))


def compute_composite_input_snapshot_fingerprint(
    source_refs: tuple[RunSourceRef, ...],
) -> str | None:
    """Return a deterministic fingerprint for composite cached-Bronze inputs."""
    snapshot_ids = sorted(
        snapshot.snapshot_id
        for source_ref in source_refs
        for snapshot in source_ref.input_snapshots
    )
    return compute_input_snapshot_identity_fingerprint(snapshot_ids)


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _shared_control_plane_root(settings, leaf)


def normalize_object(value: object) -> dict[str, object]:
    """Convert dataclasses/models into stable JSON-safe mappings."""
    return _shared_to_serializable_mapping(value)


def bind_manifest_logger(logger: LoggerPort, manifest_id: str | None) -> LoggerPort:
    """Bind ``manifest_id`` into logger context when supported."""
    if manifest_id is None:
        return logger
    bind = getattr(logger, "bind", None)
    if not callable(bind):
        return logger
    rebound = bind(manifest_id=manifest_id)
    return cast("LoggerPort", rebound)
