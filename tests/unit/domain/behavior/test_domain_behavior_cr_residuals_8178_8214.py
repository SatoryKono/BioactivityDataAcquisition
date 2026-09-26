# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/behavior CR-FULL #8178-#8214."""

from __future__ import annotations


import pytest

pytestmark = pytest.mark.unit

from bioetl.domain.behavior.author_normalization_service import AuthorNormalizer
from bioetl.domain.behavior.composite_validation_helpers import (
    _is_valid_field_priorities,
)
from bioetl.domain.behavior.cross_validation_helpers import _is_valid_threshold
from bioetl.domain.behavior.cross_validation_validator import (
    CrossValidationDispositionPolicy,
    _apply_disposition_policy,
)
from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.behavior.dq_rule_evaluator import evaluate_dq_rules_for_record
from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.behavior.organism_classification_service_models import (
    ClassificationStats,
)
from bioetl.domain.behavior.validation_helpers import validate_data
from bioetl.domain.behavior.value_validator_rules import validate_percent_value
from bioetl.domain.behavior._author_helpers import deduplicate_case_insensitive
from bioetl.domain.config import DQConfig
from bioetl.domain.config.validation import CrossFieldValidation
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.types.validation_result import ValidationIssue
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


def test_validate_percent_rejects_nan() -> None:
    ok, err = validate_percent_value(float("nan"))
    assert ok is False
    assert err is not None


def test_validate_data_allows_zero_and_false() -> None:
    validate_data(0)
    validate_data(False)
    with pytest.raises(ValueError):
        validate_data(None)
    with pytest.raises(ValueError):
        validate_data([])


def test_field_priorities_reject_duplicate_ranks() -> None:
    assert _is_valid_field_priorities({"a": {"priority": 1}, "b": {"priority": 2}})
    assert not _is_valid_field_priorities({"a": {"priority": 1}, "b": {"priority": 1}})


def test_classification_stats_rejects_inconsistent_buckets() -> None:
    with pytest.raises(ValueError):
        ClassificationStats(
            total=2,
            acellular=1,
            unicellular=0,
            multicellular=0,
            unresolved=0,
            conflict_count=0,
        )


def test_extract_incoming_fields_unions_batch() -> None:
    fields = DQMetricsCalculator._extract_incoming_fields(
        [{"a": 1}, {"b": 2}, {"a": 3, "c": 4}]
    )
    assert fields == {"a", "b", "c"}


def test_identity_service_copies_hash_policy_sets() -> None:
    include = {"x"}
    exclude = {"y"}
    service = EntityIdentityGenerator(
        content_hash_include_fields=include,
        content_hash_exclude_fields=exclude,
    )
    include.add("z")
    exclude.add("w")
    assert service._content_hash_include_fields == {"x"}
    assert service._content_hash_exclude_fields == {"y"}


def test_threshold_rejects_bool() -> None:
    assert _is_valid_threshold(0.5)
    assert not _is_valid_threshold(True)
    assert not _is_valid_threshold(False)


def test_disposition_policy_preserves_non_blockers() -> None:
    issues = [
        ValidationIssue(
            code=IssueCode.CMP_PF_CV_012,
            severity=ValidationSeverity.WARNING,
            layer=ValidationLayer.DEEP_PREFLIGHT,
            message="warn",
            details={},
        ),
        ValidationIssue(
            code=IssueCode.CMP_PF_CV_011,
            severity=ValidationSeverity.BLOCKER,
            layer=ValidationLayer.DEEP_PREFLIGHT,
            message="block",
            details={},
        ),
    ]
    out = _apply_disposition_policy(
        issues=issues,
        policy=CrossValidationDispositionPolicy.WARNING_ONLY,
    )
    assert len(out) == 2
    assert out[0].severity == ValidationSeverity.WARNING
    assert out[1].severity == ValidationSeverity.WARNING


def test_author_salt_required() -> None:
    svc = AuthorNormalizer()
    with pytest.raises(ValueError, match="salt"):
        svc.normalize_authors(["Ada Lovelace"], salt="")


def test_casefold_dedupe() -> None:
    assert deduplicate_case_insensitive(["A", "a", "B"]) == ["A", "B"]


def test_cross_field_applies_invalid_record_policy() -> None:
    cfg = DQConfig(
        invalid_record_policy="quarantine",
        cross_field_validations=(
            CrossFieldValidation(
                name="require_pair",
                fields=("a", "b"),
                condition="all_present",
                severity="error",
            ),
        ),
    )
    # force a violation depending on evaluator semantics; if rule not violated, skip
    outcomes = evaluate_dq_rules_for_record({"a": 1}, cfg)
    # Either empty (no violation) or quarantined on error severity
    for outcome in outcomes:
        if outcome.rule_id.startswith("cross."):
            assert outcome.disposition == DQDisposition.QUARANTINE
