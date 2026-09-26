"""Stream A gold helpers: io_preparation and gold-only helpers, no silver_writer."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.types import ScdConfig
from bioetl.infrastructure.storage.gold import io_delta_runtime as gold_runtime
from bioetl.infrastructure.storage.gold import io_helpers as gold_helpers
from bioetl.infrastructure.storage.gold.io_metrics import (
    _gold_merged_metric_labels,
    _gold_merged_validation_metric_labels,
    _split_gold_merged_table_label,
)
from bioetl.infrastructure.storage.gold.io_preparation import (
    _GoldMergedWriteRequest,
    _log_prepared_gold_merged_write,
    _prepare_gold_merged_table,
    _prepare_gold_merged_write,
)
from bioetl.infrastructure.storage.gold.metadata_payloads import (
    _extract_completed_at,
    build_gold_merged_metadata_input,
    build_gold_metadata_payload,
    build_gold_metadata_via_coordinator,
)
from bioetl.infrastructure.storage.gold.writer_metrics import (
    _gold_validation_error_type_label,
    _gold_validation_metric_labels,
    _gold_write_metric_labels,
    _split_gold_table_label,
)

pytestmark = pytest.mark.unit


def _patch_gold_writer_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold.io_preparation._load_gold_writer_module",
        lambda: SimpleNamespace(coerce_null_types_for_delta=lambda table: table),
    )


class TestIoPreparation:
    def test_prepare_table_sorts_and_drops_ingestion_ts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_gold_writer_module(monkeypatch)
        table = _prepare_gold_merged_table(
            records=[
                {"id": "b", "value": 2, "_ingestion_ts": "ts"},
                {"id": "a", "value": 1, "_ingestion_ts": "ts"},
            ],
            primary_keys=["id"],
            preserve_column_order=False,
        )
        assert "_ingestion_ts" not in table.column_names
        assert table.column("id").to_pylist() == ["a", "b"]

    def test_prepare_table_preserves_order_without_valid_keys(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_gold_writer_module(monkeypatch)
        table = _prepare_gold_merged_table(
            records=[{"id": "b"}, {"id": "a"}],
            primary_keys=["missing"],
            preserve_column_order=True,
        )
        assert table.column("id").to_pylist() == ["b", "a"]
        unsorted = _prepare_gold_merged_table(
            records=[{"id": "b"}, {"id": "a"}],
            primary_keys=None,
            preserve_column_order=False,
        )
        assert unsorted.column("id").to_pylist() == ["b", "a"]

    async def test_prepare_write_and_log(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_gold_writer_module(monkeypatch)
        logger = MagicMock()
        host = SimpleNamespace(
            logger=logger,
            csv_exporter=None,
            _resolve_table_path=lambda name: f"/tables/{name}",
            _validate_schema_strict=lambda _schema: None,
            _validate_records_against_schema=AsyncMock(),
        )
        request = _GoldMergedWriteRequest(
            table_name="chembl/activity",
            records=[{"id": "1"}],
            primary_keys=["id"],
            schema=MagicMock(),
            completed_at=datetime(2024, 1, 1, tzinfo=UTC),
            run_id="run-1",
            sources_used=["chembl"],
            preserve_column_order=False,
        )
        prepared = await _prepare_gold_merged_write(host, request)
        assert prepared.table_path == "/tables/chembl/activity"
        host._validate_records_against_schema.assert_awaited()
        _log_prepared_gold_merged_write(host, prepared)
        logger.info.assert_called()


class TestGoldHelpers:
    def test_initialize_scd2_records(self) -> None:
        records = [{"id": "1"}, {"id": "2", "version": 4}]
        initialize = gold_helpers.initialize_scd2_records
        scd = ScdConfig(business_key="id")
        ts = datetime(2024, 1, 1, tzinfo=UTC)
        initialize(records, scd, ts)
        assert records[0]["is_current"] is True
        assert records[0]["version"] == 1
        assert records[1]["version"] == 4
        assert records[0]["valid_to"] is None

    def test_writer_and_merged_metrics(self) -> None:
        assert _split_gold_table_label("") == ("unknown", "unknown")
        assert _split_gold_table_label("chembl/activity")[0] == "chembl"
        assert _split_gold_table_label("chembl.activity")[1] == "activity"
        request = SimpleNamespace(table_name="chembl/activity", mode="overwrite")
        labels = _gold_write_metric_labels(request, status="success")
        assert labels["mode"] == "overwrite"
        assert labels["status"] == "success"
        unknown = _gold_write_metric_labels(
            SimpleNamespace(table_name="solo", mode="mystery"), status="nope"
        )
        assert unknown["mode"] == "other"
        assert unknown["status"] == "failure"
        assert _gold_validation_error_type_label(ValueError("x")) == "ValueError"
        assert _gold_validation_error_type_label(RuntimeError("x")) == "RuntimeError"
        validation = _gold_validation_metric_labels(request, TypeError("bad"))
        assert validation["error_type"] == "TypeError"
        assert _split_gold_merged_table_label("/") == ("unknown", "unknown")
        merged = _gold_merged_metric_labels("pipeline/table", status="success")
        assert merged["mode"] == GoldWriteMode.OVERWRITE.value
        merged_unknown = _gold_merged_metric_labels("solo", status="weird")
        assert merged_unknown["status"] == "failure"
        merged_validation = _gold_merged_validation_metric_labels(
            "chembl.activity", ValueError("x")
        )
        assert merged_validation["error_type"] == "ValueError"

    def test_metadata_payloads(self) -> None:
        records = [
            {"_ingestion_ts": "2024-01-02T00:00:00+00:00"},
            {"_ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC)},
            {"_ingestion_ts": "bad"},
        ]
        extracted = _extract_completed_at(records)
        assert extracted == datetime(2024, 1, 1, tzinfo=UTC)
        assert _extract_completed_at([]) is None
        merged = build_gold_merged_metadata_input(
            table_path="/gold",
            table_name="chembl/activity",
            records=records,
            completed_at=None,
            schema=None,
            transform_version="1",
            transform_steps=("merge",),
        )
        assert merged.mode is GoldWriteMode.OVERWRITE
        with pytest.raises(RuntimeError, match="MetadataCoordinator is required"):
            build_gold_metadata_payload(
                coordinator=None,
                table_path="/gold",
                table_name="t",
                records=[],
                mode=GoldWriteMode.OVERWRITE,
                scd_config=None,
                ingestion_ts=None,
                run_id=None,
                silver_refs=None,
                gold_schema=None,
                transform_version=None,
                transform_steps=(),
            )
        coordinator = SimpleNamespace(
            create_gold_metadata_bundle=lambda _inp: SimpleNamespace(
                metadata="gold-meta", lineage_fragment=None
            )
        )
        built = build_gold_metadata_via_coordinator(
            coordinator=coordinator,
            table_path="/gold",
            table_name="t",
            records=[],
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            completed_at=None,
            silver_refs=None,
            gold_schema=None,
            transform_version=None,
            transform_steps=(),
        )
        assert built == "gold-meta"

    async def test_delta_runtime_retry_helpers(self) -> None:
        assert gold_runtime._gold_write_retry_delay(0) == pytest.approx(0.55)
        extended = gold_runtime._extend_retry_errors_with_arrow((OSError,))
        assert pa.ArrowException in extended
        already = gold_runtime._extend_retry_errors_with_arrow((pa.ArrowException,))
        assert already == (pa.ArrowException,)
        typed = gold_runtime._base_exception_retry_types((OSError, "nope"))  # type: ignore[arg-type]
        assert typed == (OSError,)
        module = SimpleNamespace(GOLD_WRITE_RETRY_ERRORS=(), asyncio=SimpleNamespace())
        called = {"n": 0}

        async def once() -> None:
            called["n"] += 1

        await gold_runtime._run_gold_write_with_retry(module, once)
        assert called["n"] == 1

        attempts = {"n": 0}

        async def fail_then_ok() -> None:
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise OSError("retry")

        sleep = AsyncMock()
        retry_module = SimpleNamespace(
            GOLD_WRITE_RETRY_ERRORS=(OSError,),
            asyncio=SimpleNamespace(sleep=sleep),
        )
        await gold_runtime._run_gold_write_with_retry(retry_module, fail_then_ok)
        assert attempts["n"] == 2
        sleep.assert_awaited()

        prepared = gold_runtime._build_simple_gold_write(
            SimpleNamespace(
                _to_arrow_table=lambda records, column_order=None: pa.table(
                    {"id": [row["id"] for row in records]}
                )
            ),
            gold_runtime._SimpleGoldWriteRequest(
                table_path="/g",
                table_name="t",
                records=[{"id": "b"}, {"id": "a"}],
                mode="overwrite",
                partition_cols=None,
                primary_keys=["id"],
            ),
        )
        assert prepared.schema_mode == "overwrite"
        assert prepared.arrow_data.column("id").to_pylist() == ["a", "b"]
