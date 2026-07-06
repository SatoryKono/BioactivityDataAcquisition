"""Focused unit tests for quarantine statistics helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioetl.infrastructure.quarantine import _statistics as subject
from bioetl.infrastructure.quarantine import filtered_manifest_support
from bioetl.infrastructure.quarantine import statistics_support

pytestmark = pytest.mark.unit


class _FakeArrowTable:
    def __init__(
        self,
        rows: list[dict[str, object]],
        *,
        filtered_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self._rows = rows
        self._filtered_rows = filtered_rows
        self.filter_mask: object | None = None

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, column: str) -> list[object]:
        return [row.get(column) for row in self._rows]

    def filter(self, mask: object) -> _FakeArrowTable:
        self.filter_mask = mask
        return _FakeArrowTable(
            self._filtered_rows if self._filtered_rows is not None else self._rows
        )

    def to_pylist(self) -> list[dict[str, object]]:
        return self._rows


class _FakeDeltaTable:
    def __init__(self, table: _FakeArrowTable) -> None:
        self.table = table
        self.partitions: list[tuple[str, str, object]] | None = None
        self.filters: list[tuple[str, str, object]] | None = None

    def to_pyarrow_table(
        self,
        *,
        partitions: list[tuple[str, str, object]],
        filters: list[tuple[str, str, object]] | None,
    ) -> _FakeArrowTable:
        self.partitions = partitions
        self.filters = filters
        return self.table


class _FakeSeries:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def min(self) -> object:
        return self._values[0]

    def max(self) -> object:
        return self._values[-1]


class _FakePandasFrame:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def __getitem__(self, column: str) -> _FakeSeries:
        assert column == "ingestion_ts"
        return _FakeSeries(self._values)


class _FakePandasArrowTable:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def to_pandas(self) -> _FakePandasFrame:
        return _FakePandasFrame(self._values)


def test_filtered_manifest_lookup_handles_missing_invalid_and_cached_manifests(
    tmp_path: Path,
) -> None:
    """Run type lookup should tolerate partial control-plane manifest indexes."""
    root = tmp_path / "control" / "run_manifest"
    index = root / "_by_run_id"
    index.mkdir(parents=True)
    base_path = tmp_path / "quarantine"
    base_path.mkdir()

    (index / "run-1.txt").write_text("manifest-a\n", encoding="utf-8")
    (index / "run-2.txt").write_text("manifest-a\n", encoding="utf-8")
    (index / "run-3.txt").write_text("manifest-missing\n", encoding="utf-8")
    (index / "run-4.txt").write_text("manifest-invalid\n", encoding="utf-8")
    (index / "run-5.txt").write_text("manifest-empty\n", encoding="utf-8")
    (root / "manifest-a.json").write_text(
        '{"run_type": " incremental "}',
        encoding="utf-8",
    )
    (root / "manifest-invalid.json").write_text("{", encoding="utf-8")
    (root / "manifest-empty.json").write_text('{"run_type": " "}', encoding="utf-8")

    assert filtered_manifest_support._parse_run_type_from_manifest_payload([]) is None
    assert (
        filtered_manifest_support._parse_run_type_from_manifest_payload({"run_type": 1})
        is None
    )
    assert (
        filtered_manifest_support._parse_run_type_from_manifest_payload(
            {"run_type": " "}
        )
        is None
    )
    assert filtered_manifest_support._build_run_type_lookup(
        [
            {"run_id": None},
            {"run_id": " "},
            {"run_id": "run-1"},
            {"run_id": "run-2"},
            {"run_id": "run-1"},
            {"run_id": "run-3"},
            {"run_id": "run-4"},
            {"run_id": "run-5"},
            {"run_id": "run-missing-index"},
        ],
        base_path=str(base_path),
    ) == {"run-1": "incremental", "run-2": "incremental"}

    fallback_base = tmp_path / "fallback" / "quarantine"
    fallback_root = tmp_path / "fallback" / "control_plane" / "run_manifest"
    fallback_index = fallback_root / "_by_run_id"
    fallback_base.mkdir(parents=True)
    fallback_index.mkdir(parents=True)
    (fallback_index / "run-6.txt").write_text("manifest-b\n", encoding="utf-8")
    (fallback_root / "manifest-b.json").write_text(
        '{"run_type": "backfill"}',
        encoding="utf-8",
    )
    assert filtered_manifest_support._build_run_type_lookup(
        [{"run_id": "run-6"}],
        base_path=str(fallback_base),
    ) == {"run-6": "backfill"}
    assert (
        filtered_manifest_support._build_run_type_lookup(
            [{"run_id": "run-7"}],
            base_path=str(tmp_path / "missing-quarantine"),
        )
        == {}
    )


def test_statistics_support_processes_filtered_reason_dimensions() -> None:
    """Support aggregation should count only structured Silver-filter dimensions."""
    rows = [
        {
            "error_code": "SCHEMA_ERROR",
            "dq_status": "FAILED",
            "error_details": {"reason_code": "ignored"},
        },
        {
            "error_code": "FILTERED_OUT_SILVER",
            "dq_status": "FILTERED",
            "error_details": {
                "reason_code": "missing_required_field",
                "field": "canonical_smiles",
                "rule_type": "required_fields",
                "operator": "required",
            },
        },
        {
            "error_code": "FILTERED_OUT_SILVER",
            "dq_status": "FILTERED",
            "error_details": (
                '{"reason_code": "invalid_type", "field": "molecule_weight", '
                '"rule_type": "type", "operator": "float"}'
            ),
        },
        {
            "error_code": "FILTERED_OUT_SILVER",
            "dq_status": "FILTERED",
            "error_details": "[]",
        },
        {
            "error_code": "FILTERED_OUT_SILVER",
            "dq_status": "FILTERED",
            "error_details": None,
        },
    ]

    (
        by_error_code,
        by_status,
        by_reason_code,
        by_field,
        by_rule_type,
        by_operator,
        by_reason_code_field,
        by_reason_signature,
        silver_filter_total,
    ) = statistics_support._process_quarantine_records(rows)

    assert by_error_code == {"SCHEMA_ERROR": 1, "FILTERED_OUT_SILVER": 4}
    assert by_status == {"FAILED": 1, "FILTERED": 4}
    assert by_reason_code == {"missing_required_field": 1, "invalid_type": 1}
    assert by_field == {"canonical_smiles": 1, "molecule_weight": 1}
    assert by_rule_type == {"required_fields": 1, "type": 1}
    assert by_operator == {"required": 1, "float": 1}
    assert by_reason_code_field == {
        "missing_required_field | canonical_smiles": 1,
        "invalid_type | molecule_weight": 1,
    }
    assert by_reason_signature == {
        "missing_required_field | required_fields | canonical_smiles | required": 1,
        "invalid_type | type | molecule_weight | float": 1,
    }
    assert silver_filter_total == 4


def test_statistics_support_counts_bronze_scope_and_builds_response() -> None:
    """Pure statistics helpers should sort counters and preserve scoped totals."""
    calls: list[tuple[str, str | None]] = []

    def load_pipeline_stats(pipeline: str, run_id: str | None) -> dict[str, object]:
        calls.append((pipeline, run_id))
        return {
            "total_count": {"chembl_activity": 7, "pubchem_compound": 11}.get(pipeline)
        }

    rows = [
        {"pipeline": " chembl_activity "},
        {"pipeline": ""},
        {"pipeline": "pubchem_compound"},
        {"pipeline": 42},
    ]
    assert statistics_support._scoped_pipeline_names(rows, None) == {
        "chembl_activity",
        "pubchem_compound",
    }
    assert statistics_support._scoped_pipeline_names(rows, {"chembl_activity"}) == {
        "chembl_activity"
    }
    assert (
        statistics_support._count_bronze_records(
            rows,
            pipeline_filter=None,
            pipeline_stats_loader=load_pipeline_stats,
            run_id_single="run-1",
        )
        == 18
    )
    assert calls == [("chembl_activity", "run-1"), ("pubchem_compound", "run-1")]
    assert (
        statistics_support._count_bronze_records(
            rows,
            pipeline_filter={"unknown"},
            pipeline_stats_loader=load_pipeline_stats,
            run_id_single=None,
        )
        == 0
    )
    assert statistics_support._sorted_counter_items({"b": 1, "a": 2}) == [
        {"key": "a", "count": 2},
        {"key": "b", "count": 1},
    ]
    assert (
        statistics_support._build_reason_signature_from_row(
            {
                "reason_code": " missing ",
                "rule_type": "required",
                "field": "canonical_smiles",
                "operator": "",
            }
        )
        == "missing | required | canonical_smiles"
    )
    assert statistics_support._build_reason_signature_from_row({"operator": 1}) == ""
    assert statistics_support._get_time_statistics(
        _FakePandasArrowTable(["2026-01-01", "2026-01-02"])
    ) == ("2026-01-01", "2026-01-02")
    assert statistics_support._build_statistics_response(
        3,
        {"FILTERED_OUT_SILVER": 3},
        {"FILTERED": 3},
        "oldest",
        "newest",
        3,
        {"missing": 2},
        {"field": 2},
        {"rule": 2},
        {"op": 2},
        {"missing | field": 2},
        {"missing | rule | field | op": 2},
    ) == {
        "total_count": 3,
        "total_records": 3,
        "by_error_code": {"FILTERED_OUT_SILVER": 3},
        "by_status": {"FILTERED": 3},
        "oldest_record": "oldest",
        "newest_record": "newest",
        "silver_filter_rejects": {
            "total_count": 3,
            "by_reason_code": {"missing": 2},
            "by_field": {"field": 2},
            "by_rule_type": {"rule": 2},
            "by_operator": {"op": 2},
            "by_reason_code_field": {"missing | field": 2},
            "by_reason_signature": {"missing | rule | field | op": 2},
        },
    }


def test_get_filtered_stats_aggregates_reason_and_run_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filtered stats should summarize structural Silver reject dimensions."""

    def fake_load_filtered_rows(*_args: Any, **_kwargs: Any) -> list[dict[str, object]]:
        return [
            {
                "reason_code": "missing_required_field",
                "field": "canonical_smiles",
                "rule_type": "required_fields",
                "operator": "required",
                "run_id": "run-2",
            },
            {
                "reason_code": "missing_required_field",
                "field": "canonical_smiles",
                "rule_type": "required_fields",
                "operator": "required",
                "run_id": "run-1",
            },
            {
                "reason_code": "invalid_type",
                "field": "molecule_weight",
                "rule_type": "type",
                "operator": "float",
                "run_id": "",
            },
        ]

    monkeypatch.setattr(subject, "_load_filtered_rows", fake_load_filtered_rows)

    result = subject.get_filtered_stats("delta/path", None, pipeline="chembl_activity")

    assert result["total"] == 3
    assert result["run_ids"] == ["run-1", "run-2"]
    assert result["by_reason_code"] == [
        {"key": "missing_required_field", "count": 2},
        {"key": "invalid_type", "count": 1},
    ]
    assert result["by_field"] == [
        {"key": "canonical_smiles", "count": 2},
        {"key": "molecule_weight", "count": 1},
    ]
    assert result["by_reason_signature"][0] == {
        "key": "missing_required_field | required_fields | canonical_smiles | required",
        "count": 2,
    }


def test_get_filtered_stats_preserves_explicit_run_scope_for_empty_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit run-id filter remains visible when no rows match it."""
    monkeypatch.setattr(subject, "_load_filtered_rows", lambda *_args, **_kwargs: [])

    result = subject.get_filtered_stats("delta/path", None, run_id="run-42")

    assert result["total"] == 0
    assert result["run_ids"] == ["run-42"]
    assert result["by_reason_code"] == []
    assert result["by_field"] == []


def test_get_statistics_returns_empty_stats_when_delta_table_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing_table(*_args: Any, **_kwargs: Any) -> object:
        raise subject.TableNotFoundError("not found")

    monkeypatch.setattr(subject, "DeltaTable", raise_missing_table)

    result = subject.get_statistics("missing/path", None, pipeline="chembl_activity")

    assert result["total_count"] == 0
    assert result["total_records"] == 0
    assert result["silver_filter_rejects"]["total_count"] == 0


def test_get_statistics_returns_empty_stats_when_run_filter_matches_no_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _FakeArrowTable(
        [{"run_id": "run-1", "error_code": "invalid_type"}],
        filtered_rows=[],
    )
    delta_table = _FakeDeltaTable(table)

    monkeypatch.setattr(subject, "DeltaTable", lambda *_args, **_kwargs: delta_table)
    monkeypatch.setattr(
        subject,
        "equal_mask",
        lambda column, value: {"column": column, "value": value},
    )

    result = subject.get_statistics(
        "delta/path",
        {"AWS_REGION": "us-east-1"},
        pipeline="chembl_activity",
        error_code="invalid_type",
        run_id="run-2",
    )

    assert delta_table.partitions == [("pipeline", "=", "chembl_activity")]
    assert delta_table.filters == [("error_code", "=", "invalid_type")]
    assert result["total_count"] == 0


def test_get_statistics_processes_filtered_rows_into_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [{"run_id": "run-1", "error_code": "invalid_type"}]
    table = _FakeArrowTable(rows)
    delta_table = _FakeDeltaTable(table)
    processed = (
        {"invalid_type": 1},
        {"open": 1},
        {"missing_required_field": 1},
        {"canonical_smiles": 1},
        {"required_fields": 1},
        {"required": 1},
        {"missing_required_field|canonical_smiles": 1},
        {"missing_required_field|required_fields|canonical_smiles|required": 1},
        1,
    )

    monkeypatch.setattr(subject, "DeltaTable", lambda *_args, **_kwargs: delta_table)
    monkeypatch.setattr(subject, "_process_quarantine_records", lambda data: processed)
    monkeypatch.setattr(
        subject,
        "_get_time_statistics",
        lambda arrow_table: ("2026-06-17T10:00:00Z", "2026-06-17T11:00:00Z"),
    )
    monkeypatch.setattr(
        subject,
        "_build_statistics_response",
        lambda *args: {"response_args": args},
    )

    result = subject.get_statistics("delta/path", None, pipeline="chembl_activity")

    assert delta_table.partitions == [("pipeline", "=", "chembl_activity")]
    assert delta_table.filters is None
    assert result["response_args"] == (
        1,
        processed[0],
        processed[1],
        "2026-06-17T10:00:00Z",
        "2026-06-17T11:00:00Z",
        processed[8],
        processed[2],
        processed[3],
        processed[4],
        processed[5],
        processed[6],
        processed[7],
    )
