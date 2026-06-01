"""Historical replay and replay-bundle application service seam."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.replay.bundle_descriptor_service import (
        RunReplayBundleDescriptorRecord as RunReplayBundleDescriptorRecord,
    )
    from bioetl.application.services.control_plane.replay.bundle_descriptor_service import (
        build_run_replay_bundle_descriptor as build_run_replay_bundle_descriptor,
    )
    from bioetl.application.services.control_plane.replay.historical_certification_service import (
        HistoricalReplayCertificationResult as HistoricalReplayCertificationResult,
    )
    from bioetl.application.services.control_plane.replay.historical_certification_service import (
        HistoricalReplayCertificationService as HistoricalReplayCertificationService,
    )
    from bioetl.application.services.control_plane.replay.historical_certification_service import (
        HistoricalReplaySnapshotCertification as HistoricalReplaySnapshotCertification,
    )
    from bioetl.application.services.control_plane.replay.historical_closure_models import (
        HistoricalReplayClosureReportRecord as HistoricalReplayClosureReportRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_closure_models import (
        HistoricalReplayResidualDispositionRecord as HistoricalReplayResidualDispositionRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_closure_service import (
        HistoricalReplayClosureService as HistoricalReplayClosureService,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_models import (
        HistoricalReplayBulkCertificationRecord as HistoricalReplayBulkCertificationRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_models import (
        HistoricalReplayBulkCertificationResult as HistoricalReplayBulkCertificationResult,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_models import (
        HistoricalReplayBulkCertificationSpec as HistoricalReplayBulkCertificationSpec,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_models import (
        HistoricalReplayCertifiabilityInventory as HistoricalReplayCertifiabilityInventory,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_models import (
        HistoricalReplayCertifiabilityRecord as HistoricalReplayCertifiabilityRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_service import (
        HistoricalReplayCorpusService as HistoricalReplayCorpusService,
    )
    from bioetl.application.services.control_plane.replay.historical_universe_service import (
        HistoricalReplayUniverseClosureReportRecord as HistoricalReplayUniverseClosureReportRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_universe_service import (
        HistoricalReplayUniverseExternalRecord as HistoricalReplayUniverseExternalRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_universe_service import (
        HistoricalReplayUniverseInventorySnapshot as HistoricalReplayUniverseInventorySnapshot,
    )
    from bioetl.application.services.control_plane.replay.historical_universe_service import (
        HistoricalReplayUniverseRecord as HistoricalReplayUniverseRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_universe_service import (
        HistoricalReplayUniverseService as HistoricalReplayUniverseService,
    )

_PUBLIC_EXPORTS = {
    "HistoricalReplayBulkCertificationRecord": (
        "bioetl.application.services.control_plane.replay.historical_corpus_models"
    ),
    "HistoricalReplayBulkCertificationResult": (
        "bioetl.application.services.control_plane.replay.historical_corpus_models"
    ),
    "HistoricalReplayBulkCertificationSpec": (
        "bioetl.application.services.control_plane.replay.historical_corpus_models"
    ),
    "HistoricalReplayCertifiabilityInventory": (
        "bioetl.application.services.control_plane.replay.historical_corpus_models"
    ),
    "HistoricalReplayCertifiabilityRecord": (
        "bioetl.application.services.control_plane.replay.historical_corpus_models"
    ),
    "HistoricalReplayCertificationResult": (
        "bioetl.application.services.control_plane.replay.historical_certification_service"
    ),
    "HistoricalReplayCertificationService": (
        "bioetl.application.services.control_plane.replay.historical_certification_service"
    ),
    "HistoricalReplayClosureReportRecord": (
        "bioetl.application.services.control_plane.replay.historical_closure_models"
    ),
    "HistoricalReplayClosureService": (
        "bioetl.application.services.control_plane.replay.historical_closure_service"
    ),
    "HistoricalReplayCorpusService": (
        "bioetl.application.services.control_plane.replay.historical_corpus_service"
    ),
    "HistoricalReplayResidualDispositionRecord": (
        "bioetl.application.services.control_plane.replay.historical_closure_models"
    ),
    "HistoricalReplaySnapshotCertification": (
        "bioetl.application.services.control_plane.replay.historical_certification_service"
    ),
    "HistoricalReplayUniverseClosureReportRecord": (
        "bioetl.application.services.control_plane.replay.historical_universe_service"
    ),
    "HistoricalReplayUniverseExternalRecord": (
        "bioetl.application.services.control_plane.replay.historical_universe_service"
    ),
    "HistoricalReplayUniverseInventorySnapshot": (
        "bioetl.application.services.control_plane.replay.historical_universe_service"
    ),
    "HistoricalReplayUniverseRecord": (
        "bioetl.application.services.control_plane.replay.historical_universe_service"
    ),
    "HistoricalReplayUniverseService": (
        "bioetl.application.services.control_plane.replay.historical_universe_service"
    ),
    "RunReplayBundleDescriptorRecord": (
        "bioetl.application.services.control_plane.replay.bundle_descriptor_service"
    ),
    "build_run_replay_bundle_descriptor": (
        "bioetl.application.services.control_plane.replay.bundle_descriptor_service"
    ),
}

__all__ = list(_PUBLIC_EXPORTS)


def __getattr__(name: str) -> object:
    """Resolve replay exports lazily to avoid heavy import cycles."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
