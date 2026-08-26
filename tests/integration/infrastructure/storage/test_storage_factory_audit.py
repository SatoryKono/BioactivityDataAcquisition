# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for canonical storage factory audit wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_run_uuid_from_callsite,
)

import pyarrow as pa
import pytest
from pandera.pandas import Column, DataFrameSchema

from bioetl.composition.factories.storage.audit import create_audit_port
from bioetl.composition.factories.storage.storage_factory import StorageFactory
from bioetl.domain.ports import AuditLayer
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import RunType
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter
from bioetl.infrastructure.validation.pandera_validator import NoOpValidator

pytestmark = pytest.mark.integration

TEST_INGESTION_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


def _make_csv_config(path: str, *, enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=enabled,
        path=path,
        delimiter=",",
        header=True,
        encoding="utf-8",
    )


def _make_sink_layer(path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        path=str(path),
        csv_export=_make_csv_config(str(path / "csv"), enabled=False),
        save_json=False,
        save_metadata=False,
        flat_structure=False,
    )


def _make_settings(*, tmp_path: Path, audit_path: Path) -> SimpleNamespace:
    data_dir = tmp_path / "data"
    return SimpleNamespace(
        test_mode=True,
        bronze_path=data_dir / "bronze",
        silver_path=data_dir / "silver",
        gold_path=data_dir / "gold",
        checkpoint_path=data_dir / "checkpoints",
        data_dir=data_dir,
        observability=SimpleNamespace(
            audit_enabled=True,
            audit_base_path=audit_path,
        ),
        pipeline=SimpleNamespace(silver_resilience_enabled=False),
    )


def _make_config(*, tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        provider="chembl",
        entity_type="activity",
        sink={
            "bronze": _make_sink_layer(tmp_path / "yaml" / "bronze"),
            "silver": _make_sink_layer(tmp_path / "yaml" / "silver"),
            "gold": _make_sink_layer(tmp_path / "yaml" / "gold"),
        },
        transform=SimpleNamespace(version="v-test", steps=["extract", "normalize"]),
    )


@pytest.mark.asyncio
async def test_storage_factory_wires_file_audit_across_medallion_writers(
    tmp_path: Path,
    noop_logger: object,
) -> None:
    """Canonical storage wiring should emit Bronze/Silver/Gold audit entries."""
    run_id = deterministic_run_uuid_from_callsite("test_storage_factory_audit")
    batch_id = deterministic_batch_uuid_from_callsite("test_storage_factory_audit")
    audit_path = tmp_path / "audit"
    settings = _make_settings(tmp_path=tmp_path, audit_path=audit_path)
    metrics = NoOpMetrics(warn_on_use=False)
    audit = create_audit_port(
        settings=settings,
        logger=noop_logger,
        metrics=metrics,
    )
    context = StorageFactory.create(
        settings=settings,
        config=_make_config(tmp_path=tmp_path),
        logger=noop_logger,
        metrics=metrics,
        audit=audit,
        silver_validator=NoOpValidator(),
    )

    bronze_audit = context.adapter.bronze._audit
    silver_audit = context.adapter.silver._audit
    gold_audit = context.adapter.gold._audit

    assert isinstance(bronze_audit, FileAuditAdapter)
    assert bronze_audit is silver_audit
    assert bronze_audit is gold_audit
    assert bronze_audit.base_path == audit_path

    try:
        bronze_result = await context.adapter.write_bronze(
            records=iter(
                [
                    b'{"entity_id":"CHEMBL1","value":1.0}\n',
                    b'{"entity_id":"CHEMBL2","value":2.0}\n',
                ]
            ),
            provider="chembl",
            entity="activity",
            date=TEST_INGESTION_TS,
            batch_id=batch_id,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            ingestion_ts=TEST_INGESTION_TS,
        )

        silver_records = [
            {
                "entity_id": "CHEMBL1",
                "value": 1.0,
                "_run_id": str(run_id),
                "_run_type": RunType.INCREMENTAL.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": TEST_INGESTION_TS.isoformat(),
            },
            {
                "entity_id": "CHEMBL2",
                "value": 2.0,
                "_run_id": str(run_id),
                "_run_type": RunType.INCREMENTAL.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": TEST_INGESTION_TS.isoformat(),
            },
        ]
        silver_schema = pa.schema(
            [
                ("entity_id", pa.string()),
                ("value", pa.float64()),
                ("_run_id", pa.string()),
                ("_run_type", pa.string()),
                ("_source_batch_id", pa.string()),
                ("_ingestion_ts", pa.string()),
            ]
        )
        silver_result = await context.adapter.write_silver(
            table_name="chembl.activity_silver",
            records=silver_records,
            primary_keys=["entity_id"],
            schema=silver_schema,
            mode="append",
            bronze_refs=[bronze_result],
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            source_batch_id=batch_id,
            ingestion_ts=TEST_INGESTION_TS,
        )

        assert silver_result is not None

        await context.adapter.write_gold(
            table_name="chembl.activity_gold",
            records=[
                {
                    "entity_id": "CHEMBL1",
                    "score": 0.95,
                }
            ],
            schema=DataFrameSchema(
                {
                    "entity_id": Column(str, nullable=False),
                    "score": Column(float, nullable=False),
                },
                strict=True,
            ),
            primary_keys=["entity_id"],
            mode="append",
            ingestion_ts=TEST_INGESTION_TS,
            run_id=run_id,
            silver_refs=[silver_result],
        )

        entries = await bronze_audit.get_entries(run_id=run_id, limit=10)
    finally:
        await context.adapter.aclose()

    assert bronze_audit._closed is True

    assert {entry.layer for entry in entries} == {
        AuditLayer.BRONZE,
        AuditLayer.SILVER,
        AuditLayer.GOLD,
    }

    entries_by_layer = {entry.layer: entry for entry in entries}
    bronze_entry = entries_by_layer[AuditLayer.BRONZE]
    silver_entry = entries_by_layer[AuditLayer.SILVER]
    gold_entry = entries_by_layer[AuditLayer.GOLD]

    assert bronze_entry.records_count == 2
    assert silver_entry.records_count == 2
    assert gold_entry.records_count == 1
    assert "chembl/activity" in bronze_entry.table_name.replace("\\", "/")
    assert silver_entry.table_name == "chembl.activity_silver"
    assert gold_entry.table_name == "chembl.activity_gold"
