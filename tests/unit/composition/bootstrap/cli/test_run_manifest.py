# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for run-manifest CLI bootstrap wiring."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from bioetl.composition.bootstrap.cli import run_manifest


pytestmark = pytest.mark.unit


class _CaptureService:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


def _patch_control_plane_stores(monkeypatch: pytest.MonkeyPatch) -> tuple[object, ...]:
    stores = tuple(object() for _ in range(4))
    monkeypatch.setattr(run_manifest, "get_settings", lambda: mock.sentinel.settings)
    monkeypatch.setattr(
        run_manifest, "create_metrics", lambda settings: mock.sentinel.metrics
    )
    monkeypatch.setattr(
        run_manifest,
        "create_run_manifest_store",
        lambda *, settings, metrics: stores[0],
    )
    monkeypatch.setattr(
        run_manifest,
        "create_run_ledger_store",
        lambda *, settings, metrics: stores[1],
    )
    monkeypatch.setattr(
        run_manifest,
        "create_effective_config_artifact_store",
        lambda *, settings: stores[2],
    )
    monkeypatch.setattr(
        run_manifest,
        "create_historical_replay_universe_store",
        lambda *, settings: stores[3],
    )
    return stores


def test_create_control_plane_stores_uses_settings_and_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stores = _patch_control_plane_stores(monkeypatch)

    assert run_manifest._create_control_plane_stores() == stores


def test_run_manifest_bootstrap_wires_manifest_and_diff_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stores = _patch_control_plane_stores(monkeypatch)
    monkeypatch.setattr(run_manifest, "RunManifestInspectionService", _CaptureService)
    monkeypatch.setattr(run_manifest, "ForensicRunDiffService", _CaptureService)
    monkeypatch.setattr(
        run_manifest,
        "FileArtifactByteComparisonAdapter",
        lambda: mock.sentinel.byte_comparator,
    )

    manifest_service = run_manifest.bootstrap_run_manifest_service()
    assert manifest_service.kwargs == {
        "manifest_port": stores[0],
        "ledger_port": stores[1],
        "effective_config_artifact_port": stores[2],
        "historical_replay_universe_report_loader": stores[3],
    }

    diff_service = run_manifest.bootstrap_forensic_run_diff_service()
    assert diff_service.kwargs["manifest_port"] is stores[0]
    assert diff_service.kwargs["ledger_port"] is stores[1]
    assert (
        diff_service.kwargs["artifact_byte_comparison_port"]
        is mock.sentinel.byte_comparator
    )
    nested = diff_service.kwargs["inspection_service_factory"]()
    assert nested.kwargs["manifest_port"] is stores[0]
    assert nested.kwargs["historical_replay_universe_report_loader"] is stores[3]


def test_historical_replay_bootstrap_wires_shared_corpus_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stores = _patch_control_plane_stores(monkeypatch)
    monkeypatch.setattr(
        run_manifest, "HistoricalReplayCertificationService", _CaptureService
    )
    monkeypatch.setattr(run_manifest, "HistoricalReplayCorpusService", _CaptureService)
    monkeypatch.setattr(run_manifest, "HistoricalReplayClosureService", _CaptureService)
    monkeypatch.setattr(
        run_manifest, "HistoricalReplayUniverseService", _CaptureService
    )
    monkeypatch.setattr(
        run_manifest,
        "create_runtime_occurrence_id",
        lambda prefix: f"{prefix}:id",
    )

    corpus_service = run_manifest.bootstrap_historical_replay_corpus_service()
    certification_service = corpus_service.kwargs["certification_service"]
    assert corpus_service.kwargs["manifest_port"] is stores[0]
    assert corpus_service.kwargs["ledger_port"] is stores[1]
    assert certification_service.kwargs["entry_id_factory"]() == (
        "historical_replay_certification_ledger_entry:id"
    )

    closure_service = run_manifest.bootstrap_historical_replay_closure_service()
    universe_service = run_manifest.bootstrap_historical_replay_universe_service()
    assert isinstance(closure_service.kwargs["corpus_service"], _CaptureService)
    assert isinstance(universe_service.kwargs["corpus_service"], _CaptureService)
    assert closure_service.kwargs["now_factory"] is run_manifest.current_utc_time
    assert universe_service.kwargs["now_factory"] is run_manifest.current_utc_time


def test_historical_replay_report_persistence_uses_composition_stores(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    closure_path = tmp_path / "closure.json"
    universe_path = tmp_path / "universe.json"
    closure_store = SimpleNamespace(save=mock.Mock(return_value=closure_path))
    universe_store = SimpleNamespace(save=mock.Mock(return_value=universe_path))
    monkeypatch.setattr(run_manifest, "get_settings", lambda: mock.sentinel.settings)
    monkeypatch.setattr(
        run_manifest,
        "create_historical_replay_closure_store",
        lambda *, settings: closure_store,
    )
    monkeypatch.setattr(
        run_manifest,
        "create_historical_replay_universe_store",
        lambda *, settings: universe_store,
    )

    assert (
        run_manifest.persist_historical_replay_closure_report(mock.sentinel.report)
        == closure_path
    )
    assert (
        run_manifest.persist_historical_replay_universe_report(mock.sentinel.report)
        == universe_path
    )
    closure_store.save.assert_called_once_with(mock.sentinel.report)
    universe_store.save.assert_called_once_with(mock.sentinel.report)
