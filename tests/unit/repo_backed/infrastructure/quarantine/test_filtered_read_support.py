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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for quarantine filtered-row support helpers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def _load_filtered_read_support() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[5]
        / "src/bioetl/infrastructure/quarantine/filtered_read_support.py"
    )
    module_name = "bioetl.infrastructure.quarantine.filtered_read_support"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


support = _load_filtered_read_support()


def test_error_details_normalization_accepts_json_mapping_only() -> None:
    assert support._normalize_error_details(
        {"error_details": '{"reason_code":"DQ","field":"assay_id"}'}
    ) == {"reason_code": "DQ", "field": "assay_id"}
    assert support._normalize_error_details({"error_details": "[1,2]"}) == {}
    with pytest.raises(ValueError, match="Invalid JSON"):
        support._normalize_error_details({"error_details": "not-json"})
    assert support._normalize_error_details(
        {"error_details": {"reason_code": "DQ"}}
    ) == {"reason_code": "DQ"}
    assert support._normalize_error_details({"error_details": None}) == {}


def test_counter_and_reason_signatures_skip_blank_or_non_string_values() -> None:
    counter: dict[str, int] = {}

    support._increment_counter(counter, " DQ ")
    support._increment_counter(counter, "DQ")
    support._increment_counter(counter, "")
    support._increment_counter(counter, 7)

    assert counter == {"DQ": 2}
    assert (
        support._build_reason_signature(
            {
                "reason_code": "DQ",
                "rule_type": "schema",
                "field": "assay_id",
                "operator": "required",
            }
        )
        == "DQ | schema | assay_id | required"
    )
    assert support._build_reason_signature({"reason_code": " "}) is None
    assert (
        support._build_reason_field_signature(
            {"reason_code": "DQ", "field": "assay_id", "operator": "ignored"}
        )
        == "DQ | assay_id"
    )
    assert support._build_reason_field_signature({"field": ""}) is None


def test_timestamp_normalization_covers_datetime_strings_and_invalid_values() -> None:
    naive = datetime(2026, 7, 5, 12, 0, 0)
    aware = datetime(2026, 7, 5, 12, 0, 0, tzinfo=UTC)

    assert support._normalize_timestamp(naive) == (
        "2026-07-05T12:00:00+00:00",
        aware,
    )
    assert support._normalize_timestamp(aware) == (
        "2026-07-05T12:00:00+00:00",
        aware,
    )
    assert support._normalize_timestamp("2026-07-05T12:00:00Z") == (
        "2026-07-05T12:00:00Z",
        aware,
    )
    assert support._normalize_timestamp("2026-07-05T12:00:00") == (
        "2026-07-05T12:00:00",
        aware,
    )
    assert support._normalize_timestamp("not-a-date") == ("not-a-date", None)
    assert support._normalize_timestamp("  ") == ("", None)
    assert support._normalize_timestamp(cast(Any, 7)) == ("", None)


def test_payload_preview_truncates_dicts_and_wraps_scalar_values() -> None:
    payload = {f"k{i}": i for i in range(10)}

    preview = support._build_payload_preview(payload)

    assert list(preview) == [f"k{i}" for i in range(8)] + ["_truncated_keys"]
    assert preview["_truncated_keys"] == 2
    assert support._build_payload_preview(["not", "mapping"]) == {
        "value": ["not", "mapping"]
    }


def test_normalize_filtered_row_resolves_reason_run_type_and_payload_options() -> None:
    record = {
        "ingestion_ts": "2026-07-05T12:00:00Z",
        "pipeline": "chembl_activity",
        "run_id": "run-1",
        "payload_hash": "hash-1",
        "dq_status": "filtered",
        "error_code": "fallback",
        "payload": '{"a":1,"b":2}',
        "error_details": {
            "message": " rejected ",
            "reason_code": "DQ",
            "rule_type": "schema",
            "field": "assay_id",
            "operator": "required",
            "expected": "present",
            "actual": None,
        },
    }

    normalized = support._normalize_filtered_row(
        record,
        run_type_lookup={"run-1": "scheduled"},
        include_payload=True,
        include_payload_preview=False,
    )

    assert normalized["reason"] == "rejected"
    assert normalized["run_type"] == "scheduled"
    assert normalized["payload_preview"] == {"a": 1, "b": 2}
    assert normalized["payload"] == {"a": 1, "b": 2}

    record_with_embedded_run_type = {
        "run_id": "run-2",
        "error_code": "fallback",
        "payload": ["raw"],
        "error_details": {"_run_type": "manual", "message": " "},
    }
    normalized_preview = support._normalize_filtered_row(
        record_with_embedded_run_type,
        run_type_lookup={"run-2": "scheduled"},
        include_payload=False,
        include_payload_preview=True,
    )
    assert normalized_preview["run_type"] == "manual"
    assert normalized_preview["reason"] == "fallback"
    assert normalized_preview["payload_preview"] == {"value": ["raw"]}
    assert "payload" not in normalized_preview


def test_filter_value_helpers_handle_wildcards_lists_and_singletons() -> None:
    assert support._normalize_filter_values(None) is None
    assert support._normalize_filter_values("  ") is None
    assert support._normalize_filter_values("*") is None
    assert support._normalize_filter_values("all") is None
    assert support._normalize_filter_values("A,,*, B , A") == {"A", "B"}
    assert support._single_filter_value(" only ") == "only"
    assert support._single_filter_value("A,B") is None
    assert support._single_filter_value("*") is None


def test_collect_values_and_limit_clamping() -> None:
    rows = [{"pipeline": " A "}, {"pipeline": "B"}, {"pipeline": ""}, {"pipeline": 7}]

    assert support._collect_string_field_values(rows, "pipeline") == ["A", "B"]
    assert support._clamp_limit(0) == 50
    assert support._clamp_limit(-5, default=10) == 10
    assert support._clamp_limit(25) == 25
    assert support._clamp_limit(999, hard_cap=100) == 100


def test_iter_filtered_rows_applies_text_and_time_filters() -> None:
    records = [
        {
            "ingestion_ts": "2026-07-05T12:00:00Z",
            "pipeline": "chembl_activity",
            "run_id": "run-1",
            "payload_hash": "hash-1",
            "error_details": (
                '{"reason_code":"DQ","field":"assay_id","run_type":"scheduled"}'
            ),
        },
        {
            "ingestion_ts": "2026-07-06T12:00:00Z",
            "pipeline": "chembl_target",
            "run_id": "run-2",
            "payload_hash": "hash-2",
            "error_details": '{"reason_code":"SCHEMA","field":"target_id"}',
        },
        {
            "ingestion_ts": "not-a-date",
            "pipeline": "chembl_activity",
            "run_id": "run-3",
            "payload_hash": "hash-3",
            "error_details": '{"reason_code":"DQ","field":"assay_id"}',
        },
    ]

    rows = support._iter_filtered_rows(
        records,
        run_type_lookup={"run-3": "manual"},
        pipeline="chembl_activity",
        run_type="scheduled,manual",
        reason_code="DQ",
        field="assay_id",
        run_id="run-1,run-3",
        payload_hash="hash-1,hash-3",
        from_ts="2026-07-05T00:00:00Z",
        to_ts="2026-07-05T23:59:59Z",
        include_payload=False,
        include_payload_preview=False,
    )

    assert [row["run_id"] for row in rows] == ["run-1"]

    rows_without_time_bounds = support._iter_filtered_rows(
        records,
        run_type_lookup={"run-3": "manual"},
        pipeline="$__all",
        run_type=None,
        reason_code=None,
        field=None,
        run_id=None,
        payload_hash=None,
        from_ts="not-a-date",
        to_ts=" ",
        include_payload=False,
        include_payload_preview=False,
    )
    assert [row["run_id"] for row in rows_without_time_bounds] == [
        "run-1",
        "run-2",
        "run-3",
    ]
