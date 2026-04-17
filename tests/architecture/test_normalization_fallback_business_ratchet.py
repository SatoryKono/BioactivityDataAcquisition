"""Architecture ratchet for normalization fallback business debt."""

from __future__ import annotations

import pytest

from scripts.engineering.qa.report_normalization_fallback_inventory import (
    _build_payload,
)
from scripts.engineering.qa.report_normalization_fallback_inventory import (
    _fallback_rows,
)

FALLBACK_BUSINESS_FIELD_BUDGET = 0

# Derived from the reviewed post-#2789/#2791 baseline where explicit profile coverage
# reaches 100% and the fallback inventory is empty. Rebaseline intentionally if one of
# these families is allowed to re-introduce business fallback normalization.
REVIEWED_PIPELINE_FALLBACK_BUSINESS_BUDGETS: dict[str, int] = {
    "chembl_assay_parameters": 0,
    "chembl_target_component": 0,
    "chembl_protein_class": 0,
    "chembl_cell_line": 0,
    "chembl_publication_similarity": 0,
    "chembl_compound_record": 0,
    "chembl_tissue": 0,
    "chembl_publication_term": 0,
    "chembl_subcellular_fraction": 0,
}


def _fallback_business_counts_by_pipeline(
    payload: dict[str, object],
) -> dict[str, int]:
    counts_by_pipeline: dict[str, int] = {}
    for item in payload["pipelines"]:
        typed_item = dict(item)
        counts_by_pipeline[str(typed_item["pipeline_name"])] = int(
            typed_item.get("fallback_business_field_count", 0)
        )
    return counts_by_pipeline


def _assert_reviewed_pipeline_fallback_business_budgets(
    payload: dict[str, object],
) -> None:
    counts_by_pipeline = _fallback_business_counts_by_pipeline(payload)
    exceeded = [
        (
            pipeline_name,
            counts_by_pipeline.get(pipeline_name, 0),
            budget,
        )
        for pipeline_name, budget in REVIEWED_PIPELINE_FALLBACK_BUSINESS_BUDGETS.items()
        if counts_by_pipeline.get(pipeline_name, 0) > budget
    ]

    assert not exceeded, (
        "reviewed pipeline fallback_business budgets exceeded: "
        + "; ".join(
            f"{pipeline_name}={actual} exceeds budget {budget}"
            for pipeline_name, actual, budget in exceeded
        )
        + ". Reduce pipeline-specific fallback business debt or intentionally "
        "rebaseline the reviewed ratchet."
    )


def test_fallback_business_field_count_does_not_exceed_budget() -> None:
    """Business fallback normalization debt must not grow above the reviewed baseline."""
    payload = _build_payload(_fallback_rows())
    actual = int(payload["fallback_business_field_count"])

    assert actual <= FALLBACK_BUSINESS_FIELD_BUDGET, (
        "fallback_business_field_count="
        f"{actual} exceeds budget {FALLBACK_BUSINESS_FIELD_BUDGET}. "
        "Reduce fallback business debt or intentionally rebaseline the ratchet."
    )


def test_reviewed_pipeline_fallback_business_counts_do_not_exceed_budgets() -> None:
    """Reviewed high-debt families must not silently regain fallback business debt."""
    payload = _build_payload(_fallback_rows())

    _assert_reviewed_pipeline_fallback_business_budgets(payload)


def test_reviewed_pipeline_ratchet_reports_pipeline_specific_regression() -> None:
    """Synthetic regression should fail with a pipeline-specific ratchet message."""
    payload = _build_payload(
        [
            {
                "pipeline_name": "chembl_assay_parameters",
                "field_name": "comments",
                "normalizer": "normalize_profile_json_string",
                "normalization_source": "fallback_business",
            }
        ],
        coverage_kpi={
            "name": "explicit_profile_coverage_pct",
            "numerator": 999,
            "denominator": 1000,
            "value_pct": 99.9,
        },
    )

    with pytest.raises(
        AssertionError,
        match=(
            "reviewed pipeline fallback_business budgets exceeded: "
            "chembl_assay_parameters=1 exceeds budget 0"
        ),
    ):
        _assert_reviewed_pipeline_fallback_business_budgets(payload)
