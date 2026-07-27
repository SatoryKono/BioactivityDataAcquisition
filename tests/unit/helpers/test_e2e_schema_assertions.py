"""Unit tests for E2E schema assertion helpers (T-09)."""

from __future__ import annotations

import pytest

from tests.helpers.e2e_schema_assertions import (
    assert_optional_numeric_in_range,
    assert_records_have_required_fields,
)

pytestmark = pytest.mark.unit


def test_assert_records_have_required_fields_accepts_valid_rows() -> None:
    assert_records_have_required_fields(
        [{"assay_id": "A1", "assay_type": "B"}, {"assay_id": "A2", "assay_type": "F"}],
        ("assay_id", "assay_type"),
        entity_label="assay",
    )


def test_assert_records_have_required_fields_rejects_blank_and_missing() -> None:
    with pytest.raises(AssertionError, match="must not be blank"):
        assert_records_have_required_fields(
            [{"assay_id": "  ", "assay_type": "B"}],
            ("assay_id", "assay_type"),
            entity_label="assay",
        )
    with pytest.raises(AssertionError, match="must not be None"):
        assert_records_have_required_fields(
            [{"assay_id": "A1", "assay_type": None}],
            ("assay_id", "assay_type"),
            entity_label="assay",
        )


def test_assert_optional_numeric_in_range() -> None:
    assert_optional_numeric_in_range(
        [{"confidence_score": 4}, {"confidence_score": None}],
        "confidence_score",
        minimum=0,
        maximum=9,
        entity_label="assay",
    )
    with pytest.raises(AssertionError, match="outside"):
        assert_optional_numeric_in_range(
            [{"confidence_score": 12}],
            "confidence_score",
            minimum=0,
            maximum=9,
            entity_label="assay",
        )
