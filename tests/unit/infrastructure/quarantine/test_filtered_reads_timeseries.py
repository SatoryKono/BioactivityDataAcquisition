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
"""Focused tests for quarantine filtered read and timeseries APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from bioetl.infrastructure.quarantine import _statistics_helpers
from bioetl.infrastructure.quarantine import _timeseries
from bioetl.infrastructure.quarantine import filtered_reads
from bioetl.infrastructure.quarantine import record_encoding

pytestmark = pytest.mark.unit


class _FakeArrowTable:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def to_pylist(self) -> list[dict[str, object]]:
        return self._rows


@dataclass
class _FakeMetadata:
    partition_columns: object


class _FakeDeltaTable:
    def __init__(
        self,
        rows: list[dict[str, object]],
        *,
        partition_columns: object = (),
    ) -> None:
        self._rows = rows
        self._partition_columns = partition_columns
        self.partitions: list[tuple[str, str, object]] | None = None
        self.filters: list[tuple[str, str, object]] | None = None
        self.columns: list[str] | None = None

    def metadata(self) -> _FakeMetadata:
        return _FakeMetadata(self._partition_columns)

    def to_pyarrow_table(
        self,
        *,
        partitions: list[tuple[str, str, object]] | None,
        filters: list[tuple[str, str, object]] | None,
        columns: list[str] | None = None,
    ) -> _FakeArrowTable:
        self.partitions = partitions
        self.filters = filters
        self.columns = columns
        return _FakeArrowTable(self._rows)


@dataclass
class _FakeSchemaField:
    name: str


@dataclass
class _FakeSchema:
    fields: list[_FakeSchemaField]


class _ProjectionDeltaTable(_FakeDeltaTable):
    def __init__(self, rows: list[dict[str, object]]) -> None:
        super().__init__(rows, partition_columns=["pipeline"])
        self.columns: list[str] | None = None

    def schema(self) -> _FakeSchema:
        return _FakeSchema(
            [
                _FakeSchemaField(name)
                for name in (
                    "ingestion_ts",
                    "pipeline",
                    "run_id",
                    "payload_hash",
                    "error_code",
                    "error_details",
                    "dq_status",
                    "payload",
                )
            ]
        )

    def to_pyarrow_table(
        self,
        *,
        partitions: list[tuple[str, str, object]] | None,
        filters: list[tuple[str, str, object]] | None,
        columns: list[str] | None = None,
    ) -> _FakeArrowTable:
        self.columns = columns
        return super().to_pyarrow_table(
            partitions=partitions, filters=filters, columns=columns
        )


def test_record_encoding_quotes_strings_booleans_numbers_and_hashes() -> None:
    assert record_encoding.quote_literal("O'Hara") == "'O''Hara'"
    assert record_encoding.quote_literal(True) == "true"
    assert record_encoding.quote_literal(False) == "false"
    assert record_encoding.quote_literal(42) == "42"
    assert record_encoding.quote_literal(3.5) == "3.5"
    assert record_encoding.quote_literal(None) == "'None'"
    assert record_encoding.calculate_hash('{"a":1}') == (
        "015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862"
    )


def test_filtered_stats_projection_excludes_large_payload_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _ProjectionDeltaTable([])
    monkeypatch.setattr(filtered_reads, "DeltaTable", lambda *_a, **_kw: table)

    filtered_reads._load_filtered_rows(
        "delta/path",
        None,
        pipeline="chembl_activity",
        run_type=None,
        reason_code=None,
        field=None,
        run_id=None,
        payload_hash=None,
        from_ts=None,
        to_ts=None,
        include_payload=False,
        include_payload_preview=False,
    )

    assert table.columns is not None
    assert "payload" not in table.columns
    assert {"pipeline", "run_id", "error_details"} <= set(table.columns)


def test_statistics_bucket_helpers_normalize_supported_buckets() -> None:
    assert _statistics_helpers.resolve_bucket_seconds(" 1H ") == 3600
    assert _statistics_helpers.resolve_bucket_seconds("6h") == 21600
    assert _statistics_helpers.resolve_bucket_seconds("1d") == 86400
    assert (
        _statistics_helpers.bucket_start_iso(
            "2026-07-07T10:17:30+00:00",
            bucket_seconds=3600,
        )
        == "2026-07-07T10:00:00+00:00"
    )
    assert (
        _statistics_helpers.bucket_start_iso("not-a-date", bucket_seconds=3600) is None
    )
    with pytest.raises(ValueError, match="Unsupported filtered-timeseries bucket"):
        _statistics_helpers.resolve_bucket_seconds("15m")


def test_load_filtered_rows_uses_partition_filter_when_pipeline_is_partitioned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {
            "ingestion_ts": "2026-07-07T10:05:00Z",
            "pipeline": "chembl_activity",
            "run_id": "run-1",
            "payload_hash": "hash-1",
            "error_code": "FILTERED_OUT_SILVER",
            "dq_status": "FILTERED",
            "error_details": {
                "reason_code": "missing_required_field",
                "field": "target_id",
            },
        }
    ]
    table = _FakeDeltaTable(rows, partition_columns=["pipeline"])
    monkeypatch.setattr(filtered_reads, "DeltaTable", lambda *_a, **_kw: table)

    result = filtered_reads._load_filtered_rows(
        "delta/path",
        {"AWS_REGION": "us-east-1"},
        pipeline="chembl_activity",
        run_type=None,
        reason_code="missing_required_field",
        field="target_id",
        run_id="run-1",
        payload_hash="hash-1",
        from_ts=None,
        to_ts=None,
        include_payload=False,
        include_payload_preview=False,
    )

    assert table.partitions == [("pipeline", "=", "chembl_activity")]
    assert table.filters == [
        ("error_code", "=", "FILTERED_OUT_SILVER"),
        ("run_id", "=", "run-1"),
        ("payload_hash", "=", "hash-1"),
    ]
    assert [row["payload_hash"] for row in result] == ["hash-1"]
    assert result[0]["reason_code"] == "missing_required_field"


def test_load_filtered_rows_uses_row_filter_for_legacy_non_partitioned_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _FakeDeltaTable([], partition_columns=["provider"])
    monkeypatch.setattr(filtered_reads, "DeltaTable", lambda *_a, **_kw: table)

    result = filtered_reads._load_filtered_rows(
        "delta/path",
        None,
        pipeline="chembl_activity",
        run_type=None,
        reason_code=None,
        field=None,
        run_id=None,
        payload_hash=None,
        from_ts=None,
        to_ts=None,
        include_payload=False,
        include_payload_preview=False,
    )

    assert result == []
    assert table.partitions is None
    assert table.filters == [
        ("error_code", "=", "FILTERED_OUT_SILVER"),
        ("pipeline", "=", "chembl_activity"),
    ]


def test_filtered_reads_raise_on_unscoped_lookup_and_tolerate_missing_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="require a scoped pipeline"):
        filtered_reads._load_filtered_rows(
            "delta/path",
            None,
            pipeline=None,
            run_type=None,
            reason_code=None,
            field=None,
            run_id=None,
            payload_hash=None,
            from_ts=None,
            to_ts=None,
            include_payload=False,
            include_payload_preview=False,
        )

    def raise_missing(*_args: Any, **_kwargs: Any) -> object:
        raise filtered_reads.TableNotFoundError("missing")

    monkeypatch.setattr(filtered_reads, "DeltaTable", raise_missing)
    assert (
        filtered_reads._load_filtered_rows(
            "missing/path",
            None,
            pipeline="chembl_activity",
            run_type=None,
            reason_code=None,
            field=None,
            run_id=None,
            payload_hash=None,
            from_ts=None,
            to_ts=None,
            include_payload=False,
            include_payload_preview=False,
        )
        == []
    )


def test_list_filtered_records_sorts_clamps_and_paginates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        filtered_reads,
        "_load_filtered_rows",
        lambda *_args, **_kwargs: [
            {"ingestion_ts": "2026-07-07T10:00:00Z", "payload_hash": "old"},
            {"ingestion_ts": "2026-07-07T11:00:00Z", "payload_hash": "new"},
        ],
    )

    result = filtered_reads.list_filtered_records(
        "delta/path",
        None,
        pipeline="chembl_activity",
        limit=1,
        offset=-2,
    )

    assert result == {
        "items": [{"ingestion_ts": "2026-07-07T11:00:00Z", "payload_hash": "new"}],
        "total": 2,
        "limit": 1,
        "offset": 0,
    }


def test_get_filtered_record_returns_latest_detail_with_cli_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {
            "ingestion_ts": "2026-07-07T10:00:00Z",
            "pipeline": "chembl_activity",
            "run_id": "run-1",
            "payload_hash": "hash-1",
            "error_code": "FILTERED_OUT_SILVER",
            "error_details": {"reason_code": "old"},
        },
        {
            "ingestion_ts": "2026-07-07T11:00:00Z",
            "pipeline": "chembl_activity",
            "run_id": "run-2",
            "payload_hash": "hash-1",
            "error_code": "FILTERED_OUT_SILVER",
            "error_details": {"reason_code": "new"},
        },
    ]
    table = _FakeDeltaTable(rows, partition_columns=["pipeline"])
    monkeypatch.setattr(filtered_reads, "DeltaTable", lambda *_a, **_kw: table)

    result = filtered_reads.get_filtered_record(
        "delta/path",
        None,
        payload_hash="hash-1",
        pipeline="chembl_activity",
    )

    assert result is not None
    assert result["run_id"] == "run-2"
    assert result["reason_code"] == "new"
    assert result["cli_hint"] == (
        "bioetl quarantine resolve --pipeline chembl_activity "
        "--payload-hash hash-1 --status IGNORED"
    )


def test_get_filtered_filter_options_collects_distinct_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        filtered_reads,
        "_load_filtered_rows",
        lambda *_args, **_kwargs: [
            {
                "pipeline": "chembl_activity",
                "run_type": "incremental",
                "reason_code": "missing",
                "field": "target_id",
                "run_id": "run-1",
            },
            {
                "pipeline": "chembl_activity",
                "run_type": "incremental",
                "reason_code": "type",
                "field": "assay_id",
                "run_id": "run-2",
            },
        ],
    )

    assert filtered_reads.get_filtered_filter_options(
        "delta/path",
        None,
        pipeline="chembl_activity",
    ) == {
        "pipelines": ["chembl_activity"],
        "run_types": ["incremental"],
        "reason_codes": ["missing", "type"],
        "fields": ["assay_id", "target_id"],
        "run_ids": ["run-1", "run-2"],
    }


def test_get_filtered_timeseries_buckets_rows_and_sorts_run_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _timeseries,
        "_load_filtered_rows",
        lambda *_args, **_kwargs: [
            {"ingestion_ts": "2026-07-07T10:05:00Z", "run_id": "run-b"},
            {"ingestion_ts": "2026-07-07T10:55:00Z", "run_id": "run-a"},
            {"ingestion_ts": "not-a-date", "run_id": "run-c"},
            {"ingestion_ts": "2026-07-07T11:01:00Z", "run_id": ""},
        ],
    )

    result = _timeseries.get_filtered_timeseries(
        "delta/path",
        None,
        pipeline="chembl_activity",
        bucket="1h",
    )

    assert result == {
        "bucket": "1h",
        "rows": [
            {
                "bucket_start": "2026-07-07T10:00:00+00:00",
                "reject_count": 2,
                "bronze_records": 0,
                "reject_ratio": 0.0,
                "run_ids": ["run-a", "run-b"],
            },
            {
                "bucket_start": "2026-07-07T11:00:00+00:00",
                "reject_count": 1,
                "bronze_records": 0,
                "reject_ratio": 0.0,
                "run_ids": [],
            },
        ],
    }
