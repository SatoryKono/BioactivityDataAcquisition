"""Stream B APP: leftover pubmed, inspection, dedup, and batch-write branches."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from xml.etree import ElementTree as ET

import polars as pl
import pytest

from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.core._batch_write_support import (
    _execute_layer_write,
    emit_batch_written,
)
from bioetl.application.pipelines.pubmed import _block_helpers as pubmed
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionCorruptionError,
    RunManifestInspectionService,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    parse_run_id,
)

pytestmark = pytest.mark.unit


def test_pubmed_author_skip_collective_and_month_digits() -> None:
    authors = pubmed.build_authors_with_affiliations(
        [
            {
                "last_name": None,
                "initials": None,
                "fore_name": None,
                "collective_name": None,
            }
        ],
        pii_hasher=None,
    )
    assert authors == []
    hashed = pubmed.build_authors_with_affiliations(
        [
            {
                "last_name": "Doe",
                "initials": None,
                "fore_name": None,
                "collective_name": None,
                "structured_affiliations": [{"text": "Org", "ror_id": None}],
            }
        ],
        pii_hasher=None,
    )
    assert hashed[0]["name_hash"] is None
    assert (
        pubmed._resolve_author_name({"collective_name": "Consortium"}) == "Consortium"
    )
    assert pubmed.parse_month(None, {}) is None
    assert pubmed.parse_month("03", {}) == 3
    month, day = pubmed.parse_month_day(
        ET.Element("PubDate"),
        date_extractor=SimpleNamespace(extract=lambda _n: {}),  # type: ignore[arg-type]
        month_map={},
    )
    assert month is None and day is None


def test_inspection_historical_claim_and_resolve_gaps() -> None:
    loader = SimpleNamespace(
        load_latest_report=lambda: {
            "universal_claim": {"claimed": True},
            "durable_evidence_coverage_claim": {"claimed": False},
            "_artifact_path": "reports/universe.json",
            "governed_full_corpus_gate": {"status": "blocked"},
        }
    )
    port = SimpleNamespace(
        get=lambda _id: None,
        get_by_run_id=lambda _rid: (_ for _ in ()).throw(ValueError("corrupt")),
    )
    svc = RunManifestInspectionService(
        manifest_port=port,  # type: ignore[arg-type]
        historical_replay_universe_report_loader=loader,  # type: ignore[arg-type]
    )
    diagnostics: dict[str, object] = {}
    svc._attach_historical_replay_universe_claim(diagnostics)
    assert diagnostics["historical_replay_universe_durable_evidence_claimed"] is False
    svc._attach_reproducibility_claim_views({"reproducibility_audit_score": "not-dict"})
    run_id = str(uuid4())
    assert parse_run_id(run_id) is not None
    with pytest.raises(RunManifestInspectionCorruptionError):
        svc._resolve_manifest(run_id)
    with pytest.raises(ValueError, match="not found"):
        svc._resolve_manifest("not-a-uuid")


def test_deduplicator_empty_and_missing_keys() -> None:
    service = EnricherDeduplicatorService(logger=MagicMock())
    empty = pl.DataFrame({"id": []})
    assert service._check_duplicates(empty, ["id"]) is False
    df = pl.DataFrame({"id": [1, 1], "value": ["a", "b"]})
    assert service._check_duplicates(df, ["missing"]) is False


@pytest.mark.asyncio
async def test_batch_write_gold_dispatch_and_missing_run() -> None:
    emit_batch_written(
        emitter=MagicMock(),
        run_id=None,
        batch_id="b1",  # type: ignore[arg-type]
        layer="gold",
        record_count=1,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    writer = SimpleNamespace(
        write_gold=AsyncMock(return_value="gold-ok"),
        write_silver=AsyncMock(),
        log_and_track_write_error=MagicMock(),
    )

    async def _span(name: str, operation: object, *_a: object, **_k: object) -> object:
        del name
        return await operation  # type: ignore[misc]

    result = await _execute_layer_write(
        execute_with_span=_span,
        writer=writer,  # type: ignore[arg-type]
        layer="gold",
        records=[{"id": 1}],
        batch_id="b1",  # type: ignore[arg-type]
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        bronze_refs=None,
        silver_refs=None,
    )
    assert result == "gold-ok"
    writer.write_gold.assert_awaited_once()
