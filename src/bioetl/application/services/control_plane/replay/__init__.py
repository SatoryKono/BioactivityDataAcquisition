# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
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

_BUNDLE_DESCRIPTOR_MODULE = (
    "bioetl.application.services.control_plane.replay.bundle_descriptor_service"
)
_CERTIFICATION_SERVICE_MODULE = (
    "bioetl.application.services.control_plane.replay.historical_certification_service"
)
_CLOSURE_MODELS_MODULE = (
    "bioetl.application.services.control_plane.replay.historical_closure_models"
)
_CLOSURE_SERVICE_MODULE = (
    "bioetl.application.services.control_plane.replay.historical_closure_service"
)
_CORPUS_MODELS_MODULE = (
    "bioetl.application.services.control_plane.replay.historical_corpus_models"
)
_CORPUS_SERVICE_MODULE = (
    "bioetl.application.services.control_plane.replay.historical_corpus_service"
)
_UNIVERSE_SERVICE_MODULE = (
    "bioetl.application.services.control_plane.replay.historical_universe_service"
)

_PUBLIC_EXPORTS = {
    "HistoricalReplayBulkCertificationRecord": _CORPUS_MODELS_MODULE,
    "HistoricalReplayBulkCertificationResult": _CORPUS_MODELS_MODULE,
    "HistoricalReplayBulkCertificationSpec": _CORPUS_MODELS_MODULE,
    "HistoricalReplayCertifiabilityInventory": _CORPUS_MODELS_MODULE,
    "HistoricalReplayCertifiabilityRecord": _CORPUS_MODELS_MODULE,
    "HistoricalReplayCertificationResult": _CERTIFICATION_SERVICE_MODULE,
    "HistoricalReplayCertificationService": _CERTIFICATION_SERVICE_MODULE,
    "HistoricalReplayClosureReportRecord": _CLOSURE_MODELS_MODULE,
    "HistoricalReplayClosureService": _CLOSURE_SERVICE_MODULE,
    "HistoricalReplayCorpusService": _CORPUS_SERVICE_MODULE,
    "HistoricalReplayResidualDispositionRecord": _CLOSURE_MODELS_MODULE,
    "HistoricalReplaySnapshotCertification": _CERTIFICATION_SERVICE_MODULE,
    "HistoricalReplayUniverseClosureReportRecord": _UNIVERSE_SERVICE_MODULE,
    "HistoricalReplayUniverseExternalRecord": _UNIVERSE_SERVICE_MODULE,
    "HistoricalReplayUniverseInventorySnapshot": _UNIVERSE_SERVICE_MODULE,
    "HistoricalReplayUniverseRecord": _UNIVERSE_SERVICE_MODULE,
    "HistoricalReplayUniverseService": _UNIVERSE_SERVICE_MODULE,
    "RunReplayBundleDescriptorRecord": _BUNDLE_DESCRIPTOR_MODULE,
    "build_run_replay_bundle_descriptor": _BUNDLE_DESCRIPTOR_MODULE,
}

__all__ = [*_PUBLIC_EXPORTS]


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
