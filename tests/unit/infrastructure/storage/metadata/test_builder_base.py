"""Focused branch tests for metadata builder base helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bioetl.infrastructure.storage.metadata import builder_base
from bioetl.infrastructure.storage.metadata.builder_base import (
    _MetadataBuilderBase,
    _build_gold_artifact_id,
    _build_silver_artifact_id,
    _get_git_commit_cached,
    _parse_table_name,
    _resolve_metadata_timestamp,
    _resolve_records_metadata_timestamp,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("table_name", "expected"),
    [
        ("chembl.activity", ("chembl", "activity")),
        ("composite/activity", ("composite", "activity")),
        ("pubchem_compound", ("pubchem", "compound")),
        ("activity", ("unknown", "activity")),
        ("", ("unknown", "unknown")),
    ],
)
def test_parse_table_name_covers_supported_shapes(
    table_name: str,
    expected: tuple[str, str],
) -> None:
    assert _parse_table_name(table_name) == expected


def test_resolve_metadata_timestamp_prefers_explicit_and_normalizes_utc() -> None:
    explicit = datetime(2026, 6, 17, 12, 0)

    resolved = _resolve_metadata_timestamp(explicit=explicit, records=[])

    assert resolved == datetime(2026, 6, 17, 12, 0, tzinfo=UTC)


def test_resolve_metadata_timestamp_uses_earliest_record_anchor() -> None:
    records = [
        {"_lineage_created_at": "not-a-date", "_ingestion_ts": "2026-06-17T12:00:00+00:00"},
        {"_lineage_created_at": datetime(2026, 6, 17, 11, 0, tzinfo=UTC)},
    ]

    assert _resolve_records_metadata_timestamp(records) == datetime(
        2026,
        6,
        17,
        11,
        0,
        tzinfo=UTC,
    )


def test_resolve_metadata_timestamp_uses_fallback_and_errors_without_anchor() -> None:
    fallback = datetime(2026, 6, 17, 10, 0)

    assert _resolve_metadata_timestamp(
        explicit=None,
        records=[{"_lineage_created_at": "bad"}],
        fallback=fallback,
    ) == datetime(2026, 6, 17, 10, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="Deterministic metadata timestamp requires"):
        _resolve_metadata_timestamp(explicit=None, records=[])


def test_get_git_commit_cached_handles_success_failure_and_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="abc123\n"),
    )
    assert _get_git_commit_cached() == "abc123"

    monkeypatch.setattr(
        "subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""),
    )
    assert _get_git_commit_cached() is None

    def _raise_os_error(*_args: object, **_kwargs: object) -> object:
        raise OSError("git unavailable")

    monkeypatch.setattr("subprocess.run", _raise_os_error)
    assert _get_git_commit_cached() is None


def test_metadata_builder_base_composite_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder_base, "_get_git_commit_cached", lambda: "abc123")
    builder = _MetadataBuilderBase(
        transform_version="2.0.0",
        transform_steps=("merge", "publish"),
    )

    runtime, pipeline, lineage = builder._build_composite_runtime_pipeline_lineage(
        table_name="chembl.activity",
        now=datetime(2026, 6, 17, tzinfo=UTC),
        run_id=None,
        sources_used=["silver.chembl_activity"],
    )

    assert runtime.run_id == ""
    assert pipeline.git_commit == "abc123"
    assert lineage.transform_steps == ["merge", "publish"]
    assert lineage.source_tables == {"silver.chembl_activity": 0}


def test_metadata_builder_base_artifact_ids_are_layer_specific() -> None:
    assert "silver:" in _build_silver_artifact_id("chembl.activity", 7)
    assert "gold:" in _build_gold_artifact_id("chembl.activity")
