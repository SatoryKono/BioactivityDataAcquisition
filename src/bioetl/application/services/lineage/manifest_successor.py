"""Live-context adoption after a run manifest successor is published."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest


class _SuccessorHost(Protocol):
    """Runner fields the successor observer is allowed to replace."""

    _contract_evidence_context: object | None
    _services: object


class _SuccessorService(Protocol):
    """Ledger service slot that receives the successor observer."""

    manifest_successor_observer: object | None


def bind_manifest_successor_observer(host: object, service: object) -> None:
    """Register a successor observer that updates one runner's live context."""
    runner = cast("_SuccessorHost", host)
    ledger = cast("_SuccessorService", service)

    def _adopt(manifest: RunManifest) -> None:
        runner._contract_evidence_context = adopt_live_manifest_successor(
            launch_context=runner._contract_evidence_context,
            services=runner._services,
            manifest=manifest,
        )

    ledger.manifest_successor_observer = _adopt


def adopt_live_manifest_successor(
    *,
    launch_context: object | None,
    services: object,
    manifest: RunManifest,
) -> object | None:
    """Rebind mutable holders that still name the predecessor manifest.

    Frozen launch context and the metadata coordinator are replaced so later
    sidecars and Silver/Gold lineage use the successor identity. Composite
    checkpoint replay reads the successor ledger chain separately.
    """
    updated_launch = launch_context
    if (
        launch_context is not None
        and is_dataclass(launch_context)
        and not isinstance(launch_context, type)
        and hasattr(launch_context, "manifest_id")
    ):
        updates: dict[str, object] = {"manifest_id": manifest.manifest_id}
        if hasattr(launch_context, "execution_fingerprint"):
            updates["execution_fingerprint"] = manifest.execution_fingerprint
        updated_launch = replace(launch_context, **updates)
    coordinator = getattr(services, "metadata_coordinator", None)
    adopt = getattr(coordinator, "adopt_manifest_successor", None)
    if callable(adopt):
        adopt(
            manifest_id=manifest.manifest_id,
            execution_fingerprint=manifest.execution_fingerprint,
        )
    return updated_launch
