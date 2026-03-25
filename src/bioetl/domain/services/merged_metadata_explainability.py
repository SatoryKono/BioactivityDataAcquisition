"""Merged metadata explainability service for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bioetl.domain.types import JsonDict
from bioetl.domain.models.metadata import CompositeOutputExt


@dataclass(frozen=True)
class MergedFieldExplanation:
    """Explanation for a single merged field."""

    field_name: str
    """Name of the field being explained."""
    
    source_providers: list[str]
    """List of source providers that contributed to this field."""
    
    merge_strategy: str
    """Strategy used to merge values (prioritize, concatenate, etc.)."""
    
    priority_order: Optional[list[str]] = None
    """Priority order of sources if prioritize strategy was used."""
    
    final_value_source: Optional[str] = None
    """Source that provided the final value."""
    
    conflict_resolution: Optional[str] = None
    """How conflicts were resolved (if any)."""
    
    enrichment_applied: Optional[list[str]] = None
    """Enrichments applied to this field."""


@dataclass(frozen=True)
class MergedRecordExplanation:
    """Explanation for a complete merged record."""

    record_id: str
    """Identifier for the record being explained."""
    
    composite_run_id: str
    """Composite run that produced this record."""
    
    source_providers: list[str]
    """All source providers that contributed to this record."""
    
    field_explanations: list[MergedFieldExplanation]
    """Detailed explanations for each field."""
    
    merge_strategy: str
    """Overall merge strategy used."""
    
    conflict_count: int = 0
    """Number of conflicts that were resolved."""
    
    enrichment_count: int = 0
    """Number of enrichments applied."""


class MergedMetadataExplainabilityService:
    """Service for generating explainability metadata for merged records."""

    def generate_field_explanation(
        self,
        field_name: str,
        record_data: JsonDict,
        composite_metadata: CompositeOutputExt,
        field_priorities: Optional[dict[str, dict]] = None,
    ) -> MergedFieldExplanation:
        """Generate explanation for a single merged field."""
        
        # Extract source providers from composite metadata
        source_providers = composite_metadata.source_providers or []
        
        # Determine merge strategy (could be extracted from config or metadata)
        merge_strategy = "prioritize"  # Default, could be made configurable
        
        # Extract priority order if available
        priority_order = None
        if field_priorities and field_name in field_priorities:
            priority_config = field_priorities[field_name]
            if "priority" in priority_config:
                # This would need to be extracted from the actual field priorities config
                priority_order = [str(p) for p in priority_config["priority"]] if isinstance(priority_config["priority"], list) else []
        
        # Determine final value source (simplified logic)
        final_value_source = source_providers[0] if source_providers else None
        
        # Check for enrichments
        enrichment_applied = None
        if composite_metadata.enrichment_status:
            field_enrichments = [enricher for enricher, status in composite_metadata.enrichment_status.items() if status == "applied"]
            if field_enrichments:
                enrichment_applied = field_enrichments
        
        return MergedFieldExplanation(
            field_name=field_name,
            source_providers=source_providers,
            merge_strategy=merge_strategy,
            priority_order=priority_order,
            final_value_source=final_value_source,
            conflict_resolution="priority_based" if priority_order else None,
            enrichment_applied=enrichment_applied,
        )

    def generate_record_explanation(
        self,
        record_id: str,
        record_data: JsonDict,
        composite_metadata: CompositeOutputExt,
        field_priorities: Optional[dict[str, dict]] = None,
        merge_strategy: str = "prioritize",
    ) -> MergedRecordExplanation:
        """Generate explanation for a complete merged record."""
        
        # Generate explanations for all fields in the record
        field_explanations = []
        conflict_count = 0
        enrichment_count = 0
        
        for field_name in record_data.keys():
            if field_name.startswith("_"):  # Skip internal fields
                continue
                
            field_explanation = self.generate_field_explanation(
                field_name, record_data, composite_metadata, field_priorities
            )
            field_explanations.append(field_explanation)
            
            # Count conflicts and enrichments
            if field_explanation.conflict_resolution:
                conflict_count += 1
            if field_explanation.enrichment_applied:
                enrichment_count += len(field_explanation.enrichment_applied)
        
        return MergedRecordExplanation(
            record_id=record_id,
            composite_run_id=composite_metadata.composite_run_id or "unknown",
            source_providers=composite_metadata.source_providers or [],
            field_explanations=field_explanations,
            merge_strategy=merge_strategy,
            conflict_count=conflict_count,
            enrichment_count=enrichment_count,
        )

    def generate_explainability_metadata(
        self,
        records: list[JsonDict],
        composite_metadata: CompositeOutputExt,
        field_priorities: Optional[dict[str, dict]] = None,
        merge_strategy: str = "prioritize",
    ) -> list[MergedRecordExplanation]:
        """Generate explainability metadata for multiple records."""
        
        explanations = []
        
        for record in records:
            record_id = record.get("_record_id") or record.get("id") or record.get("molecule_id") or str(hash(str(record)))
            
            explanation = self.generate_record_explanation(
                str(record_id),
                record,
                composite_metadata,
                field_priorities,
                merge_strategy,
            )
            explanations.append(explanation)
        
        return explanations

    def generate_explainability_summary(
        self,
        explanations: list[MergedRecordExplanation],
    ) -> JsonDict:
        """Generate a summary of explainability across multiple records."""
        
        if not explanations:
            return {
                "record_count": 0,
                "source_provider_distribution": {},
                "merge_strategy_distribution": {},
                "conflict_summary": {"total_conflicts": 0, "conflict_rate": 0.0},
                "enrichment_summary": {"total_enrichments": 0, "enrichment_rate": 0.0},
            }
        
        # Calculate statistics
        total_records = len(explanations)
        total_fields = sum(len(exp.field_explanations) for exp in explanations)
        total_conflicts = sum(exp.conflict_count for exp in explanations)
        total_enrichments = sum(exp.enrichment_count for exp in explanations)
        
        # Source provider distribution
        source_provider_distribution = {}
        merge_strategy_distribution = {}
        
        for explanation in explanations:
            for provider in explanation.source_providers:
                source_provider_distribution[provider] = source_provider_distribution.get(provider, 0) + 1
            
            merge_strategy = explanation.merge_strategy
            merge_strategy_distribution[merge_strategy] = merge_strategy_distribution.get(merge_strategy, 0) + 1
        
        return {
            "record_count": total_records,
            "field_count": total_fields,
            "avg_fields_per_record": total_fields / total_records if total_records > 0 else 0,
            "source_provider_distribution": source_provider_distribution,
            "merge_strategy_distribution": merge_strategy_distribution,
            "conflict_summary": {
                "total_conflicts": total_conflicts,
                "conflict_rate": total_conflicts / total_fields if total_fields > 0 else 0.0,
                "records_with_conflicts": sum(1 for exp in explanations if exp.conflict_count > 0),
            },
            "enrichment_summary": {
                "total_enrichments": total_enrichments,
                "enrichment_rate": total_enrichments / total_fields if total_fields > 0 else 0.0,
                "records_with_enrichments": sum(1 for exp in explanations if exp.enrichment_count > 0),
            },
        }

    def generate_field_priority_explanation(
        self,
        field_priorities: dict[str, dict],
    ) -> list[JsonDict]:
        """Generate explanations for field priority configurations."""
        
        explanations = []
        
        for field_name, priority_config in field_priorities.items():
            explanation = {
                "field_name": field_name,
                "priority_order": priority_config.get("priority", []),
                "source": priority_config.get("source"),
                "fallback_strategy": priority_config.get("fallback", "keep_first"),
                "conflict_resolution": priority_config.get("conflict_resolution", "priority_based"),
            }
            explanations.append(explanation)
        
        return explanations


def create_merged_metadata_explainability_service() -> MergedMetadataExplainabilityService:
    """Factory function for MergedMetadataExplainabilityService."""
    return MergedMetadataExplainabilityService()