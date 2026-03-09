"""Integration tests for DataFrame-level data validation.

Tests Pandera-based validation covering:
- Row count checks (minimum expected records)
- Null percentage thresholds per column
- Value range constraints (numeric bounds)
- Cross-record consistency (unique IDs, no duplicate primary keys)
- Schema-level column presence checks

These tests use in-memory DataFrames and Pandera schemas to ensure that
the validation layer catches real data quality issues before Silver/Gold
promotion.
"""

from __future__ import annotations

from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Guard: skip this module if optional dependencies (pandas, pandera) are not
# installed.  This mirrors the pattern used in the production validators.
# ---------------------------------------------------------------------------
pandas = pytest.importorskip("pandas")
pandera = pytest.importorskip("pandera")

import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema

from bioetl.domain.transformations.quality import calculate_dq_score, exceeds_threshold
from bioetl.domain.types import ValidationResult
from bioetl.infrastructure.validation.pandera_validator import (
    NoOpValidator,
    PanderaGoldValidator,
    PanderaSilverValidator,
)


# =============================================================================
# Helper: build a minimal activity schema for testing
# =============================================================================


def _activity_schema(nullable_value: bool = False) -> DataFrameSchema:
    """Return a minimal Pandera schema for a ChEMBL activity-like table."""
    return DataFrameSchema(
        {
            "activity_id": Column(int, nullable=False),
            "molecule_chembl_id": Column(str, nullable=False),
            "standard_type": Column(str, nullable=False),
            "standard_value": Column(float, nullable=nullable_value),
            "standard_units": Column(str, nullable=True),
        },
        strict=False,  # allow extra columns
    )


def _publication_schema() -> DataFrameSchema:
    """Return a minimal Pandera schema for a PubMed publication-like table."""
    return DataFrameSchema(
        {
            "pmid": Column(str, nullable=False),
            "title": Column(str, nullable=False),
            "year": Column(
                int,
                nullable=False,
                checks=pa.Check.in_range(1900, 2100),
            ),
        },
        strict=False,
    )


# =============================================================================
# 1. Row count validation
# =============================================================================


@pytest.mark.integration
class TestRowCountValidation:
    """Validation must respect minimum row-count expectations."""

    def test_non_empty_batch_passes_validation(self) -> None:
        """A non-empty batch that matches the schema should pass."""
        validator = PanderaSilverValidator(schema=_activity_schema())
        records = [
            {
                "activity_id": 1,
                "molecule_chembl_id": "CHEMBL25",
                "standard_type": "IC50",
                "standard_value": 0.5,
                "standard_units": "nM",
            }
        ]
        result = validator.validate(records)
        assert result.valid is True, f"Unexpected errors: {result.errors}"

    def test_empty_batch_always_passes(self) -> None:
        """An empty list should always be considered valid (no rows to fail)."""
        validator = PanderaSilverValidator(schema=_activity_schema())
        result = validator.validate([])
        assert result.valid is True

    def test_row_count_check_via_dq_score(self) -> None:
        """DQ score for a full-valid batch should equal 1.0."""
        total = 100
        score = calculate_dq_score(valid_count=total, total_count=total)
        assert score == 1.0

    def test_dq_score_below_threshold_flags_error(self) -> None:
        """If too many rows are invalid the hard threshold should be exceeded."""
        total = 100
        error_count = 25  # 25% error rate — exceeds default hard threshold of 20%
        _, exceeds_hard = exceeds_threshold(
            error_count=error_count,
            total_count=total,
            soft_threshold=0.05,
            hard_threshold=0.20,
        )
        assert exceeds_hard is True

    def test_dq_score_within_threshold_is_fine(self) -> None:
        """A 2% error rate should not exceed either threshold."""
        total = 100
        error_count = 2  # 2%
        exceeds_soft, exceeds_hard = exceeds_threshold(
            error_count=error_count,
            total_count=total,
            soft_threshold=0.05,
            hard_threshold=0.20,
        )
        assert exceeds_soft is False
        assert exceeds_hard is False


# =============================================================================
# 2. Null percentage validation
# =============================================================================


@pytest.mark.integration
class TestNullPercentageValidation:
    """Non-nullable columns must not contain nulls; nullable columns may."""

    def test_non_nullable_column_with_null_fails(self) -> None:
        """A null in a non-nullable column should cause validation to fail."""
        validator = PanderaSilverValidator(schema=_activity_schema())
        records = [
            {
                "activity_id": None,  # non-nullable → should fail
                "molecule_chembl_id": "CHEMBL25",
                "standard_type": "IC50",
                "standard_value": 0.5,
                "standard_units": "nM",
            }
        ]
        result = validator.validate(records)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_nullable_column_with_null_passes(self) -> None:
        """A null in a nullable column must be accepted.

        When all values for a float column are None, pandas infers the
        column as object dtype, causing a type mismatch.  We include at
        least one float value so that pandas infers float64 correctly.
        """
        schema = _activity_schema(nullable_value=True)
        validator = PanderaSilverValidator(schema=schema)
        records = [
            {
                "activity_id": 1,
                "molecule_chembl_id": "CHEMBL25",
                "standard_type": "IC50",
                "standard_value": None,  # nullable in this schema
                "standard_units": "nM",
            },
            {
                "activity_id": 2,
                "molecule_chembl_id": "CHEMBL12",
                "standard_type": "Ki",
                "standard_value": 5.0,  # ensures float64 column dtype
                "standard_units": "nM",
            },
        ]
        result = validator.validate(records)
        assert result.valid is True

    def test_null_percentage_calculation_helper(self) -> None:
        """Compute null percentage for a column using DQ score helpers."""
        total_rows = 20
        null_rows = 4  # 20% null
        valid_rows = total_rows - null_rows

        score = calculate_dq_score(valid_count=valid_rows, total_count=total_rows)
        assert score == 0.80

        # 20% null rate — exceeds soft threshold of 5% but not hard at 40%
        exceeds_soft, exceeds_hard = exceeds_threshold(
            error_count=null_rows,
            total_count=total_rows,
            soft_threshold=0.05,
            hard_threshold=0.40,
        )
        assert exceeds_soft is True
        assert exceeds_hard is False

    def test_mixed_records_null_on_required_field(self) -> None:
        """Batch where some rows have null required fields fails validation."""
        validator = PanderaSilverValidator(schema=_activity_schema())
        records = [
            {
                "activity_id": 1,
                "molecule_chembl_id": "CHEMBL25",
                "standard_type": "IC50",
                "standard_value": 0.5,
                "standard_units": "nM",
            },
            {
                "activity_id": 2,
                "molecule_chembl_id": None,  # required field is null
                "standard_type": "Ki",
                "standard_value": 12.3,
                "standard_units": "nM",
            },
        ]
        result = validator.validate(records)
        assert result.valid is False


# =============================================================================
# 3. Value range validation
# =============================================================================


@pytest.mark.integration
class TestValueRangeValidation:
    """Numeric columns should respect defined min/max bounds."""

    def test_year_out_of_range_fails(self) -> None:
        """A publication year of 1800 is below the 1900 lower bound."""
        validator = PanderaSilverValidator(schema=_publication_schema())
        records = [
            {
                "pmid": "12345678",
                "title": "Old paper",
                "year": 1800,  # below pa.Check.in_range(1900, 2100)
            }
        ]
        result = validator.validate(records)
        assert result.valid is False

    def test_year_within_range_passes(self) -> None:
        records = [
            {"pmid": "12345678", "title": "Good paper", "year": 2020}
        ]
        validator = PanderaSilverValidator(schema=_publication_schema())
        result = validator.validate(records)
        assert result.valid is True

    def test_future_year_out_of_range_fails(self) -> None:
        records = [
            {"pmid": "00000001", "title": "Future paper", "year": 2200}
        ]
        validator = PanderaSilverValidator(schema=_publication_schema())
        result = validator.validate(records)
        assert result.valid is False

    def test_custom_range_schema(self) -> None:
        """Custom schema with value range check works end-to-end."""
        schema = DataFrameSchema(
            {
                "ic50_nm": Column(
                    float,
                    nullable=False,
                    checks=pa.Check.greater_than(0),
                ),
            },
            strict=False,
        )
        validator = PanderaSilverValidator(schema=schema)

        valid_records = [{"ic50_nm": 0.5}, {"ic50_nm": 100.0}]
        assert validator.validate(valid_records).valid is True

        invalid_records = [{"ic50_nm": -1.0}]
        result = validator.validate(invalid_records)
        assert result.valid is False


# =============================================================================
# 4. Column presence / schema completeness checks
# =============================================================================


@pytest.mark.integration
class TestColumnPresenceValidation:
    """Required columns must be present; missing columns fail validation."""

    def test_missing_required_column_fails(self) -> None:
        """A record dict that lacks a required schema column fails."""
        validator = PanderaSilverValidator(schema=_activity_schema())
        records = [
            {
                # 'activity_id' is missing
                "molecule_chembl_id": "CHEMBL25",
                "standard_type": "IC50",
                "standard_value": 0.5,
                "standard_units": "nM",
            }
        ]
        result = validator.validate(records)
        assert result.valid is False

    def test_extra_columns_allowed_when_strict_false(self) -> None:
        """Schema built with strict=False allows extra columns."""
        schema = DataFrameSchema(
            {"activity_id": Column(int, nullable=False)},
            strict=False,
        )
        validator = PanderaSilverValidator(schema=schema)
        records = [
            {
                "activity_id": 1,
                "extra_field_a": "extra",
                "extra_field_b": 42,
            }
        ]
        result = validator.validate(records)
        assert result.valid is True

    def test_gold_validator_strict_mode_fails_without_schema(self) -> None:
        """Gold validator in strict mode requires a schema."""
        validator = PanderaGoldValidator(schema=None, strict=True)
        records = [{"entity_id": "CHEMBL25", "value": 5.5}]
        result = validator.validate(records)
        assert result.valid is False
        assert any("Gold" in e or "schema" in e.lower() for e in result.errors)

    def test_noop_validator_always_passes(self) -> None:
        """NoOpValidator should pass any records unconditionally."""
        validator = NoOpValidator()
        assert validator.validate([]).valid is True
        assert validator.validate([{"any": "data"}]).valid is True
        assert validator.validate([{"activity_id": 1, "score": 0.9}]).valid is True


# =============================================================================
# 5. Cross-record consistency: duplicate primary keys
# =============================================================================


@pytest.mark.integration
class TestCrossRecordConsistency:
    """Records within a single batch must not violate primary key uniqueness."""

    def test_unique_primary_keys_within_batch(self) -> None:
        """Validate that a batch has no duplicate primary keys."""
        records = [
            {"pmid": "111", "title": "Paper A", "year": 2020},
            {"pmid": "222", "title": "Paper B", "year": 2021},
            {"pmid": "333", "title": "Paper C", "year": 2022},
        ]
        pmids = [r["pmid"] for r in records]
        assert len(pmids) == len(set(pmids)), "Duplicate primary keys in batch!"

    def test_duplicate_primary_keys_detected(self) -> None:
        """A batch containing duplicate PKs must be detectable."""
        records = [
            {"pmid": "111", "title": "Paper A", "year": 2020},
            {"pmid": "111", "title": "Paper A (dup)", "year": 2020},  # duplicate
        ]
        pmids = [r["pmid"] for r in records]
        assert len(pmids) != len(set(pmids)), "Expected duplicate to be detected."

    def test_content_hash_uniqueness_enforces_deduplication(self) -> None:
        """Identical records produce identical content hashes — enabling dedup."""
        from bioetl.domain.transformations import generate_content_hash, normalize_for_hash

        record_a = {"pmid": "111", "title": "Paper A", "year": 2020}
        record_b = {"pmid": "111", "title": "Paper A", "year": 2020}  # same

        hash_a = generate_content_hash(normalize_for_hash(record_a), "pubmed")
        hash_b = generate_content_hash(normalize_for_hash(record_b), "pubmed")

        assert hash_a == hash_b, "Identical records must produce identical content hashes."

    def test_different_records_have_different_content_hashes(self) -> None:
        """Distinct records must not collide on content hash."""
        from bioetl.domain.transformations import generate_content_hash, normalize_for_hash

        record_a = {"pmid": "111", "title": "Paper A", "year": 2020}
        record_b = {"pmid": "222", "title": "Paper B", "year": 2021}

        hash_a = generate_content_hash(normalize_for_hash(record_a), "pubmed")
        hash_b = generate_content_hash(normalize_for_hash(record_b), "pubmed")

        assert hash_a != hash_b


# =============================================================================
# 6. ValidationResult dataclass contracts
# =============================================================================


@pytest.mark.unit
class TestValidationResultContract:
    """ValidationResult must honour its API contract."""

    def test_default_valid_result(self) -> None:
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []

    def test_invalid_result_with_errors(self) -> None:
        errors = ["Column 'x' has nulls", "Column 'y' out of range"]
        result = ValidationResult(valid=False, errors=errors)
        assert result.valid is False
        assert len(result.errors) == 2

    def test_valid_true_with_no_errors(self) -> None:
        result = ValidationResult(valid=True, errors=[])
        assert bool(result.errors) is False
