"""Unit tests for cross-validation helper functions."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.cross_validation_helpers import (
    _collect_covered_sources,
    _comparison_source_list,
    _is_valid_threshold,
    _validate_coverage,
    _validate_pairs,
    _validate_rules,
)
from bioetl.domain.types.validation_severity import IssueCode

pytestmark = pytest.mark.unit


def test_validate_pairs_reports_empty_shape_type_and_source_errors() -> None:
    assert _validate_pairs([], ["chembl"])[0].code == IssueCode.CMP_PF_CV_002
    assert _validate_pairs(["bad"], ["chembl"])[0].code == IssueCode.CMP_PF_CV_003
    assert _validate_pairs([{"a": ["b"], "c": ["d"]}], ["a"])[0].code == (
        IssueCode.CMP_PF_CV_004
    )
    assert _validate_pairs([{1: ["chembl"]}], ["chembl"])[0].code == (
        IssueCode.CMP_PF_CV_005
    )


def test_validate_pairs_reports_invalid_comparison_sources() -> None:
    issues = _validate_pairs(
        [
            {"chembl": []},
            {"pubmed": ["chembl", 1]},
            {"openalex": {"bad": "shape"}},
            {"crossref": ["missing"]},
        ],
        ["chembl", "pubmed", "openalex", "crossref"],
    )

    assert [issue.code for issue in issues] == [
        IssueCode.CMP_PF_CV_006,
        IssueCode.CMP_PF_CV_006,
        IssueCode.CMP_PF_CV_006,
        IssueCode.CMP_PF_CV_007,
    ]


def test_validate_pairs_accepts_self_and_known_comparison_sources() -> None:
    assert _validate_pairs([{"chembl": ["chembl", "pubmed"]}], ["chembl", "pubmed"]) == []


def test_validate_rules_reports_empty_non_string_and_unsupported_types() -> None:
    assert _validate_rules({})[0].code == IssueCode.CMP_PF_CV_008
    assert _validate_rules({"r1": 1})[0].code == IssueCode.CMP_PF_CV_009
    assert _validate_rules({"r1": "bad"})[0].code == IssueCode.CMP_PF_CV_010
    assert _validate_rules({"r1": "strict", "r2": "custom"}) == []


def test_threshold_and_coverage_helpers_report_uncovered_sources() -> None:
    assert _is_valid_threshold(None)
    assert _is_valid_threshold(0.0)
    assert _is_valid_threshold(1.0)
    assert not _is_valid_threshold(-0.1)
    assert not _is_valid_threshold(1.1)
    assert not _is_valid_threshold("0.5")

    issues = _validate_coverage([{"chembl": "pubmed"}], ["chembl", "pubmed", "openalex"])
    assert issues[0].code == IssueCode.CMP_PF_CV_013
    assert issues[0].details is not None
    assert issues[0].details["uncovered_sources"] == ["openalex"]
    assert _validate_coverage([], []) == []


def test_collect_covered_sources_and_comparison_source_list_ignore_invalid_shapes() -> None:
    assert _comparison_source_list("pubmed") == ["pubmed"]
    assert _comparison_source_list(["pubmed", 1, "openalex"]) == ["pubmed", "openalex"]
    assert _comparison_source_list({"bad": "shape"}) == []
    assert _collect_covered_sources(
        [{"chembl": ["pubmed", 1]}, {"openalex": "crossref"}, "bad"]
    ) == {"chembl", "pubmed", "openalex", "crossref"}
