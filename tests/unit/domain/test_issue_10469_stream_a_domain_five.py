"""Stream A domain coverage for #10469 / #10519 (identity, hash, leftovers)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest

import bioetl.domain.serialization as serialization
from bioetl.domain.constants import META_FIELDS
from bioetl.domain.exceptions._redaction import _redact, redact_string
from bioetl.domain.filtering._filter_primitives import (
    check_required_fields,
    check_single_column,
    check_single_list_contains,
    check_single_list_length,
    check_single_range,
    get_list_length,
    is_empty_value,
    to_string_set,
)
from bioetl.domain.filtering.column_filter import FilterOperator, GoldColumnFilter
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.medallion import Layer
from bioetl.domain.normalization._control_plane_identity import (
    build_execution_identity_payload,
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_strict_sha256,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.normalization._reference_id_support import (
    _canonical_or_text,
    _json_fallback,
    _parse_json_array,
    _parse_json_object,
)
from bioetl.domain.normalization.hash_identity import (
    normalize_hash_identity_record,
    normalize_hash_identity_value,
)
from bioetl.domain.normalization.profiles._profile_reference_normalizers import (
    normalize_profile_inchi_key,
    normalize_profile_uniprot_accessions_ordered,
)
from bioetl.domain.normalization.profiles._profile_validation import (
    _normalize_profile_contract,
)
from bioetl.domain.normalization.profiles.base import FieldRule
from bioetl.domain.run_reports.models import WorkflowExecutionRow
from bioetl.domain.run_reports.workflow_totals import (
    _as_int,
    _build_totals,
    _expired_count,
    _measured_current,
    _optional_sum,
    _snapshot_current,
)
from bioetl.domain.serialization import _escape_non_ascii, serialize_to_json
from bioetl.domain.types import BatchID
from bioetl.domain.types._gold_contracts_support import (
    default_rule_id,
    invoke_to_schema,
    normalize_business_key,
    normalize_contract_version as normalize_gold_contract_version,
    normalize_semantic_scope,
)
from bioetl.domain.value_objects.bronze_result import (
    BronzeWriteResult,
    _parse_provider_entity,
)
from bioetl.domain.value_objects.dq_report_builder import (
    BronzeDQReport,
    DQReportSummary,
    DQThresholds,
    SilverDQReport,
)
from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus, DQReportStatus

pytestmark = pytest.mark.unit

_SHA = "a" * 64


def test_control_plane_identity_covers_hash_contract_and_bool_token_errors() -> None:
    assert normalize_control_plane_strict_sha256(None) is None
    assert normalize_control_plane_strict_sha256(f"SHA256:{_SHA.upper()}") == _SHA
    with pytest.raises(ValueError, match="Invalid SHA256"):
        normalize_control_plane_strict_sha256("deadbeef")
    with pytest.raises(ValueError, match="Invalid contract_ref"):
        normalize_contract_ref("CHEMBL Activity")
    assert normalize_contract_version("v1") == "1.0.0"
    with pytest.raises(ValueError, match="numeric semver"):
        normalize_contract_version("1.x")
    with pytest.raises(ValueError, match="X.Y.Z"):
        normalize_contract_version("1.2.3.4")
    payload = build_execution_identity_payload(
        pipeline_name="chembl_activity",
        run_type="INCREMENTAL",
        pipeline_version="1",
        git_commit="ABC",
        effective_config_hash=_SHA,
        dq_contract_compatibility_hash=_SHA,
        contract=("chembl.activity", "v1.2"),
        exact_replay=True,
        dependency_lock_hash=_SHA,
    )
    assert payload["run_type"] == "incremental"
    assert payload["exact_replay"] == "true"
    with pytest.raises(ValueError, match="exact_replay"):
        build_execution_identity_payload(
            pipeline_name="x",
            run_type="full",
            pipeline_version="1",
            git_commit=None,
            effective_config_hash=None,
            dq_contract_compatibility_hash=None,
            exact_replay="maybe",
        )
    anchors = normalize_runtime_anchor_payload(
        {"contract_ref": "Chembl.Activity", "note": "  ", "config_hash": "Ab"}
    )
    assert anchors["contract_ref"] == "chembl.activity"
    assert anchors["note"] is None
    assert anchors["config_hash"] == "ab"


def test_hash_identity_covers_json_string_sets_and_field_filters() -> None:
    assert normalize_hash_identity_value("{", sort_nested_sequences=True) == "{"
    assert (
        normalize_hash_identity_value("{not-json}", sort_nested_sequences=True)
        == "{not-json}"
    )
    assert normalize_hash_identity_value((2, 1), sort_nested_sequences=True) == [1, 2]
    assert normalize_hash_identity_value({2, 1}, sort_nested_sequences=False) == [1, 2]
    record = normalize_hash_identity_record(
        {
            "keep": 1,
            "drop": None,
            "_private": 2,
            next(iter(META_FIELDS)): 3,
            "extra": 4,
            "tags": '["b","a"]',
        },
        exclude_none=True,
        include_fields={"keep", "tags", "extra"},
        exclude_fields={"extra"},
        sort_nested_sequence_fields={"tags"},
    )
    assert record == {"keep": 1, "tags": ["a", "b"]}


def test_profile_reference_and_validation_cover_invalid_and_empty_contracts() -> None:
    assert normalize_profile_inchi_key(None) is None
    assert normalize_profile_inchi_key(1) == 1
    assert normalize_profile_inchi_key("not-a-key") is None
    assert normalize_profile_uniprot_accessions_ordered(1) == 1
    assert normalize_profile_uniprot_accessions_ordered("  ") is None
    assert normalize_profile_uniprot_accessions_ordered("{") is None
    assert normalize_profile_uniprot_accessions_ordered('{"a":1}') is None
    serialized = normalize_profile_uniprot_accessions_ordered('["p12345","P01308"]')
    assert serialized == '["P12345","P01308"]'

    rules = {"name": FieldRule(field_name="name")}
    with pytest.raises(ValueError, match="cannot be empty"):
        _normalize_profile_contract(
            field_rules={}, field_aliases={}, meta_fields=frozenset()
        )
    with pytest.raises(ValueError, match="does not match field_name"):
        _normalize_profile_contract(
            field_rules={"other": FieldRule(field_name="name")},
            field_aliases={},
            meta_fields=frozenset(),
        )
    with pytest.raises(ValueError, match="cannot shadow"):
        _normalize_profile_contract(
            field_rules=rules, field_aliases={"name": "name"}, meta_fields=frozenset()
        )
    with pytest.raises(ValueError, match="missing from field_rules"):
        _normalize_profile_contract(
            field_rules=rules,
            field_aliases={"alias": "missing"},
            meta_fields=frozenset(),
        )
    with pytest.raises(ValueError, match="must be present"):
        _normalize_profile_contract(
            field_rules=rules, field_aliases={}, meta_fields=frozenset({"missing"})
        )
    normalized, aliases = _normalize_profile_contract(
        field_rules=rules,
        field_aliases={"alias": "name"},
        meta_fields=frozenset({"name"}),
    )
    assert list(normalized) == ["name"]
    assert aliases["alias"] == "name"


def test_workflow_totals_and_serialization_cover_invalid_counts_and_stdlib() -> None:
    assert _as_int(None) == 0
    assert _as_int(object()) == 0
    assert _as_int("nope") == 0
    empty = WorkflowExecutionRow(step_id="a", status="unknown", records_extracted=1)
    assert _optional_sum([empty], "records_silver") is None
    assert _snapshot_current({"source_snapshot": "x"}) is None
    assert _measured_current(empty, {"dry_run": True}) is None
    assert (
        _measured_current(
            WorkflowExecutionRow(step_id="a", status="success", records_extracted=1),
            {"source_scope": "limited", "mutation_mode": "gold_scd2_expiry"},
        )
        is None
    )
    assert _expired_count({"mutation_mode": "no_op"}) == 0
    totals = _build_totals(
        (
            WorkflowExecutionRow(
                step_id="reconcile",
                status="success",
                records_extracted=0,
                records_gold=4,
                gold_excluded_by_contract=1,
                reconciliation={
                    "source_layer": "gold",
                    "source_table": "activity",
                    "source_scope": "all_current",
                    "mutation_mode": "gold_scd2_expiry",
                    "orphan_rows_deleted": "2",
                    "source_snapshot": {"physical_rows": 9, "current_rows": 4},
                },
            ),
        ),
        planned=1,
    )
    assert totals["records_gold_expired_sum"] == 2
    assert totals["final_current_by_table"] == {"activity": 4}

    assert "\\ud83d\\udc4b" in _escape_non_ascii("👋")
    serialization.is_orjson_available.cache_clear()
    original = serialization._orjson_available
    serialization._orjson_available = False
    try:
        assert serialize_to_json({"b": 1, "a": 2}, sort_keys=False) in {
            '{"b":1,"a":2}',
            '{"a":2,"b":1}',
        }
        with pytest.raises(ValueError, match="NaN or Infinity"):
            serialize_to_json({"nested": [float("nan")]})
    finally:
        serialization._orjson_available = original
        serialization.is_orjson_available.cache_clear()


def test_redaction_filter_support_and_gold_helpers_cover_edge_branches() -> None:
    assert "[REDACTED]" in redact_string('password="secret\\"value" leftover')
    assert "[REDACTED]" in redact_string("https://user:pass@example.com:8080/x?q=1")
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    assert _redact(cyclic)["self"] == "[REDACTED CYCLE]"
    assert is_empty_value({}) is True
    assert is_empty_value(b"x") is False
    assert check_required_fields(("id",), {"id": " "}) is False
    assert check_single_column(
        {"status": "open"},
        GoldColumnFilter("status", FilterOperator.IN, frozenset({"open"})),
    )
    unknown = SimpleNamespace(column="status", operator="nope", values=frozenset({"x"}))
    assert check_single_column({"status": "open"}, unknown) is False  # type: ignore[arg-type]
    assert (
        check_single_range(
            {"n": "x"}, GoldRangeFilter("n", min_value=1.0, include_min=False)
        )
        is False
    )
    assert (
        check_single_range(
            {"n": 2}, GoldRangeFilter("n", min_value=2.0, include_min=False)
        )
        is False
    )
    assert get_list_length("[") == 1
    assert get_list_length("[1,2]") == 2
    assert to_string_set("not-list") == {"not-list"}
    assert (
        check_single_list_length(
            {"tags": None}, GoldListLengthFilter("tags", min_length=0)
        )
        is True
    )
    contains = GoldListContainsFilter("tags", frozenset({"a"}), mode="any")
    assert check_single_list_contains({}, contains) is True
    assert check_single_list_contains({"tags": None}, contains) is True
    assert check_single_list_contains({"tags": ["a", "b"]}, contains) is True

    assert invoke_to_schema(object()) is None
    assert normalize_business_key([" a ", "b"]) == ("a", "b")
    with pytest.raises(ValueError, match="string or a non-empty sequence"):
        normalize_business_key(1)
    assert normalize_gold_contract_version(None) == "0.0.0"
    assert normalize_semantic_scope("profile") == "profile"
    with pytest.raises(ValueError, match="semantic_scope"):
        normalize_semantic_scope("other")
    assert default_rule_id("gold", None) == "gold.record"

    assert _parse_json_array("  ") is None
    assert _parse_json_object("{") is None
    assert _canonical_or_text(1, normalizer=lambda text: text.upper()) == 1
    assert _json_fallback(1) == 1

    with pytest.raises(ValueError, match="parent-directory"):
        _parse_provider_entity("chembl/../activity")
    with pytest.raises(ValueError, match="provider/entity"):
        _parse_provider_entity("chembl")
    result = BronzeWriteResult(
        batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000201")),
        relative_path="v1/chembl/activity/batch.jsonl",
        absolute_path="/data/bronze/v1/chembl/activity/batch.jsonl",
        record_count=0,
        compressed_size=0,
        uncompressed_size=8,
        checksum_blake2="abc",
    )
    assert result.compression_ratio == 1.0
    assert result.provider_entity == ("chembl", "activity")

    summary = DQReportSummary(1, 1, 0, 0, DQReportStatus.PASS)
    with pytest.raises(ValueError, match="timezone-aware"):
        BronzeDQReport(
            layer=Layer.BRONZE,
            timestamp=datetime(2026, 1, 1),
            run_id="r",
            pipeline="p",
            batch_id="b",
            source_file="f",
            checks={},
            summary=summary,
        )
    with pytest.raises(ValueError, match="zero UTC offset"):
        BronzeDQReport(
            layer=Layer.BRONZE,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=3))),
            run_id="r",
            pipeline="p",
            batch_id="b",
            source_file="f",
            checks={},
            summary=summary,
        )
    with pytest.raises(ValueError, match="must be BRONZE"):
        BronzeDQReport(
            layer=Layer.SILVER,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            run_id="r",
            pipeline="p",
            batch_id="b",
            source_file="f",
            checks={},
            summary=summary,
        )
    silver = SilverDQReport(
        layer=Layer.SILVER,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        run_id="r",
        pipeline="p",
        source_batch_ids=["b1"],  # type: ignore[arg-type]
        target_table="t",
        checks={},
        thresholds=DQThresholds(0.1, 0.2, 0.0, DQCheckStatus.PASS),
        summary=summary,
    )
    assert silver.source_batch_ids == ("b1",)
