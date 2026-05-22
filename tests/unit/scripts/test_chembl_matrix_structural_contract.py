"""Unit tests for ChEMBL matrix structural contract export helpers."""

from __future__ import annotations

import pytest

from scripts.docs.chembl_matrix_structural_contract import (
    DEFAULT_REQUIRED_LABEL,
    MatrixStructuralContractRow,
    NOT_APPLICABLE,
    QUARANTINE,
    contract_lookup_key,
    index_runtime_contract_rows,
    build_structural_workbook_semantics,
    resolve_required_display,
    STRUCTURAL_BOOLEAN_VOCABULARY_VALIDATION,
    STRUCTURAL_CUSTOM_EMPTY_SEMANTICS_VALIDATION,
    STRUCTURAL_NO_STRING_COERCION_VALIDATION,
)


@pytest.mark.unit
def test_required_typed_field_gets_presence_and_type_quarantine_tokens() -> None:
    semantics = build_structural_workbook_semantics(
        logical_type="integer",
        nullable=False,
        optional=False,
        empty_as_missing=None,
        coercion_policy="default",
        boolean_true_values=(),
        boolean_false_values=(),
        is_framework_field=False,
    )

    assert semantics.silver_filter_tokens == (
        "structural_presence_guard",
        "structural_type_guard",
    )
    assert semantics.silver_validation_tokens == (
        "structural:presence_required",
        "structural:type_strict",
    )
    assert semantics.validation_fail_action_prefixes == ("quarantine_filter_rejection",)
    assert semantics.filter_fail_sink == QUARANTINE


@pytest.mark.unit
def test_nullable_typed_field_gets_set_null_warn_semantics() -> None:
    semantics = build_structural_workbook_semantics(
        logical_type="float",
        nullable=True,
        optional=True,
        empty_as_missing=None,
        coercion_policy="default",
        boolean_true_values=(),
        boolean_false_values=(),
        is_framework_field=False,
    )

    assert semantics.silver_filter_tokens == ("structural_type_guard",)
    assert semantics.silver_validation_tokens == ("structural:type_to_null_warn",)
    assert semantics.silver_normalisation_tokens == ("invalid_type_to_null",)
    assert semantics.validation_fail_action_prefixes == ("set_null_and_warn",)
    assert semantics.filter_fail_sink == NOT_APPLICABLE


@pytest.mark.unit
def test_optional_nonnullable_typed_field_gets_quarantine_semantics() -> None:
    semantics = build_structural_workbook_semantics(
        logical_type="boolean",
        nullable=False,
        optional=True,
        empty_as_missing=None,
        coercion_policy="default",
        boolean_true_values=(),
        boolean_false_values=(),
        is_framework_field=False,
    )

    assert semantics.silver_filter_tokens == ("structural_type_guard",)
    assert semantics.silver_validation_tokens == (
        "structural:type_proposed_null_warn_error_then_quarantine",
    )
    assert semantics.silver_normalisation_tokens == ("proposed_null_then_quarantine",)
    assert semantics.validation_fail_action_prefixes == (
        "propose_null_warn_error_then_quarantine",
    )
    assert semantics.filter_fail_sink == QUARANTINE


@pytest.mark.unit
def test_framework_field_has_no_structural_tokens() -> None:
    semantics = build_structural_workbook_semantics(
        logical_type="string",
        nullable=False,
        optional=False,
        empty_as_missing=None,
        coercion_policy="default",
        boolean_true_values=(),
        boolean_false_values=(),
        is_framework_field=True,
    )

    assert semantics.silver_filter_tokens == ()
    assert semantics.silver_validation_tokens == ()
    assert semantics.silver_normalisation_tokens == ()
    assert semantics.validation_fail_action_prefixes == ()
    assert semantics.filter_fail_sink == NOT_APPLICABLE


@pytest.mark.unit
def test_resolve_required_display_preserves_richer_non_optional_label() -> None:
    assert (
        resolve_required_display("runtime, filters, schema", optional=False)
        == "runtime, filters, schema"
    )
    assert (
        resolve_required_display("optional", optional=False) == DEFAULT_REQUIRED_LABEL
    )
    assert resolve_required_display("", optional=False) == DEFAULT_REQUIRED_LABEL
    assert resolve_required_display("filters, schema", optional=True) == "optional"


@pytest.mark.unit
def test_overlay_tokens_are_added_to_structural_validation() -> None:
    semantics = build_structural_workbook_semantics(
        logical_type="boolean",
        nullable=True,
        optional=True,
        empty_as_missing=False,
        coercion_policy="no_string_coercion",
        boolean_true_values=("true", "reviewed"),
        boolean_false_values=("false", "unreviewed"),
        is_framework_field=False,
    )

    assert (
        STRUCTURAL_CUSTOM_EMPTY_SEMANTICS_VALIDATION
        in semantics.silver_validation_tokens
    )
    assert (
        STRUCTURAL_NO_STRING_COERCION_VALIDATION in semantics.silver_validation_tokens
    )
    assert (
        STRUCTURAL_BOOLEAN_VOCABULARY_VALIDATION in semantics.silver_validation_tokens
    )


@pytest.mark.unit
def test_runtime_contract_index_uses_case_insensitive_workbook_identity() -> None:
    row = MatrixStructuralContractRow(
        source_db="ChEMBL",
        source_table="activity",
        pipeline="chembl_activity",
        silver_column="activity_id",
        logical_type="string",
        physical_type="str",
        nullable=False,
        optional=False,
        optionality_sources=("silver_required_fields",),
        empty_as_missing=None,
        coercion_policy="default",
        boolean_true_values=(),
        boolean_false_values=(),
        is_framework_field=False,
        silver_filter_tokens=("structural_presence_guard",),
        silver_validation_tokens=("structural:presence_required",),
        silver_normalisation_tokens=(),
        validation_fail_action_prefixes=("quarantine_filter_rejection",),
        filter_fail_sink=QUARANTINE,
    )

    index = index_runtime_contract_rows([row])

    key = contract_lookup_key("chembl", "ACTIVITY", "ACTIVITY_ID")
    assert index[key] == row
