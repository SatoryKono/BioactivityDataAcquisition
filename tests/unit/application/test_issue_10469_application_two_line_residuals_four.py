"""Behavior coverage for the remaining application two-line residuals in #10469."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.merger_io_mixin import MergeIOMixin
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationSpec,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_identity_models import (
    HistoricalReplayUniverseExternalRecord,
    build_historical_certified_identity_payload_from_record,
)
from bioetl.application.services.dq._checks_basic import _extract_freshness_timestamp
from bioetl.application.services.quality import (
    _quarantine_service_filtered_helpers as filtered,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_merge_io_returns_unchanged_frames_without_joinable_inputs() -> None:
    host = MergeIOMixin()
    frame = pl.DataFrame({"id": [1]})
    dependencies = [SimpleNamespace(pipeline="chembl_target")]
    assert (
        await host._apply_dependency_joins_if_needed(
            frame,
            {"chembl_assay": frame},
            dependencies,  # type: ignore[arg-type]
            "chembl_assay",
        )
        is frame
    )

    host._cross_validator = MagicMock()
    output, stats, rows = host._run_cross_validation(
        frame,
        [SimpleNamespace(pipeline="chembl_target")],  # type: ignore[list-item]
        {"chembl_assay": frame},
        "chembl_assay",
    )
    assert output is frame
    assert stats is None
    assert rows == []


def test_preflight_ignores_pipeline_names_without_provider_entity_separator() -> None:
    service = CompositePreflightValidationService(MagicMock())
    sources = {"kept"}
    service._add_pipeline_source_tokens(sources, "invalid")
    assert sources == {"kept"}


def test_historical_bulk_validation_names_missing_manifest_and_inventory() -> None:
    service = HistoricalReplayCorpusService(MagicMock(), MagicMock(), MagicMock())
    spec = HistoricalReplayBulkCertificationSpec(
        manifest_id="manifest-1", certifications=()
    )
    with pytest.raises(ValueError, match="could not find manifest"):
        service.validate_bulk_manifests(
            (spec,), manifest_by_id={}, status_by_manifest_id={}
        )
    with pytest.raises(ValueError, match="inventory is missing"):
        service.validate_bulk_manifests(
            (spec,),
            manifest_by_id={"manifest-1": MagicMock()},
            status_by_manifest_id={},
        )


def _external_identity() -> HistoricalReplayUniverseExternalRecord:
    return HistoricalReplayUniverseExternalRecord(
        manifest_id="manifest-1",
        run_id="run-1",
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        execution_context="source",
        certification_status="certified",
        replay_occurrence_kind="exact",
    )


def test_historical_external_identity_serializes_and_rejects_core_override() -> None:
    record = _external_identity()
    assert record.to_dict()["evidence_residency"] == "archived"
    with pytest.raises(ValueError, match="cannot override certified identity"):
        build_historical_certified_identity_payload_from_record(
            record, certification_status="changed"
        )


class _BrokenColumn:
    def max(self) -> object:
        raise RuntimeError("broken column")


class _BrokenFrame:
    columns = ["updated_at"]

    def __getitem__(self, _name: str) -> _BrokenColumn:
        return _BrokenColumn()


def test_freshness_timestamp_skips_unreadable_columns() -> None:
    assert _extract_freshness_timestamp(_BrokenFrame()) is None  # type: ignore[arg-type]


def test_filtered_helpers_handle_unselectable_manifest_and_missing_show(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = SimpleNamespace(
        pipeline_name="chembl_activity", run_type="incremental", run_id="run-1"
    )
    service = SimpleNamespace(
        manifest_port=SimpleNamespace(list_all=lambda: (manifest,)), ledger_port=None
    )
    monkeypatch.setattr(filtered, "_pick_latest_scope_manifest", lambda **_kw: None)
    assert (
        filtered._resolve_latest_scope_run_id(
            pipeline="chembl_activity", run_type=None, run_manifest_service=service
        )
        is None
    )
    assert (
        filtered._resolve_bronze_for_run(
            "run-1",
            list_entries_by_run_id=None,
            run_manifest_service=SimpleNamespace(),
        )
        is None
    )
