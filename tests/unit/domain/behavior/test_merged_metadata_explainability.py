"""Unit tests for merged metadata explainability behavior."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedMetadataExplainer,
    _safe_ratio,
    create_merged_metadata_explainability_service,
)
from bioetl.domain.models.metadata import CompositeOutputExt

pytestmark = pytest.mark.unit


def _metadata() -> CompositeOutputExt:
    return CompositeOutputExt(
        composite_run_id="run-1",
        source_providers=["chembl", "pubmed"],
        enrichment_status={"mesh": "applied", "openalex": "skipped"},
    )


def test_field_explanation_uses_priority_and_applied_enrichments() -> None:
    explainer = create_merged_metadata_explainability_service()

    explanation = explainer.generate_field_explanation(
        "title",
        {"title": "Aspirin"},
        _metadata(),
        {"title": {"priority": ["pubmed", "chembl"]}},
    )

    assert explanation.field_name == "title"
    assert explanation.source_providers == ["chembl", "pubmed"]
    assert explanation.priority_order == ["pubmed", "chembl"]
    assert explanation.final_value_source == "chembl"
    assert explanation.conflict_resolution == "priority_based"
    assert explanation.enrichment_applied == ["mesh"]


def test_field_explanation_handles_missing_priority_and_enrichment() -> None:
    explanation = MergedMetadataExplainer().generate_field_explanation(
        "title",
        {"title": "Aspirin"},
        CompositeOutputExt(source_providers=[]),
        {"title": {"priority": "pubmed"}},
    )

    assert explanation.priority_order == []
    assert explanation.final_value_source is None
    assert explanation.conflict_resolution is None
    assert explanation.enrichment_applied is None


def test_record_explanation_ignores_private_fields_and_counts_conflicts() -> None:
    explanation = MergedMetadataExplainer().generate_record_explanation(
        "record-1",
        {"title": "Aspirin", "_internal": "hidden"},
        _metadata(),
        {"title": {"priority": ["chembl"]}},
        merge_strategy="custom",
    )

    assert explanation.record_id == "record-1"
    assert explanation.composite_run_id == "run-1"
    assert [field.field_name for field in explanation.field_explanations] == ["title"]
    assert explanation.conflict_count == 1
    assert explanation.enrichment_count == 1
    assert explanation.merge_strategy == "custom"


def test_generate_explainability_metadata_resolves_record_ids() -> None:
    explanations = MergedMetadataExplainer().generate_explainability_metadata(
        [
            {"_record_id": "explicit", "title": "A"},
            {"id": "id-field", "title": "B"},
            {"molecule_id": "CHEMBL25", "title": "C"},
            {"title": "D"},
        ],
        _metadata(),
    )

    assert [item.record_id for item in explanations[:3]] == [
        "explicit",
        "id-field",
        "CHEMBL25",
    ]
    assert explanations[3].record_id


def test_summary_reports_empty_and_non_empty_distributions() -> None:
    explainer = MergedMetadataExplainer()

    assert explainer.generate_explainability_summary([]) == {
        "record_count": 0,
        "source_provider_distribution": {},
        "merge_strategy_distribution": {},
        "conflict_summary": {"total_conflicts": 0, "conflict_rate": 0.0},
        "enrichment_summary": {"total_enrichments": 0, "enrichment_rate": 0.0},
    }

    explanations = explainer.generate_explainability_metadata(
        [{"title": "A"}, {"title": "B"}],
        _metadata(),
        {"title": {"priority": ["chembl"]}},
    )
    summary = explainer.generate_explainability_summary(explanations)

    assert summary["record_count"] == 2
    assert summary["field_count"] == 2
    assert summary["avg_fields_per_record"] == 1.0
    assert summary["source_provider_distribution"] == {"chembl": 2, "pubmed": 2}
    assert summary["merge_strategy_distribution"] == {"prioritize": 2}
    assert summary["conflict_summary"]["records_with_conflicts"] == 2
    assert summary["enrichment_summary"]["records_with_enrichments"] == 2


def test_field_priority_explanation_defaults_are_stable() -> None:
    explanation = MergedMetadataExplainer().generate_field_priority_explanation(
        {"title": {"priority": ["pubmed"], "source": "config"}}
    )

    assert explanation == [
        {
            "field_name": "title",
            "priority_order": ["pubmed"],
            "source": "config",
            "fallback_strategy": "keep_first",
            "conflict_resolution": "priority_based",
        }
    ]
    assert _safe_ratio(1, 0) == 0.0
