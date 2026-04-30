"""Merged metadata explainer for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.models.metadata import CompositeOutputExt
from bioetl.domain.types import JsonDict


@dataclass(frozen=True)
class MergedFieldExplanation:
    """Explanation for a single merged field."""

    field_name: str
    source_providers: list[str]
    merge_strategy: str
    priority_order: list[str] | None = None
    final_value_source: str | None = None
    conflict_resolution: str | None = None
    enrichment_applied: list[str] | None = None


@dataclass(frozen=True)
class MergedRecordExplanation:
    """Explanation for a complete merged record."""

    record_id: str
    composite_run_id: str
    source_providers: list[str]
    field_explanations: list[MergedFieldExplanation]
    merge_strategy: str
    conflict_count: int = 0
    enrichment_count: int = 0


class MergedMetadataExplainer:
    """Explainer for merged-record provenance and merge decisions."""

    def generate_field_explanation(
        self,
        field_name: str,
        _record_data: JsonDict,
        composite_metadata: CompositeOutputExt,
        field_priorities: dict[str, JsonDict] | None = None,
    ) -> MergedFieldExplanation:
        """Describe how one merged field was selected and enriched."""
        source_providers = list(composite_metadata.source_providers or [])
        priority_order = _resolve_priority_order(field_name, field_priorities)
        return MergedFieldExplanation(
            field_name=field_name,
            source_providers=source_providers,
            merge_strategy="prioritize",
            priority_order=priority_order,
            final_value_source=next(iter(source_providers), None),
            conflict_resolution="priority_based" if priority_order else None,
            enrichment_applied=_extract_applied_enrichments(composite_metadata),
        )

    def generate_record_explanation(
        self,
        record_id: str,
        record_data: JsonDict,
        composite_metadata: CompositeOutputExt,
        field_priorities: dict[str, JsonDict] | None = None,
        merge_strategy: str = "prioritize",
    ) -> MergedRecordExplanation:
        """Build explainability details for one merged output record."""
        field_explanations = [
            self.generate_field_explanation(
                field_name,
                record_data,
                composite_metadata,
                field_priorities,
            )
            for field_name in _public_field_names(record_data)
        ]
        conflict_count, enrichment_count = _count_conflicts_and_enrichments(
            field_explanations
        )
        return MergedRecordExplanation(
            record_id=record_id,
            composite_run_id=composite_metadata.composite_run_id or "unknown",
            source_providers=list(composite_metadata.source_providers or []),
            field_explanations=field_explanations,
            merge_strategy=merge_strategy,
            conflict_count=conflict_count,
            enrichment_count=enrichment_count,
        )

    def generate_explainability_metadata(
        self,
        records: list[JsonDict],
        composite_metadata: CompositeOutputExt,
        field_priorities: dict[str, JsonDict] | None = None,
        merge_strategy: str = "prioritize",
    ) -> list[MergedRecordExplanation]:
        """Generate record-level explainability objects for a merged batch."""
        return [
            self.generate_record_explanation(
                _resolve_record_id(record),
                record,
                composite_metadata,
                field_priorities,
                merge_strategy,
            )
            for record in records
        ]

    def generate_explainability_summary(
        self,
        explanations: list[MergedRecordExplanation],
    ) -> JsonDict:
        """Summarize explainability coverage, conflicts, and enrichments."""
        if not explanations:
            return _empty_explainability_summary()
        return _build_explainability_summary(explanations)

    def generate_field_priority_explanation(
        self,
        field_priorities: dict[str, JsonDict],
    ) -> list[JsonDict]:
        """Expose field-priority policy in a report-friendly structure."""
        return [
            {
                "field_name": field_name,
                "priority_order": priority_config.get("priority", []),
                "source": priority_config.get("source"),
                "fallback_strategy": priority_config.get("fallback", "keep_first"),
                "conflict_resolution": priority_config.get(
                    "conflict_resolution",
                    "priority_based",
                ),
            }
            for field_name, priority_config in field_priorities.items()
        ]


def _resolve_priority_order(
    field_name: str,
    field_priorities: dict[str, JsonDict] | None,
) -> list[str] | None:
    if not field_priorities or field_name not in field_priorities:
        return None
    priority = field_priorities[field_name].get("priority")
    if not isinstance(priority, list):
        return []
    return [str(item) for item in priority]


def _extract_applied_enrichments(
    composite_metadata: CompositeOutputExt,
) -> list[str] | None:
    if not composite_metadata.enrichment_status:
        return None
    applied = [
        enricher
        for enricher, status in composite_metadata.enrichment_status.items()
        if status == "applied"
    ]
    return applied or None


def _public_field_names(record_data: JsonDict) -> list[str]:
    return [name for name in record_data if not name.startswith("_")]


def _count_conflicts_and_enrichments(
    field_explanations: list[MergedFieldExplanation],
) -> tuple[int, int]:
    conflict_count = sum(1 for exp in field_explanations if exp.conflict_resolution)
    enrichment_count = sum(
        len(exp.enrichment_applied) if exp.enrichment_applied else 0
        for exp in field_explanations
    )
    return conflict_count, enrichment_count


def _resolve_record_id(record: JsonDict) -> str:
    candidate = (
        record.get("_record_id")
        or record.get("id")
        or record.get("molecule_id")
        or str(hash(str(record)))
    )
    return str(candidate)


def _empty_explainability_summary() -> JsonDict:
    return {
        "record_count": 0,
        "source_provider_distribution": {},
        "merge_strategy_distribution": {},
        "conflict_summary": {"total_conflicts": 0, "conflict_rate": 0.0},
        "enrichment_summary": {"total_enrichments": 0, "enrichment_rate": 0.0},
    }


def _build_distributions(
    explanations: list[MergedRecordExplanation],
) -> tuple[JsonDict, JsonDict]:
    source_distribution: dict[str, int] = {}
    strategy_distribution: dict[str, int] = {}
    for explanation in explanations:
        for provider in explanation.source_providers:
            source_distribution[provider] = source_distribution.get(provider, 0) + 1
        strategy = explanation.merge_strategy
        strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1
    return source_distribution, strategy_distribution


def _build_explainability_summary(
    explanations: list[MergedRecordExplanation],
) -> JsonDict:
    totals = _summary_totals(explanations)
    source_distribution, strategy_distribution = _build_distributions(explanations)
    return {
        "record_count": totals["total_records"],
        "field_count": totals["total_fields"],
        "avg_fields_per_record": _safe_ratio(
            totals["total_fields"],
            totals["total_records"],
        ),
        "source_provider_distribution": source_distribution,
        "merge_strategy_distribution": strategy_distribution,
        "conflict_summary": _conflict_summary(explanations, totals),
        "enrichment_summary": _enrichment_summary(explanations, totals),
    }


def _summary_totals(explanations: list[MergedRecordExplanation]) -> dict[str, int]:
    return {
        "total_records": len(explanations),
        "total_fields": sum(len(exp.field_explanations) for exp in explanations),
        "total_conflicts": sum(exp.conflict_count for exp in explanations),
        "total_enrichments": sum(exp.enrichment_count for exp in explanations),
    }


def _conflict_summary(
    explanations: list[MergedRecordExplanation],
    totals: dict[str, int],
) -> JsonDict:
    return {
        "total_conflicts": totals["total_conflicts"],
        "conflict_rate": _safe_ratio(totals["total_conflicts"], totals["total_fields"]),
        "records_with_conflicts": sum(
            1 for exp in explanations if exp.conflict_count > 0
        ),
    }


def _enrichment_summary(
    explanations: list[MergedRecordExplanation],
    totals: dict[str, int],
) -> JsonDict:
    return {
        "total_enrichments": totals["total_enrichments"],
        "enrichment_rate": _safe_ratio(
            totals["total_enrichments"],
            totals["total_fields"],
        ),
        "records_with_enrichments": sum(
            1 for exp in explanations if exp.enrichment_count > 0
        ),
    }


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator > 0 else 0.0


# Deprecated compatibility alias retained during ADR-041 migration.
MergedMetadataExplainabilityService = MergedMetadataExplainer


def create_merged_metadata_explainability_service() -> MergedMetadataExplainer:
    """Factory function for the canonical merged metadata explainer."""
    return MergedMetadataExplainer()
