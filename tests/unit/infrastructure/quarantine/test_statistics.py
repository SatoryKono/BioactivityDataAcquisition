"""Focused unit tests for quarantine statistics helpers."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.infrastructure.quarantine import _statistics as subject

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
