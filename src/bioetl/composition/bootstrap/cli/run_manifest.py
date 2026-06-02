"""Bootstrap functions for run-manifest CLI operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.control_plane.forensic_diff_service import (
    ForensicRunDiffService,
)
from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationService,
)
from bioetl.application.services.control_plane.replay.historical_closure_service import (
    HistoricalReplayClosureReport,
    HistoricalReplayClosureService,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_universe_service import (
    HistoricalReplayUniverseClosureReport,
    HistoricalReplayUniverseService,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.composition.occurrence_identity import create_runtime_occurrence_id
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.control_plane import (
    FileArtifactByteComparisonAdapter,
    FileEffectiveConfigArtifactStore,
    FileHistoricalReplayClosureStore,
    FileHistoricalReplayUniverseStore,
    FileRunLedgerStore,
    FileRunManifestStore,
)

__all__ = [
    "bootstrap_forensic_run_diff_service",
    "bootstrap_historical_replay_closure_service",
    "bootstrap_historical_replay_corpus_service",
    "bootstrap_historical_replay_universe_service",
    "bootstrap_run_manifest_service",
    "persist_historical_replay_closure_report",
    "persist_historical_replay_universe_report",
]


def _create_control_plane_stores() -> tuple[
    FileRunManifestStore,
    FileRunLedgerStore,
    FileEffectiveConfigArtifactStore,
    FileHistoricalReplayUniverseStore,
]:
    """Create file-backed control-plane stores for CLI inspection services."""
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return (
        FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
        FileRunLedgerStore(
            base_path=output_root / "run_ledger",
            metrics=metrics,
        ),
        FileEffectiveConfigArtifactStore(
            base_path=output_root / "effective_config",
        ),
        FileHistoricalReplayUniverseStore(
            base_path=output_root / "historical_replay_universe"
        ),
    )


def bootstrap_run_manifest_service() -> RunManifestInspectionService:
    """Bootstrap manifest/ledger inspection service for CLI commands."""
    manifest_store, ledger_store, effective_config_store, universe_store = (
        _create_control_plane_stores()
    )
    return RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        effective_config_artifact_port=effective_config_store,
        historical_replay_universe_report_loader=universe_store,
    )


def bootstrap_forensic_run_diff_service() -> ForensicRunDiffService:
    """Bootstrap unified forensic run-diff service for CLI diagnostics."""
    manifest_store, ledger_store, effective_config_store, universe_store = (
        _create_control_plane_stores()
    )
    return ForensicRunDiffService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        artifact_byte_comparison_port=FileArtifactByteComparisonAdapter(),
        inspection_service_factory=lambda: RunManifestInspectionService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            effective_config_artifact_port=effective_config_store,
            historical_replay_universe_report_loader=universe_store,
        ),
    )


def bootstrap_historical_replay_corpus_service() -> HistoricalReplayCorpusService:
    """Bootstrap retained-corpus historical replay workflows for CLI use."""
    manifest_store, ledger_store, _effective_config_store, _universe_store = (
        _create_control_plane_stores()
    )
    return HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            entry_id_factory=lambda: create_runtime_occurrence_id(
                "historical_replay_certification_ledger_entry"
            ),
        ),
    )


def bootstrap_historical_replay_closure_service() -> HistoricalReplayClosureService:
    """Bootstrap retained-corpus closure reporting for CLI use."""
    manifest_store, ledger_store, _effective_config_store, _universe_store = (
        _create_control_plane_stores()
    )
    corpus_service = HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            entry_id_factory=lambda: create_runtime_occurrence_id(
                "historical_replay_certification_ledger_entry"
            ),
        ),
    )
    return HistoricalReplayClosureService(
        corpus_service=corpus_service,
    )


def bootstrap_historical_replay_universe_service() -> HistoricalReplayUniverseService:
    """Bootstrap full-universe historical replay workflows for CLI use."""
    manifest_store, ledger_store, _effective_config_store, _universe_store = (
        _create_control_plane_stores()
    )
    corpus_service = HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            entry_id_factory=lambda: create_runtime_occurrence_id(
                "historical_replay_certification_ledger_entry"
            ),
        ),
    )
    return HistoricalReplayUniverseService(
        corpus_service=corpus_service,
    )


def persist_historical_replay_closure_report(
    report: HistoricalReplayClosureReport,
) -> Path:
    """Persist one historical replay closure report via composition-owned wiring."""
    settings = get_settings()
    output_root = Path(settings.data_dir) / "output" / "control"
    store = FileHistoricalReplayClosureStore(
        base_path=output_root / "historical_replay_closure"
    )
    return store.save(report)


def persist_historical_replay_universe_report(
    report: HistoricalReplayUniverseClosureReport,
) -> Path:
    """Persist one historical replay universe report via composition-owned wiring."""
    settings = get_settings()
    output_root = Path(settings.data_dir) / "output" / "control"
    store = FileHistoricalReplayUniverseStore(
        base_path=output_root / "historical_replay_universe"
    )
    return store.save(report)
