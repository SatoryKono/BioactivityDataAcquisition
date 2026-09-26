"""Unit coverage for infrastructure modules still below 75% (#10515/#10517)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
import yaml

from bioetl.domain.models.metadata import GoldMetadata, SilverMetadata
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.workflow import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze.metadata_operations import (
    BronzeMetadataWriteRequest,
    prepare_bronze_metadata_write,
)
from bioetl.infrastructure.storage.metadata.writer_operations import (
    _MetadataWriteTelemetryContext,
    _PreparedMetadataWrite,
    _PreparedMetadataWriteOperation,
)
from bioetl.infrastructure.storage.metadata_writer_finalizers import (
    build_gold_metadata_finalizer,
    build_silver_metadata_finalizer,
)
from bioetl.infrastructure.storage.metadata_writer_helpers import (
    _apply_gold_metadata_finalization,
    _apply_silver_metadata_finalization,
    _execute_atomic_metadata_write,
    _execute_prepared_metadata_write_operation,
    _load_existing_metadata_model,
    _resolve_existing_metadata_path,
    load_existing_metadata_model,
)
from bioetl.infrastructure.storage.support.atomic_ops import (
    AtomicWriteError,
    atomic_write,
    atomic_write_bytes,
    atomic_write_text,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine import (
    ReconciliationMutationSummary,
    _delta_table_column_names,
    _require_gold_writer,
    apply_reconciliation_mutation,
    quarantine_orphan_rows,
)
from tests.helpers.metadata_fixtures import build_gold_metadata, build_silver_metadata

pytestmark = pytest.mark.unit


def test_atomic_write_wraps_replace_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.infrastructure.storage.support import atomic_ops as subject

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(subject, "_replace_with_retry", _fail)
    target = tmp_path / "out.txt"
    with pytest.raises(AtomicWriteError):
        with atomic_write(target, mode="w") as handle:
            handle.write("x")
    assert not target.exists()

    def _atomic_fail(*_args: object, **_kwargs: object) -> None:
        raise AtomicWriteError(target, "already wrapped")

    monkeypatch.setattr(subject, "_replace_with_retry", _atomic_fail)
    with pytest.raises(AtomicWriteError, match="already wrapped"):
        with atomic_write(target, mode="w") as handle:
            handle.write("x")


def test_atomic_write_bytes_and_text(tmp_path: Path) -> None:
    binary = tmp_path / "bin.dat"
    text = tmp_path / "text.txt"
    atomic_write_bytes(binary, b"abc")
    atomic_write_text(text, "hello")
    assert binary.read_bytes() == b"abc"
    assert text.read_text(encoding="utf-8") == "hello"


def test_metadata_writer_finalizers_apply_fields() -> None:
    silver = build_silver_metadata()
    gold = build_gold_metadata()
    completed = datetime(2026, 1, 2, tzinfo=UTC)
    build_silver_metadata_finalizer(
        dq_report_path="dq.csv",
        completed_at=completed,
        delta_version_after=7,
    )(silver)
    build_gold_metadata_finalizer(
        dq_report_path="dq.csv",
        completed_at=completed,
    )(gold)
    assert silver.dq_report_path == "dq.csv"
    assert silver.delta.version_after == 7
    assert gold.dq_report_path == "dq.csv"
    _apply_silver_metadata_finalization(
        metadata=silver,
        dq_report_path=None,
        completed_at=None,
        delta_version_after=None,
    )
    _apply_gold_metadata_finalization(
        metadata=gold, dq_report_path=None, completed_at=None
    )


@pytest.mark.asyncio
async def test_metadata_writer_helpers_load_resolve_and_write(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    assert _load_existing_metadata_model(missing, layer="silver") is None
    listed = tmp_path / "list.yaml"
    listed.write_text("- not-a-mapping\n", encoding="utf-8")
    assert _load_existing_metadata_model(listed, layer="silver") is None

    silver = build_silver_metadata()
    silver_path = tmp_path / "silver.yaml"
    payload = silver.model_dump(mode="json")
    if isinstance(payload.get("output"), dict):
        payload["output"]["write_duration_ms"] = 12
    silver_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    loaded_silver = _load_existing_metadata_model(silver_path, layer="silver")
    assert isinstance(loaded_silver, SilverMetadata)

    gold = build_gold_metadata()
    gold_path = tmp_path / "gold.yaml"
    gold_path.write_text(yaml.safe_dump(gold.model_dump(mode="json")), encoding="utf-8")
    loaded_gold = await load_existing_metadata_model(gold_path, layer="gold")
    assert isinstance(loaded_gold, GoldMetadata)

    named = _resolve_existing_metadata_path(
        base_path=tmp_path, layer="silver", provider="chembl", entity="activity"
    )
    assert named.name.endswith(".yaml")
    flat = _resolve_existing_metadata_path(
        base_path=tmp_path,
        layer="silver",
        table_name="activity",
        flat_structure=True,
    )
    assert flat.name == "activity_metadata.yaml"
    default = _resolve_existing_metadata_path(base_path=tmp_path, layer="silver")
    assert default.name == "_metadata.yaml"

    prepared = _PreparedMetadataWrite(
        metadata_path=tmp_path / "written.yaml",
        yaml_content="ok: true\n",
        pipeline_label="chembl_activity",
    )
    context = _MetadataWriteTelemetryContext(
        layer="silver", provider="chembl", pipeline="chembl_activity"
    )
    logger = MagicMock()
    retries = await _execute_atomic_metadata_write(
        logger=logger,
        metrics=None,
        prepared_write=prepared,
        retry_policy=MagicMock(),
        context=context,
        write_text=lambda *_args, **_kwargs: None,
    )
    assert retries == 0

    def _fail_write(*_args: object, **_kwargs: object) -> None:
        raise AtomicWriteError(prepared.metadata_path, "boom")

    with pytest.raises(AtomicWriteError):
        await _execute_atomic_metadata_write(
            logger=logger,
            metrics=None,
            prepared_write=prepared,
            retry_policy=MagicMock(),
            context=context,
            write_text=_fail_write,
        )

    operation = _PreparedMetadataWriteOperation(
        prepared_write=prepared,
        telemetry_context=context,
        run_id="run-1",
    )
    path = await _execute_prepared_metadata_write_operation(
        logger=logger,
        metrics=None,
        retry_policy=MagicMock(),
        operation=operation,
        metadata=silver,
        write_text=lambda *_args, **_kwargs: None,
    )
    assert path.endswith("written.yaml")


def test_prepare_bronze_metadata_write_requires_and_uses_coordinator(
    tmp_path: Path,
) -> None:
    host = SimpleNamespace(
        base_path=tmp_path,
        _flat_structure=False,
        _metadata_coordinator=None,
    )
    output_path = "chembl/activity/file.jsonl.zst"
    full_path = tmp_path / output_path
    full_path.parent.mkdir(parents=True)
    full_path.write_bytes(b"bronze")
    request = BronzeMetadataWriteRequest(
        run_id=RunID(UUID("00000000-0000-4000-8000-000000000001")),
        run_type=RunType.INCREMENTAL,
        provider="chembl",
        entity="activity",
        batch_id=BatchID(UUID("00000000-0000-4000-8000-000000000002")),
        record_count=3,
        compressed_size=128,
        relative_path=output_path,
        ingestion_ts=datetime(2025, 1, 1, tzinfo=UTC),
        duration=2.5,
        source_metadata=None,
    )
    with pytest.raises(RuntimeError, match="MetadataCoordinator"):
        prepare_bronze_metadata_write(host, request)

    class _NoHook:
        pass

    host._metadata_coordinator = _NoHook()
    with pytest.raises(RuntimeError, match="create_bronze_metadata_bundle"):
        prepare_bronze_metadata_write(host, request)

    bundle = SimpleNamespace(metadata=MagicMock(name="meta"), lineage_fragment="frag")

    class _Coordinator:
        def create_bronze_metadata_bundle(self, _input: object) -> object:
            return bundle

    host._metadata_coordinator = _Coordinator()
    prepared = prepare_bronze_metadata_write(host, request)
    assert prepared.metadata is bundle.metadata
    assert prepared.lineage_fragment == "frag"


@pytest.mark.asyncio
async def test_quarantine_mutation_gold_empty_and_write_many() -> None:
    request = ForeignKeyReconciliationRequest(
        source_table="silver.activity",
        reference_table="silver.compound",
        source_key="molecule_chembl_id",
        reference_key="molecule_chembl_id",
        primary_keys=("molecule_chembl_id",),
        source_layer="gold",
        mutation_layer="gold",
        workflow_name="nightly",
        workflow_run_id="wf-1",
        manifest_id="m1",
        step_id="fk",
        transform_name="reconcile",
    )
    host = SimpleNamespace(
        quarantine=None,
        quarantine_pipeline_name=None,
        logger=NoOpLogger(),
        clock=SimpleNamespace(now=lambda: datetime(2026, 1, 1, tzinfo=UTC)),
        silver_writer=MagicMock(),
        gold_writer=None,
    )
    summary = await apply_reconciliation_mutation(host, request, orphan_rows=[])
    assert summary.mutation_mode == "gold_scd2_expiry"

    with pytest.raises(ValueError, match="gold_writer"):
        _require_gold_writer(host)
    host.gold_writer = SimpleNamespace()
    with pytest.raises(ValueError, match="_resolve_table_path"):
        _require_gold_writer(host)

    names = await _delta_table_column_names(
        SimpleNamespace(
            DeltaTable=lambda _path: (_ for _ in ()).throw(RuntimeError("no table"))
        ),
        "table",
        logger=NoOpLogger(),
    )
    assert names is None

    quarantine = SimpleNamespace(write_many=AsyncMock())
    host.quarantine = quarantine
    written = await quarantine_orphan_rows(
        host,
        request,
        orphan_rows=[{"molecule_chembl_id": "CHEMBL1"}],
    )
    assert written.mutation_mode == "quarantine_written"
    quarantine.write_many.assert_awaited()
    skipped = await quarantine_orphan_rows(host, request, orphan_rows=[])
    assert skipped == ReconciliationMutationSummary(mutation_mode="quarantine_skipped")
