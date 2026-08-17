"""Regression vectors for SHA-bound module coverage currentness (#8775)."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.core.batch_executor_state_flow import process_stateful_batch
from bioetl.application.services.control_plane.effective_config.service import (
    EffectiveConfigService,
)
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestService,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support import (
    _refresh_replay_summary_from_materialized_snapshots,
)
from bioetl.application.services.control_plane import replay
from bioetl.application.services.control_plane.replay import (
    historical_corpus_service,
)
from bioetl.application.services.control_plane.replay._historical_certification_upstream import (
    validate_upstream_presence,
)
from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    _suggested_disposition,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationRecord,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_aggregation import (
    evaluate_threshold_failures,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core import (
    score_checkpoint_safety,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_extended import (
    score_replay_readiness,
)
from bioetl.application.services.run_reports.query import _rm_tree


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_batch_state_flow_skips_disallowed_process_command() -> None:
    assembled_state = object()
    host = SimpleNamespace(
        _fsm=MagicMock(
            advance=MagicMock(
                return_value=SimpleNamespace(
                    new_state=assembled_state, commands=frozenset()
                )
            )
        ),
        _fsm_state=object(),
    )

    await process_stateful_batch(host, [], 0)

    host._fsm.advance.assert_called_once()
    assert host._fsm_state is assembled_state


def test_replay_refresh_returns_summary_without_snapshot_payloads() -> None:
    summary: dict[str, object] = {"input_snapshots": ["not-a-snapshot"]}

    assert (
        _refresh_replay_summary_from_materialized_snapshots(
            manifest=object(),  # type: ignore[arg-type]
            summary=summary,
        )
        is summary
    )


def test_historical_diagnostics_rejects_non_mapping_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostics = SimpleNamespace(build_diagnostics_summary=lambda *_a, **_k: [])
    monkeypatch.setattr(
        historical_corpus_service,
        "import_module",
        lambda _name: diagnostics,
    )

    with pytest.raises(TypeError, match="expected mapping"):
        historical_corpus_service._build_diagnostics_summary(object())


def test_score_card_residual_failure_branches_are_explicit() -> None:
    failures = evaluate_threshold_failures(
        thresholds={"identity": 8},
        category_scores={},
    )
    checkpoint = score_checkpoint_safety(
        {
            "required_persistence_profile": "replay_ready",
            "resume_contract": {
                "applied_checkpoint_compatibility_policy": "warn",
                "resume_requested": False,
            },
        }
    )
    replay = score_replay_readiness(
        {
            "exact_replay_eligible": True,
            "replay_mode": "rebuild_only",
            "artifact_publication_closure": "closed",
        }
    )

    assert failures[0]["reason"] == "category_score_missing"
    assert "checkpoint_policy_below_profile_minimum" in checkpoint.blockers
    assert "rebuild_only_replay_mode" in replay.blockers


def test_deduplication_handles_duplicate_key_only_frames() -> None:
    service = EnricherDeduplicatorService(MagicMock())

    result = service.deduplicate(pl.DataFrame({"id": ["1", "1"]}), ["id"], "key-only")

    assert result.to_dicts() == [{"id": "1"}]


def test_transformer_span_compatibility_delegate_is_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.application.core.base_transformer import BaseTransformer

    execution_mixin = import_module(
        "bioetl.application.core.base_transformer_execution_mixin"
    )

    sentinel = object()
    monkeypatch.setattr(
        execution_mixin,
        "start_transform_span",
        lambda *_args: sentinel,
    )

    assert (
        BaseTransformer._start_transform_span(
            object(),
            object(),
            0,  # type: ignore[arg-type]
        )
        is sentinel
    )


def test_effective_config_convenience_method_normalizes_missing_collections() -> None:
    captured: dict[str, object] = {}

    def create_effective_config_artifact(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    owner = SimpleNamespace(
        create_effective_config_artifact=create_effective_config_artifact
    )
    EffectiveConfigService.create_artifact_from_pipeline_config(
        owner,  # type: ignore[arg-type]
        "chembl_activity",
        "source",
        {"source": "chembl"},
    )

    assert captured["runtime_overrides"] == {}
    assert captured["source_refs"] == []


def test_manifest_persistence_guard_rejects_run_id_mismatch() -> None:
    manifest = SimpleNamespace(manifest_id="manifest-1", run_id="run-1")
    persisted = SimpleNamespace(manifest_id="manifest-1", run_id="run-2")
    owner = SimpleNamespace(
        manifest_port=SimpleNamespace(
            get=lambda _manifest_id: persisted,
            get_by_run_id=lambda _run_id: manifest,
        )
    )

    with pytest.raises(RuntimeError, match="persisted manifest run_id"):
        RunManifestService._assert_manifest_persisted(  # type: ignore[arg-type]
            owner, manifest
        )


def test_replay_module_introspection_and_missing_attribute_are_explicit() -> None:
    assert "HistoricalReplayCorpusService" in replay.__dir__()
    with pytest.raises(AttributeError, match="has no attribute"):
        replay.__getattr__("definitely_missing")


def test_historical_certification_rejects_missing_upstream_identity() -> None:
    with pytest.raises(ValueError, match="requires upstream_run_id"):
        validate_upstream_presence(
            SimpleNamespace(upstream_manifest_id=None, upstream_run_id=None)  # type: ignore[arg-type]
        )


def test_historical_closure_models_render_residual_paths() -> None:
    record = HistoricalReplayBulkCertificationRecord(
        manifest_id="manifest-1",
        run_id="run-1",
        certification_scope=None,
        status="certified",
        replay_occurrence_kind="ordinary_live_capture",
        broader_historical_exact_replay_state="certified",
    )

    assert record.to_dict()["manifest_id"] == "manifest-1"
    assert (
        _suggested_disposition(
            SimpleNamespace(  # type: ignore[arg-type]
                certification_status="outside_certified_historical_scope"
            )
        )
        == "outside_universal_claim_scope"
    )


def test_report_tree_removal_unlinks_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    _rm_tree(link)

    assert not link.exists()
    assert target.is_dir()
