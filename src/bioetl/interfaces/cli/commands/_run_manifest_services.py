"""Lazy service getters for run-manifest CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.forensic import (
        ForensicRunDiffService,
    )
    from bioetl.application.services.control_plane.manifest.inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.control_plane.replay.historical_closure_service import (
        HistoricalReplayClosureService,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_service import (
        HistoricalReplayCorpusService,
    )
    from bioetl.application.services.control_plane.replay.historical_universe_service import (
        HistoricalReplayUniverseService,
    )


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest inspection service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_run_manifest_service as _impl,
    )

    return _impl()


def get_forensic_run_diff_service() -> ForensicRunDiffService:
    """Load the forensic run-diff service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_forensic_run_diff_service as _impl,
    )

    return _impl()


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusService:
    """Load retained-corpus replay workflows through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_historical_replay_corpus_service as _impl,
    )

    return _impl()


def get_historical_replay_closure_service() -> HistoricalReplayClosureService:
    """Load retained-corpus closure workflows through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_historical_replay_closure_service as _impl,
    )

    return _impl()


def get_historical_replay_universe_service() -> HistoricalReplayUniverseService:
    """Load full-universe historical replay workflows through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_historical_replay_universe_service as _impl,
    )

    return _impl()
