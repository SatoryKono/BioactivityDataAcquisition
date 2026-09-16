"""Behavioral tests for optional pipeline report enrichment blocks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.run_reports.enrichment import (
    _filter_metadata,
    _hash_ids,
    build_artifacts_from_result,
    build_dq_summary,
    build_failure_block,
    build_http_summary,
    build_io_block,
    build_quarantine_block,
    build_schema_versions,
    build_stage_timings,
)

pytestmark = pytest.mark.unit


def _result(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "debug_export_uri": None,
        "debug_export_hash": None,
        "status": SimpleNamespace(value="success"),
        "error_type": None,
        "error_message": None,
        "pipeline_name": "chembl_activity",
        "run_type": "incremental",
        "records_quarantined": 0,
        "records_filtered_out": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _options(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "run_type": None,
        "limit": None,
        "start_offset": None,
        "input_csv": None,
        "filter_column": None,
        "filter_field": None,
        "skip_gold": False,
        "dry_run": False,
        "use_cached_bronze": False,
        "cached_bronze_path": None,
        "filter_ids": None,
        "multi_filter_ids": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_artifacts_from_result_handles_absent_and_hashed_export() -> None:
    assert build_artifacts_from_result(_result()) == ()
    assert build_artifacts_from_result(
        _result(debug_export_uri="debug.xlsx", debug_export_hash="sha256:abc")
    ) == ({"kind": "debug_export", "ref": "debug.xlsx", "hash": "sha256:abc"},)
    assert build_artifacts_from_result(_result(debug_export_uri="debug.xlsx")) == (
        {"kind": "debug_export", "ref": "debug.xlsx"},
    )


@pytest.mark.parametrize("status", ["success", "dry_run"])
def test_build_failure_block_omits_successful_runs(status: str) -> None:
    assert build_failure_block(_result(status=SimpleNamespace(value=status))) is None
    assert (
        build_failure_block(
            _result(
                status=SimpleNamespace(value=status),
                error_type="ignored",
                error_message="ignored",
            )
        )
        is None
    )


@pytest.mark.parametrize(
    ("status", "error_type", "hint"),
    [
        ("shutdown", None, "shutdown signal"),
        ("failed", "ValidationError", "Investigate ValidationError"),
        ("failed", None, "Inspect pipeline logs"),
    ],
)
def test_build_failure_block_explains_non_successful_runs(
    status: str, error_type: str | None, hint: str
) -> None:
    block = build_failure_block(
        _result(
            status=SimpleNamespace(value=status),
            error_type=error_type,
            error_message="boom",
        )
    )
    assert block is not None
    assert hint in block["exit_hint"]


def test_build_io_block_supports_result_only_and_bounded_filter_metadata() -> None:
    assert build_io_block(_result(), options=None) == {
        "pipeline_name": "chembl_activity",
        "run_type": "incremental",
    }
    block = build_io_block(
        _result(),
        options=_options(
            run_type="backfill",
            filter_field="molecule_id",
            filter_ids=["b", "a"],
            multi_filter_ids={"target_id": ["T1", "T2"]},
        ),
    )
    assert block is not None
    assert block["run_type"] == "backfill"
    assert block["filter_column"] == "molecule_id"
    assert block["filter_id_count"] == 2
    assert block["filter_id_hash"] == _hash_ids(["a", "b"])
    assert block["multi_filter_id_counts"] == {"target_id": 2}
    assert "limit" not in block


def test_filter_metadata_omits_empty_selectors() -> None:
    assert _filter_metadata([], {}) == {
        "filter_id_count": None,
        "filter_id_hash": None,
        "multi_filter_id_counts": None,
    }


def test_quarantine_block_uses_count_or_reasons() -> None:
    assert build_quarantine_block(_result(), reasons_top_n=[]) is None
    assert build_quarantine_block(
        _result(records_quarantined=2),
        reasons_top_n=[
            {"reason_code": "Q", "outcome": "quarantined", "count": 2},
            {"reason_code": "F", "outcome": "filtered_out", "count": 1},
        ],
    ) == {
        "records_quarantined": 2,
        "top_reasons": [{"reason_code": "Q", "outcome": "quarantined", "count": 2}],
    }


def test_dq_summary_recognizes_family_prefix_and_schema_reason() -> None:
    assert build_dq_summary(_result(), reasons_top_n=[]) is None
    reasons = [
        {"reason_code": "CUSTOM", "reason_family": "dq", "count": 1},
        {"reason_code": "dq_range", "count": 2},
        {"reason_code": "SCHEMA_VALIDATION_FAILURE", "count": 3},
        {"reason_code": "OTHER", "count": 4},
    ]
    summary = build_dq_summary(
        _result(records_filtered_out=3, records_quarantined=1),
        reasons_top_n=reasons,
    )
    assert summary is not None
    assert [item["reason_code"] for item in summary["reasons"]] == [
        "CUSTOM",
        "dq_range",
        "SCHEMA_VALIDATION_FAILURE",
    ]


def test_schema_versions_only_adds_available_fingerprints() -> None:
    assert build_schema_versions(reason_catalog_version="v1") == {
        "reason_catalog_version": "v1"
    }
    assert build_schema_versions(
        reason_catalog_version="v1",
        package_version="1.2.3",
        config_digest="cfg",
        execution_fingerprint="exec",
        entity_contract_id="contract",
    ) == {
        "reason_catalog_version": "v1",
        "bioetl_version": "1.2.3",
        "config_digest": "cfg",
        "execution_fingerprint": "exec",
        "entity_contract_id": "contract",
    }


def test_stage_timings_filters_missing_and_invalid_values() -> None:
    assert build_stage_timings(None) is None
    assert build_stage_timings({"extract": None, "load": "bad"}) is None
    assert build_stage_timings({"extract": 1, "transform": "2.5"}) == {
        "extract": 1.0,
        "transform": 2.5,
    }


def test_http_summary_allows_only_known_measured_fields() -> None:
    assert build_http_summary(None) is None
    assert build_http_summary({"unknown": 1, "request_count": None}) is None
    assert build_http_summary(
        {"request_count": 3, "retry_count": 1, "secret": "drop"}
    ) == {"request_count": 3, "retry_count": 1}
