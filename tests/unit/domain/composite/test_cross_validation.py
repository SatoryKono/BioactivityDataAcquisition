# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
"""Unit tests for cross-validation domain models.

Tests for ComparisonMethod, CrossValidationVerdict, FieldComparisonSpec,
EnricherFieldPairing, FieldMismatch, RecordCrossValidationResult,
EnricherCVStats, CrossValidationStats.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    CrossValidationStats,
    CrossValidationVerdict,
    EnricherCVStats,
    EnricherFieldPairing,
    FieldComparisonSpec,
    FieldMismatch,
    RecordCrossValidationResult,
)


pytestmark = pytest.mark.unit


class TestComparisonMethod:
    """Tests for ComparisonMethod enum."""

    def test_comparison_method__values__f25aeedf(self):
        assert ComparisonMethod.EXACT == "exact"
        assert ComparisonMethod.FUZZY == "fuzzy"
        assert ComparisonMethod.NUMERIC_TOLERANCE == "numeric_tolerance"
        assert ComparisonMethod.SKIP == "skip"

    def test_comparison_method__is_str_enum__ce3124f7(self):
        assert isinstance(ComparisonMethod.EXACT, str)


class TestCrossValidationVerdict:
    """Tests for CrossValidationVerdict enum."""

    def test_validation_verdict__values__00d56cec(self):
        assert CrossValidationVerdict.PASS == "pass"
        assert CrossValidationVerdict.WARNING == "warning"
        assert CrossValidationVerdict.ENRICHER_ERROR == "enricher_error"


class TestFieldComparisonSpec:
    """Tests for FieldComparisonSpec dataclass."""

    def test_exact_no_threshold(self):
        spec = FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT)
        assert spec.field_name == "doi"
        assert spec.method == ComparisonMethod.EXACT
        assert spec.threshold == pytest.approx(0.0)

    def test_fuzzy_with_threshold(self):
        spec = FieldComparisonSpec(
            field_name="title", method=ComparisonMethod.FUZZY, threshold=0.8
        )
        assert spec.threshold == pytest.approx(0.8)

    def test_numeric_tolerance_with_threshold(self):
        spec = FieldComparisonSpec(
            field_name="citations",
            method=ComparisonMethod.NUMERIC_TOLERANCE,
            threshold=0.1,
        )
        assert spec.threshold == pytest.approx(0.1)

    def test_skip_no_threshold(self):
        spec = FieldComparisonSpec(field_name="abstract", method=ComparisonMethod.SKIP)
        assert spec.method == ComparisonMethod.SKIP

    def test_empty_field_name_raises(self):
        with pytest.raises(ValueError, match="field_name cannot be empty"):
            FieldComparisonSpec(field_name="", method=ComparisonMethod.EXACT)

    def test_fuzzy_zero_threshold_defaults_to_0_8(self):
        # Zero is treated as "unset" and becomes the documented FUZZY default.
        spec = FieldComparisonSpec(
            field_name="title", method=ComparisonMethod.FUZZY, threshold=0.0
        )
        assert spec.threshold == 0.8

    def test_numeric_negative_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold must be in"):
            FieldComparisonSpec(
                field_name="year",
                method=ComparisonMethod.NUMERIC_TOLERANCE,
                threshold=-0.1,
            )

    def test_field_comparison_spec__frozen__599e03ff(self):
        spec = FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT)
        with pytest.raises(AttributeError):
            spec.field_name = "pmid"  # type: ignore[misc]


class TestEnricherFieldPairing:
    """Tests for EnricherFieldPairing dataclass."""

    def test_valid_pairing(self):
        fields = (
            FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
            FieldComparisonSpec(
                field_name="title", method=ComparisonMethod.FUZZY, threshold=0.8
            ),
        )
        pairing = EnricherFieldPairing(
            enricher_pipeline="crossref_publication", fields=fields
        )
        assert pairing.enricher_pipeline == "crossref_publication"
        assert len(pairing.fields) == 2

    def test_list_converted_to_tuple(self):
        fields = [
            FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
        ]
        pairing = EnricherFieldPairing(
            enricher_pipeline="crossref_publication",
            fields=fields,  # type: ignore[arg-type]
        )
        assert isinstance(pairing.fields, tuple)

    def test_empty_pipeline_raises(self):
        fields = (FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),)
        with pytest.raises(ValueError, match="enricher_pipeline cannot be empty"):
            EnricherFieldPairing(enricher_pipeline="", fields=fields)

    def test_enricher_field_pairing__empty_fields_raises__4c25b247(self):
        with pytest.raises(ValueError, match="must have at least one field"):
            EnricherFieldPairing(enricher_pipeline="crossref_publication", fields=())


class TestFieldMismatch:
    """Tests for FieldMismatch dataclass."""

    def test_creation(self):
        mismatch = FieldMismatch(
            field_name="title",
            seed_value="Foo Bar",
            enricher_value="Baz Qux",
            method=ComparisonMethod.FUZZY,
        )
        assert mismatch.field_name == "title"
        assert mismatch.seed_value == "Foo Bar"
        assert mismatch.enricher_value == "Baz Qux"
        assert mismatch.method == ComparisonMethod.FUZZY


class TestRecordCrossValidationResult:
    """Tests for RecordCrossValidationResult dataclass."""

    def test_pass_verdict(self):
        result = RecordCrossValidationResult(
            enricher="crossref_publication",
            verdict=CrossValidationVerdict.PASS,
            fields_compared=5,
            fields_skipped=2,
        )
        assert result.verdict == CrossValidationVerdict.PASS
        assert result.mismatches == ()

    def test_warning_with_mismatch(self):
        mismatch = FieldMismatch(
            field_name="title",
            seed_value="A",
            enricher_value="B",
            method=ComparisonMethod.EXACT,
        )
        result = RecordCrossValidationResult(
            enricher="crossref_publication",
            verdict=CrossValidationVerdict.WARNING,
            mismatches=(mismatch,),
            fields_compared=5,
        )
        assert len(result.mismatches) == 1

    def test_list_mismatches_converted_to_tuple(self):
        result = RecordCrossValidationResult(
            enricher="crossref_publication",
            verdict=CrossValidationVerdict.PASS,
            mismatches=[],  # type: ignore[arg-type]
        )
        assert isinstance(result.mismatches, tuple)


class TestEnricherCVStats:
    """Tests for EnricherCVStats dataclass."""

    def test_enricher_c_v_stats__defaults__5741e501(self):
        stats = EnricherCVStats(enricher="crossref_publication")
        assert stats.total_records == 0
        assert stats.passed == 0
        assert stats.warned == 0
        assert stats.errored == 0

    def test_with_values(self):
        stats = EnricherCVStats(
            enricher="crossref_publication",
            total_records=100,
            passed=90,
            warned=5,
            errored=5,
        )
        assert stats.total_records == 100


class TestCrossValidationStats:
    """Tests for CrossValidationStats dataclass."""

    def test_cross_validation_stats__defaults__d00309c8(self):
        stats = CrossValidationStats()
        assert stats.total_records == 0
        assert stats.passed == 0
        assert stats.warned == 0
        assert stats.errored == 0
        assert stats.quarantined == 0
        assert stats.enricher_stats == ()

    def test_with_enricher_stats(self):
        enricher_stats = (
            EnricherCVStats(enricher="crossref_publication", total_records=100),
            EnricherCVStats(enricher="openalex_publication", total_records=100),
        )
        stats = CrossValidationStats(
            total_records=100,
            passed=80,
            warned=10,
            errored=10,
            quarantined=2,
            enricher_stats=enricher_stats,
        )
        assert len(stats.enricher_stats) == 2

    def test_list_enricher_stats_converted_to_tuple(self):
        stats = CrossValidationStats(
            enricher_stats=[]  # type: ignore[arg-type]
        )
        assert isinstance(stats.enricher_stats, tuple)
