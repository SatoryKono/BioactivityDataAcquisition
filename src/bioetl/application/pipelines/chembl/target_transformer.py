"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.transform_utils import (
    aggregate_nested_list,
    build_empty_field_dict,
    extract_list_field,
    extract_nested_field_values,
    safe_int,
)
from bioetl.domain.entities import Target
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord

# Field names for empty component result
_COMPONENT_FIELDS = [
    "component_accessions",
    "component_ids",
    "component_types",
    "component_relationships",
    "component_descriptions",
    "component_organisms",
    "component_tax_ids",
    "protein_classifications",
    "protein_classification_ids",
    "protein_classification_names",
]


class TargetTransformer(BaseTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    def __init__(self, provider: str = "chembl"):
        super().__init__(provider)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL target to normalized format using Domain Entity."""
        # Validate required field
        target_chembl_id = self._get_required_field(record, "target_chembl_id")

        entity_id = generate_entity_id(
            record={"target_chembl_id": str(target_chembl_id)},
            provider=self.provider,
            id_field="target_chembl_id",
        )

        # Extract flattened components
        flattened_components = self._flatten_target_components(
            record.get("target_components")
        )

        business_data: dict[str, Any] = {
            # Primary identifier
            "target_chembl_id": str(target_chembl_id),
            # Core metadata
            "pref_name": record.get("pref_name"),
            "target_type": record.get("target_type"),
            "organism": record.get("organism"),
            "tax_id": safe_int(record.get("tax_id")),
            "species_group_flag": record.get("species_group_flag"),
            "description": record.get("description"),
            "downgraded": record.get("downgraded"),
            # Optional fields (present for specific target types)
            "dap_id": safe_int(record.get("dap_id")),
            "pipeline_stages": self.serialize_json(record.get("pipeline_stages")),
            "target_constraints": self.serialize_json(
                record.get("target_constraints")
            ),
            # Complex fields (JSON serialized)
            "target_components": self.serialize_json(
                record.get("target_components")
            ),
            "target_component_synonyms": self._aggregate_synonyms(
                record.get("target_components")
            ),
            "cross_references": self._aggregate_component_xrefs(
                record.get("target_components")
            ),
            # Flattened components
            **flattened_components,
        }

        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Create entity using helper method
        entity = self._create_entity(
            Target,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        # Convert Entity to SilverRecord for storage
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _flatten_target_components(
        self, components: list[dict[str, Any]] | None
    ) -> dict[str, list[Any] | None]:
        """Flatten target components into aggregated lists.

        Uses transform_utils for extraction to reduce code duplication.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships,
            descriptions, organisms, tax_ids, and protein classifications.
        """
        if not components or not isinstance(components, list):
            return cast("dict[str, list[Any] | None]", build_empty_field_dict(_COMPONENT_FIELDS))

        # Extract basic fields using utility
        basic_fields = {
            "component_accessions": extract_list_field(components, "accession"),
            "component_ids": extract_list_field(
                components, "component_id", converter=safe_int
            ),
            "component_types": extract_list_field(components, "component_type"),
            "component_relationships": extract_list_field(components, "relationship"),
            "component_descriptions": extract_list_field(
                components, "component_description"
            ),
            "component_organisms": extract_list_field(components, "organism"),
            "component_tax_ids": extract_list_field(
                components, "tax_id", converter=safe_int
            ),
        }

        # Extract protein classifications using nested field utility
        classifications = {
            "protein_classifications": extract_nested_field_values(
                components, "protein_classifications", "short_name"
            ),
            "protein_classification_ids": extract_nested_field_values(
                components, "protein_classifications", "protein_classification_id",
                converter=safe_int
            ),
            "protein_classification_names": extract_nested_field_values(
                components, "protein_classifications", "pref_name"
            ),
        }

        return {**basic_fields, **classifications}

    def _aggregate_synonyms(
        self, components: list[dict[str, Any]] | None
    ) -> str | None:
        """Aggregate synonyms from all components into a single JSON list."""
        aggregated = aggregate_nested_list(components, "target_component_synonyms")
        return self.serialize_json(aggregated) if aggregated else None

    def _aggregate_component_xrefs(
        self, components: list[dict[str, Any]] | None
    ) -> str | None:
        """Aggregate cross-references from all target components."""
        aggregated = aggregate_nested_list(components, "target_component_xrefs")
        return self.serialize_json(aggregated) if aggregated else None
