"""Focused tests for composite runner stage payload helpers."""

from __future__ import annotations

import pytest

from bioetl.application.composite.runtime_models import CompositeExecutionContext
from bioetl.application.composite.runner_pkg.runner_stage_payloads import (
    build_composite_run_completion_metrics,
    build_dependency_stage_details,
    build_dependency_stage_metrics,
    build_enrichment_stage_details,
    build_enrichment_stage_metrics,
    build_merge_stage_metrics,
    build_seed_stage_metrics,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)


pytestmark = pytest.mark.unit

def test_build_dependency_stage_details_returns_stable_payload() -> None:
    details = build_dependency_stage_details(["dep_b", "dep_a"])

    assert details == {
        "dependencies": ["dep_b", "dep_a"],
        "count": 2,
    }


def test_build_enrichment_stage_details_returns_stable_payload() -> None:
    details = build_enrichment_stage_details(("xref", "pubmed"))

    assert details == {
        "enrichers": ["xref", "pubmed"],
        "count": 2,
    }


def test_build_stage_metrics_cover_all_terminal_counts() -> None:
    seed_result = SeedResult(
        pipeline_name="seed",
        records_extracted=10,
        records_silver=9,
        keys_generated=9,
    )
    dependency_results = {
        "dep_ok": DependencyResult(
            pipeline_name="dep_ok",
            status=DependencyStatus.SUCCESS,
        ),
        "dep_fail": DependencyResult(
            pipeline_name="dep_fail",
            status=DependencyStatus.FAILED,
        ),
    }
    enrichment_results = {
        "ok": EnrichmentResult(
            enricher_name="ok",
            status=EnrichmentStatus.SUCCESS,
        ),
        "fail": EnrichmentResult(
            enricher_name="fail",
            status=EnrichmentStatus.FAILED,
        ),
        "skip": EnrichmentResult(
            enricher_name="skip",
            status=EnrichmentStatus.SKIPPED,
        ),
    }
    merge_result = MergeResult(
        records_merged=9,
        records_from_seed=10,
        records_enriched=7,
        records_fully_enriched=6,
    )

    assert build_seed_stage_metrics(seed_result) == {
        "records_extracted": 10,
        "records_silver": 9,
        "keys_generated": 9,
    }
    assert build_dependency_stage_metrics(dependency_results) == {
        "dependencies_total": 2,
        "dependencies_succeeded": 1,
        "dependencies_failed": 1,
    }
    assert build_enrichment_stage_metrics(enrichment_results) == {
        "enrichers_total": 3,
        "enrichers_succeeded": 1,
        "enrichers_failed": 1,
        "enrichers_skipped": 1,
    }
    assert build_merge_stage_metrics(merge_result) == {
        "records_merged": 9,
        "records_from_seed": 10,
        "records_enriched": 7,
        "records_fully_enriched": 6,
    }


def test_build_composite_run_completion_metrics_omits_merge_when_absent() -> None:
    execution_context = CompositeExecutionContext(
        seed_result=SeedResult(
            pipeline_name="seed",
            records_extracted=3,
            records_silver=2,
            keys_generated=2,
        ),
        dependency_results={},
        enrichment_results={},
        merge_result=None,
    )

    assert build_composite_run_completion_metrics(execution_context) == {
        "records_extracted": 3,
        "records_silver": 2,
        "keys_generated": 2,
        "dependencies_total": 0,
        "dependencies_succeeded": 0,
        "dependencies_failed": 0,
        "enrichers_total": 0,
        "enrichers_succeeded": 0,
        "enrichers_failed": 0,
        "enrichers_skipped": 0,
    }
