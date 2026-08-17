"""Merged metadata explainer for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.behavior.merged_metadata_helpers import (
    deterministic_record_id as _deterministic_record_id,
)
from bioetl.domain.behavior.merged_metadata_helpers import (
    extract_applied_enrichments as _extract_applied_enrichments,
)
from bioetl.domain.behavior.merged_metadata_helpers import (
    json_fallback as _json_fallback,
)
from bioetl.domain.behavior.merged_metadata_helpers import (
    public_field_names as _public_field_names,
)
from bioetl.domain.behavior.merged_metadata_helpers import (
    resolve_final_value_source as _resolve_final_value_source,
)
from bioetl.domain.behavior.merged_metadata_helpers import (
    resolve_priority_order as _resolve_priority_order,
)
from bioetl.domain.behavior.merged_metadata_helpers import (
    resolve_record_id as _resolve_record_id,
)
from bioetl.domain.types import JsonDict

__all__ = ["_deterministic_record_id", "_json_fallback"]

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import CompositeOutputExt


@dataclass(frozen=True)
class MergedFieldExplanation:
    """Explanation for a single merged field."""

    field_name: str
    source_providers: tuple[str, ...]
    merge_strategy: str
    priority_order: tuple[str, ...] | None = None
    final_value_source: str | None = None
    conflict_resolution: str | None = None
    enrichment_applied: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        """Freeze caller-provided collections for deep immutability."""
        object.__setattr__(self, "source_providers", tuple(self.source_providers))
        if self.priority_order is not None:
            object.__setattr__(self, "priority_order", tuple(self.priority_order))
        if self.enrichment_applied is not None:
            object.__setattr__(
                self,
                "enrichment_applied",
                tuple(self.enrichment_applied),
            )


@dataclass(frozen=True)
class MergedRecordExplanation:
    """Explanation for a complete merged record."""

    record_id: str
    composite_run_id: str
    source_providers: tuple[str, ...]
    field_explanations: tuple[MergedFieldExplanation, ...]
    merge_strategy: str
    conflict_count: int = 0
    enrichment_count: int = 0

    def __post_init__(self) -> None:
        """Freeze caller-provided collections for deep immutability."""
        object.__setattr__(self, "source_providers", tuple(self.source_providers))
        object.__setattr__(self, "field_explanations", tuple(self.field_explanations))


class MergedMetadataExplainer:
    """Explainer for merged-record provenance and merge decisions."""

    def generate_field_explanation(
        self,
        field_name: str,
        _record_data: JsonDict,
        composite_metadata: CompositeOutputExt,
        field_priorities: dict[str, JsonDict] | None = None,
        merge_strategy: str = "prioritize",
    ) -> MergedFieldExplanation:
        """Describe how one merged field was selected and enriched."""
        source_providers = tuple(composite_metadata.source_providers or ())
        priority_order = _resolve_priority_order(field_name, field_priorities)
        final_value_source = _resolve_final_value_source(
            source_providers=source_providers,
            priority_order=priority_order,
        )
        return MergedFieldExplanation(
            field_name=field_name,
            source_providers=source_providers,
            merge_strategy=merge_strategy,
            priority_order=priority_order,
            final_value_source=final_value_source,
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
        field_explanations = tuple(
            self.generate_field_explanation(
                field_name,
                record_data,
                composite_metadata,
                field_priorities,
                merge_strategy,
            )
            for field_name in _public_field_names(record_data)
        )
        conflict_count, enrichment_count = _count_conflicts_and_enrichments(
            field_explanations
        )
        return MergedRecordExplanation(
            record_id=record_id,
            composite_run_id=composite_metadata.composite_run_id or "unknown",
            source_providers=tuple(composite_metadata.source_providers or ()),
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


def _count_conflicts_and_enrichments(
    field_explanations: tuple[MergedFieldExplanation, ...],
) -> tuple[int, int]:
    conflict_count = sum(1 for exp in field_explanations if exp.conflict_resolution)
    # Count distinct enrichers once per record, not once per field.
    enrichers: set[str] = set()
    for exp in field_explanations:
        if exp.enrichment_applied:
            enrichers.update(exp.enrichment_applied)
    return conflict_count, len(enrichers)


def _empty_explainability_summary() -> JsonDict:
    return {
        "record_count": 0,
        "field_count": 0,
        "avg_fields_per_record": 0.0,
        "source_provider_distribution": {},
        "merge_strategy_distribution": {},
        "conflict_summary": {
            "total_conflicts": 0,
            "conflict_rate": 0.0,
            "records_with_conflicts": 0,
        },
        "enrichment_summary": {
            "total_enrichments": 0,
            "enrichment_rate": 0.0,
            "records_with_enrichments": 0,
        },
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
    # enrichment_count is now distinct enrichers per record; rate uses records.
    records_with_enrichments = sum(
        1 for exp in explanations if exp.enrichment_count > 0
    )
    return {
        "total_enrichments": totals["total_enrichments"],
        "enrichment_rate": _safe_ratio(
            records_with_enrichments,
            totals["total_records"],
        ),
        "records_with_enrichments": records_with_enrichments,
    }


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def create_merged_metadata_explainability_service() -> MergedMetadataExplainer:
    """Factory function for the canonical merged metadata explainer."""
    return MergedMetadataExplainer()
