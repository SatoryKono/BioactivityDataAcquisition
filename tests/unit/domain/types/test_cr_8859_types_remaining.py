# pyright: reportArgumentType=false
"""Focused tests for remaining S01-domain-types residuals (#8895)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.types._checkpoint_metadata_support import coerce_snapshot_ids
from bioetl.domain.types._gold_contracts_support import coerce_mapping, invoke_to_schema
from bioetl.domain.types.checkpoint_compatibility_result import (
    CheckpointCompatibilityResult,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.types.contract_identity import (
    ContractIdentity,
    _has_contract_ref_namespace,
)
from bioetl.domain.types.debug_export import DebugExportPack
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.domain.types.gold_contracts_rejects import (
    GoldRejectReason,
    GoldRejectReasonCode,
)
from bioetl.domain.types.gold_contracts_rules import GoldBusinessRuleSpec
from bioetl.domain.types.gold_contracts_scd import ScdConfig

pytestmark = pytest.mark.unit


def test_incompatible_result_does_not_claim_proven_identity() -> None:
    result = CheckpointCompatibilityResult.incompatible_result()
    assert result.identity_continuity_proven is False
    assert result.execution_identity_compatible is False


def test_compatibility_messages_are_immutable_and_hashable() -> None:
    result = CheckpointCompatibilityResult.incompatible_result(
        messages=["a", "b"],
    )
    assert result.messages == ("a", "b")
    with pytest.raises(TypeError):
        result.messages[0] = "x"  # type: ignore[index]
    assert isinstance(hash(result), int)


def test_coerce_snapshot_ids_skips_non_strings() -> None:
    assert coerce_snapshot_ids([None, 1, " a ", "a", ""]) == ("a",)


def test_records_processed_coerces_string_and_null() -> None:
    assert (
        CheckpointMetadata.from_legacy_metadata(
            {"records_processed": "10"}
        ).records_processed
        == 10
    )
    assert (
        CheckpointMetadata.from_legacy_metadata(
            {"records_processed": None}
        ).records_processed
        == 0
    )
    with pytest.raises(ValueError, match="integer"):
        CheckpointMetadata.from_legacy_metadata({"records_processed": True})


def test_snapshot_ids_and_refs_share_fingerprint() -> None:
    ids_only = CheckpointMetadata(records_processed=1, input_snapshot_ids=("s1",))
    refs_only = CheckpointMetadata(
        records_processed=1,
        input_snapshot_refs=({"snapshot_id": "s1"},),
    )
    assert (
        ids_only.checkpoint_execution_identity_payload()["input_snapshot_fingerprint"]
        == refs_only.checkpoint_execution_identity_payload()[
            "input_snapshot_fingerprint"
        ]
    )


def test_extract_fallback_strips_and_stringifies() -> None:
    metadata = CheckpointMetadata.from_dict(
        {"records_processed": 1, "pipeline_name": "  pipe  "}
    )
    assert metadata.pipeline_name == "pipe"


def test_contract_ref_rejects_empty_segments() -> None:
    assert _has_contract_ref_namespace("chembl.molecule.v1") is True
    assert _has_contract_ref_namespace(".") is False
    assert _has_contract_ref_namespace("..") is False
    assert _has_contract_ref_namespace(".v1.0.0") is False
    with pytest.raises(ValueError, match="cannot be empty"):
        ContractIdentity.from_legacy("", "1.0.0")


def test_gold_details_and_mapping_are_immutable() -> None:
    mapping = coerce_mapping({"a": 1})
    with pytest.raises(TypeError):
        mapping["a"] = 2  # type: ignore[index]
    reason = GoldRejectReason(
        reason_code=GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE,
        details={"a": 1},
    )
    with pytest.raises(TypeError):
        reason.details["a"] = 2  # type: ignore[index]


def test_invoke_to_schema_propagates_value_error() -> None:
    class Boom:
        def to_schema(self) -> object:
            raise ValueError("schema invalid")

    with pytest.raises(ValueError, match="schema invalid"):
        invoke_to_schema(Boom())


def test_affected_fields_are_immutable() -> None:
    outcome = DQRuleOutcome(
        "r",
        DQViolationKind.SCHEMA_VIOLATION,
        "high",
        DQDisposition.FAIL,
        affected_fields=["id"],
    )
    assert outcome.affected_fields == ("id",)
    with pytest.raises((TypeError, AttributeError)):
        outcome.affected_fields.append("x")  # type: ignore[attr-defined]
    assert isinstance(hash(outcome), int)


def test_debug_export_pack_freezes_nested_tables() -> None:
    row = {"k": 1}
    pack = DebugExportPack(
        run_id="r",
        pipeline_id="p",
        provider_id="pr",
        workflow_id="w",
        manifest_id=None,
        status="ok",
        output_root="/tmp",
        formats=("csv",),
        include_bom=False,
        max_rows_per_sheet=1,
        created_at=datetime(2026, 8, 17, tzinfo=UTC),
        tables={"t": (row,)},
        reason_dictionary=({"code": "x"},),
    )
    row["k"] = 9
    assert pack.tables["t"][0]["k"] == 1
    with pytest.raises(TypeError):
        pack.tables["t"][0]["k"] = 2  # type: ignore[index]
    assert isinstance(hash(pack), int)


def test_inverted_numeric_range_is_rejected() -> None:
    with pytest.raises(ValueError, match="minimum cannot exceed maximum"):
        GoldBusinessRuleSpec(column="x", condition="range", minimum=10, maximum=1)


def test_scd_type_rejects_bool() -> None:
    with pytest.raises(ValueError, match="integer"):
        ScdConfig.from_mapping({"type": True, "business_key": "id"})
