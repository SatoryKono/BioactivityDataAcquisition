"""Unit tests for debug export helper functions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PureWindowsPath
from uuid import UUID

import pytest

import bioetl.application.services.debug_export_helpers as helpers
from bioetl.domain.types import ErrorType

pytestmark = pytest.mark.unit


@dataclass
class _ModelDumpPayload:
    value: str

    def model_dump(self) -> dict[str, object]:
        return {"value": self.value}


@dataclass
class _DictPayload:
    value: str


class _NonMappingModelDump:
    def model_dump(self) -> object:
        return ["not", "a", "mapping"]


class _NoPayloadState:
    __slots__ = ()


def test_utc_now_is_timezone_aware() -> None:
    now = helpers._utc_now()

    assert now.tzinfo is UTC


def test_record_payload_and_json_helpers_cover_mapping_model_and_object_payloads() -> (
    None
):
    assert helpers._record_payload(None) == {}
    assert helpers._record_payload({"value": "ok"}) == {"value": "ok"}
    assert helpers._record_payload(_ModelDumpPayload("dumped")) == {"value": "dumped"}
    assert helpers._record_payload(_DictPayload("attr")) == {"value": "attr"}
    assert helpers._record_payload(_NonMappingModelDump()) == {}
    assert helpers._record_payload(_NoPayloadState()) == {}

    payload = {
        "created_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "path": Path("/tmp/debug"),
        "uuid": UUID("00000000-0000-0000-0000-000000000123"),
    }
    rendered = helpers._jsonable_payload(payload)
    assert "2026-01-01T12:00:00+00:00" in rendered
    assert "/tmp/debug" in rendered
    assert "00000000-0000-0000-0000-000000000123" in rendered
    assert helpers._json_default(PureWindowsPath(r"\tmp\debug")) == "/tmp/debug"
    assert helpers._jsonable_value({"a": 1}) == '{"a": 1}'
    assert helpers._json_default(date(2026, 1, 2)) == "2026-01-02"
    assert helpers._json_default(UUID("00000000-0000-0000-0000-000000000456")) == (
        "00000000-0000-0000-0000-000000000456"
    )
    assert helpers._jsonable_value(None) == "null"
    assert helpers._json_default(object()).startswith("<object object at ")


def test_identity_helpers_cover_primary_key_source_id_and_normalization() -> None:
    payload = {"entity_id": "entity-1", "activity_id": "activity-1"}
    assert helpers._normalize_text(None) == ""
    assert helpers._normalize_optional_text("  value  ") == "value"
    assert helpers._normalize_optional_text("   ") is None
    assert helpers._primary_key(payload) == "entity-1"
    assert helpers._primary_key({"activity_id": "ACT-1"}) == "ACT-1"
    assert helpers._primary_key({"missing": True}) == ""
    assert helpers._source_record_id({"activity_id": "ACT-1"}) == "ACT-1"
    assert helpers._source_record_id({"activity_id": " ", "id": "fallback-id"}) == (
        "fallback-id"
    )
    assert helpers._source_record_id({"missing": True}) == ""


def test_rule_and_rejection_diagnostics_helpers_cover_mapping_and_fallbacks() -> None:
    record = {"target_chembl_id": None, "rule_name": "required"}
    assert helpers._infer_failed_field(record, "missing target_chembl_id value") == (
        "target_chembl_id"
    )
    assert helpers._infer_failed_field(record, "missing assay value") == ""
    assert helpers._extract_rule_id("validation rules=[rule.alpha] failed") == (
        "rule.alpha"
    )
    assert helpers._extract_rule_id("no rules here") == ""

    details = {
        "field": "target_chembl_id",
        "operator": "not_in",
        "expected": ["A", "B"],
        "actual": None,
    }
    failed_field, failed_value, expected_constraint = (
        helpers._extract_rejection_diagnostics(
            record=record,
            details=details,
            message="target_chembl_id mismatch",
        )
    )
    assert failed_field == "target_chembl_id"
    assert failed_value == "None"
    assert expected_constraint == 'not_in ["A", "B"]'

    inferred = helpers._extract_rejection_diagnostics(
        record=record,
        details=None,
        message="missing target_chembl_id value",
    )
    assert inferred == ("target_chembl_id", "", "")

    model_dump_details = helpers._extract_rejection_details_mapping(
        _ModelDumpPayload("x")
    )
    assert model_dump_details == {"value": "x"}
    assert helpers._extract_rejection_details_mapping(_NonMappingModelDump()) == {}
    assert helpers._extract_rejection_details_mapping(_DictPayload("attr")) == {
        "value": "attr"
    }
    assert helpers._extract_rejection_details_mapping(_NoPayloadState()) is None

    assert (
        helpers._extract_expected_constraint_from_details({"expected": None}) == "None"
    )
    assert (
        helpers._extract_expected_constraint_from_details(
            {"operator": ">", "expected": True}
        )
        == "> True"
    )
    assert helpers._extract_expected_constraint_from_details({"expected": 7}) == "7"
    assert (
        helpers._extract_expected_constraint_from_details({"constraint": ">= 0"})
        == ">= 0"
    )
    assert (
        helpers._extract_expected_constraint_from_details({"check": "not blank"})
        == "not blank"
    )

    complex_actual = helpers._extract_rejection_diagnostics(
        record={"target_chembl_id": {"nested": True}},
        details={"field": "target_chembl_id", "actual": {"nested": True}},
        message="nested value",
    )
    assert complex_actual == ("target_chembl_id", '{"nested": true}', "")

    inferred_from_record = helpers._extract_rejection_diagnostics(
        record={"target_chembl_id": None},
        details={"field": "target_chembl_id"},
        message="record fallback",
    )
    assert inferred_from_record == ("target_chembl_id", "None", "")

    scalar_from_record = helpers._extract_rejection_diagnostics(
        record={"target_chembl_id": "CHEMBL1"},
        details={"field": "target_chembl_id"},
        message="record scalar fallback",
    )
    assert scalar_from_record == ("target_chembl_id", "CHEMBL1", "")

    inferred_complex_from_record = helpers._extract_rejection_diagnostics(
        record={"target_chembl_id": {"nested": True}},
        details={"field": "target_chembl_id"},
        message="record complex fallback",
    )
    assert inferred_complex_from_record == (
        "target_chembl_id",
        '{"nested": true}',
        "",
    )


def test_reason_hash_and_sort_helpers_cover_branch_variants() -> None:
    assert (
        helpers._infer_reason_code(
            error_type=ErrorType.SCHEMA_VIOLATION,
            details="schema failed",
        )
        == "SCHEMA_TYPE_MISMATCH"
    )
    assert (
        helpers._infer_reason_code(
            details="runtime dq validation failed on hard rule",
        )
        == "DQ_HARD_RULE_FAILED"
    )
    assert (
        helpers._infer_reason_code(
            details="field target_id missing",
        )
        == "SCHEMA_REQUIRED_FIELD_MISSING"
    )
    assert helpers._infer_reason_code(policy="quarantine") == "QUARANTINE_POLICY"
    assert helpers._infer_reason_code(details="soft failure") == "DQ_SOFT_RULE_FAILED"

    explicit_hash = helpers._payload_hash(
        provider_id="chembl",
        record={"content_hash": "sha256:existing"},
    )
    assert explicit_hash == "sha256:existing"
    computed_hash = helpers._payload_hash(
        provider_id="chembl",
        record={"activity_id": "ACT-1", "value": "x"},
    )
    assert computed_hash
    blank_existing_hash = helpers._payload_hash(
        provider_id="chembl",
        record={"activity_id": "ACT-1", "content_hash": " "},
    )
    assert blank_existing_hash
    assert blank_existing_hash != " "
    assert helpers._payload_hash(provider_id="chembl", record=None) == ""
    assert helpers._row_sort_key(
        {"record_index": "5", "primary_key": "B", "payload_hash": "H"}
    ) == (5, "B", "H")
    assert helpers._row_sort_key(
        {"record_index": 5.9, "primary_key": "B", "payload_hash": "H"}
    ) == (5, "B", "H")
    assert helpers._row_sort_key(
        {"record_index": "bad", "primary_key": "B", "payload_hash": "H"}
    ) == (None, "B", "H")
    assert helpers._row_sort_key(
        {"record_index": object(), "primary_key": None, "payload_hash": None}
    ) == (None, "", "")
    assert helpers._lineage_sort_key(
        {"fragment_id": "f", "edge_type": "e", "node_id": "n"}
    ) == ("f", "e", "n")
    assert helpers._lineage_sort_key({}) == ("", "", "")


def test_base_row_contains_json_payloads_and_hashes() -> None:
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    row = helpers._base_row(
        run_id="run-1",
        workflow_id="wf-1",
        pipeline_id="chembl_activity",
        provider_id="chembl",
        stage="silver",
        record_index=7,
        raw_record={"activity_id": "ACT-1"},
        normalized_record={"entity_id": "entity-1"},
        status="success",
        created_at=created_at,
        reason_code="OK",
        reason_message="done",
        action="keep",
    )

    assert row["source_record_id"] == "ACT-1"
    assert row["primary_key"] == "entity-1"
    assert row["created_at"] == "2026-01-01T12:00:00+00:00"
    assert '"activity_id": "ACT-1"' in row["raw_payload"]
    assert '"entity_id": "entity-1"' in row["normalized_payload"]
