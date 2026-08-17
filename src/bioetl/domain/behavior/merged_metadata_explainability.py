"""Merged metadata explainer for composite pipelines."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from bioetl.domain.behavior import composite_metadata_cv
from bioetl.domain.behavior.composite_metadata_helpers import (
    resolve_final_value_source as _resolve_final_value_source,
)
from bioetl.domain.behavior.composite_metadata_helpers import (
    resolve_priority_order as _resolve_priority_order,
)
from bioetl.domain.types import JsonDict

_build_explainability_summary = composite_metadata_cv.build_explainability_summary
_empty_explainability_summary = composite_metadata_cv.empty_explainability_summary
_safe_ratio = composite_metadata_cv.safe_ratio

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
        """Freeze all nested collections supplied by callers."""
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
        """Freeze all nested collections supplied by callers."""
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


def _extract_applied_enrichments(
    composite_metadata: CompositeOutputExt,
) -> tuple[str, ...] | None:
    if not composite_metadata.enrichment_status:
        return None
    applied = [
        enricher
        for enricher, status in composite_metadata.enrichment_status.items()
        if status == "applied"
    ]
    return tuple(applied) or None


def _public_field_names(record_data: JsonDict) -> list[str]:
    return [name for name in record_data if not name.startswith("_")]


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


def _resolve_record_id(record: JsonDict) -> str:
    """Resolve a stable record id, preserving valid falsy identifiers."""
    for key in ("_record_id", "id", "molecule_id"):
        if key in record and record[key] is not None:
            return str(record[key])
    return _deterministic_record_id(record)


def _deterministic_record_id(record: JsonDict) -> str:
    """Produce a deterministic id even for non-JSON-native supported values."""
    payload = _canonical_json_text(record)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_json_text(value: object) -> str:
    """Serialize supported values without identity-bearing repr fallbacks."""
    return json.dumps(
        _canonical_json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_json_fallback,
    )


def _canonical_json_value(value: object) -> object:
    """Normalize containers, including mappings with mixed scalar key types."""
    if isinstance(value, dict):
        return _canonical_json_mapping(value)
    if isinstance(value, list | tuple):
        return [_canonical_json_value(item) for item in value]
    return value


def _canonical_json_mapping(value: dict[object, object]) -> object:
    if all(isinstance(key, str) for key in value):
        return {
            key: _canonical_json_value(item)
            for key, item in value.items()
            if isinstance(key, str)
        }
    return {"\u0000bioetl:typed-mapping:v1": _typed_mapping_items(value)}


def _typed_mapping_items(
    value: dict[object, object],
) -> list[tuple[dict[str, object], object]]:
    items = [
        (
            {"type": type(key).__name__, "value": _canonical_json_value(key)},
            _canonical_json_value(item),
        )
        for key, item in value.items()
    ]
    return sorted(items, key=lambda item: _canonical_json_text(item[0]))


def _json_fallback(value: object) -> object:
    converted = _temporal_or_decimal(value)
    if converted is not None:
        return converted
    if isinstance(value, (set, frozenset)):
        return _canonical_set_members(value)
    return _bytes_or_reject(value)


def _temporal_or_decimal(value: object) -> object | None:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return _canonical_set_members(value)
    return _bytes_or_reject(value)


def _canonical_set_members(value: set[object] | frozenset[object]) -> list[object]:
    canonical_items = sorted(_canonical_json_text(item) for item in value)
    return [json.loads(item) for item in canonical_items]


def _bytes_or_reject(value: object) -> str:
    if isinstance(value, bytes):
        return value.hex()
    raise TypeError(
        f"Unsupported value for deterministic record identity: {type(value).__name__}"
    )


def create_merged_metadata_explainability_service() -> MergedMetadataExplainer:
    """Factory function for the canonical merged metadata explainer."""
    return MergedMetadataExplainer()
