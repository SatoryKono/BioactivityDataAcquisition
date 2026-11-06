"""Best-effort publication of committed manifests to the dashboard catalog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.composition.control_plane_paths import publish_new_run_manifest_to_live_root
from bioetl.domain.exceptions import InfrastructureError, StorageError

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.domain.control_plane import RunManifest
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "bind_live_root_successor_callback",
    "publish_live_root_without_failing_the_run",
]


def bind_live_root_successor_callback(
    ledger_service: RunLedgerService | None,
    *,
    settings: Settings,
    source_base: Path,
) -> None:
    """Publish a successor only after its ledger rebind has committed."""
    if ledger_service is None:
        return

    def _publish(successor: RunManifest) -> None:
        publish_live_root_without_failing_the_run(
            manifest=successor,
            settings=settings,
            source_base=source_base,
        )

    ledger_service.manifest_successor_callbacks.append(_publish)


def publish_live_root_without_failing_the_run(
    *,
    manifest: RunManifest,
    settings: Settings,
    source_base: Path,
) -> None:
    """Record the extra live catalog without failing a saved mandatory manifest."""
    try:
        publish_new_run_manifest_to_live_root(
            manifest=manifest,
            settings=settings,
            source_base=source_base,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        StorageError,
        InfrastructureError,
    ) as exc:
        record_run_observation(
            "Control Plane",
            verdict="WARN",
            reason="live_root_manifest_publication_failed",
            facts={
                "manifest_id": getattr(manifest, "manifest_id", None),
                "run_id": str(getattr(manifest, "run_id", "")),
                "error_type": type(exc).__name__,
            },
        )
