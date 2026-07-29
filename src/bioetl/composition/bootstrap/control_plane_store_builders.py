# pyright: reportImportCycles=false
# Import cycle residual (PD4).
# Import cycle residual tracked in allowlist (PD3).
"""Canonical composition-owned builders for control-plane file stores."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders import control_plane_root
from bioetl.infrastructure.control_plane import (
    FileEffectiveConfigArtifactStore,
    FileHistoricalReplayClosureStore,
    FileHistoricalReplayUniverseStore,
    FileRunLedgerStore,
    FileRunManifestStore,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.infrastructure.config.settings_api import Settings


def create_run_manifest_store(
    *,
    settings: Settings,
    metrics: MetricsPort | None = None,
) -> FileRunManifestStore:
    """Create the canonical file-backed run-manifest store."""
    return FileRunManifestStore(
        base_path=control_plane_root(settings, "run_manifest"),
        metrics=metrics,
    )


def create_run_ledger_store(
    *,
    settings: Settings,
    metrics: MetricsPort | None = None,
) -> FileRunLedgerStore:
    """Create the canonical file-backed run-ledger store."""
    return FileRunLedgerStore(
        base_path=control_plane_root(settings, "run_ledger"),
        metrics=metrics,
    )


def create_effective_config_artifact_store(
    *,
    settings: Settings,
) -> FileEffectiveConfigArtifactStore:
    """Create the canonical file-backed effective-config artifact store."""
    return FileEffectiveConfigArtifactStore(
        base_path=control_plane_root(settings, "effective_config")
    )


def create_historical_replay_closure_store(
    *,
    settings: Settings,
) -> FileHistoricalReplayClosureStore:
    """Create the canonical file-backed historical replay closure store."""
    return FileHistoricalReplayClosureStore(
        base_path=control_plane_root(settings, "historical_replay_closure")
    )


def create_historical_replay_universe_store(
    *,
    settings: Settings,
) -> FileHistoricalReplayUniverseStore:
    """Create the canonical file-backed historical replay universe store."""
    return FileHistoricalReplayUniverseStore(
        base_path=control_plane_root(settings, "historical_replay_universe")
    )


__all__ = [
    "create_effective_config_artifact_store",
    "create_historical_replay_closure_store",
    "create_historical_replay_universe_store",
    "create_run_ledger_store",
    "create_run_manifest_store",
]
