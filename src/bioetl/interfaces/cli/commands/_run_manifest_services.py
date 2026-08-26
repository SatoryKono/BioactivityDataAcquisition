"""Lazy service getters for run-manifest CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.ports.control_plane import (
        ForensicRunDiffServiceProtocol,
        HistoricalReplayClosureServiceProtocol,
        HistoricalReplayCorpusServiceProtocol,
        HistoricalReplayUniverseServiceProtocol,
        RunManifestInspectionServiceProtocol,
    )


def get_run_manifest_service() -> RunManifestInspectionServiceProtocol:
    """Load the run-manifest inspection service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_run_manifest_service as _impl,
    )

    return _impl()


def get_forensic_run_diff_service() -> ForensicRunDiffServiceProtocol:
    """Load the forensic run-diff service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_forensic_run_diff_service as _impl,
    )

    return _impl()


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusServiceProtocol:
    """Load retained-corpus replay workflows through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_historical_replay_corpus_service as _impl,
    )

    return _impl()


def get_historical_replay_closure_service() -> HistoricalReplayClosureServiceProtocol:
    """Load retained-corpus closure workflows through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_historical_replay_closure_service as _impl,
    )

    return _impl()


def get_historical_replay_universe_service() -> HistoricalReplayUniverseServiceProtocol:
    """Load full-universe historical replay workflows through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_historical_replay_universe_service as _impl,
    )

    return _impl()
