"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.dict_transformers import (
    aggregate_nested_lists,
    extract_list_field,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Target
from bioetl.domain.transformations import safe_int
from bioetl.domain.value_objects import TaxonomyId

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TargetTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    entity_class = Target
    primary_id_field = "target_id"

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Support both unified and legacy target identifier field names."""
        if "target_id" not in record and record.get("target_chembl_id") is not None:
            record = dict(record)
            record["target_id"] = record.get("target_chembl_id")
        return await super()._transform_impl(context, record, index)

    def _flatten_target_components(
        self, components: list[dict[str, Any]] | None
    ) -> dict[str, list[Any] | None]:
        """Flatten target components into aggregated lists.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships,
            descriptions, organisms, and taxonomy_ids.

        Note:
            protein_classifications are NOT available in /target endpoint.
            They are only available via /target_component endpoint.

        """
        if not components or not isinstance(components, list):
            return self._empty_component_result()

        return self._extract_basic_component_fields(components)

    def _empty_component_result(self) -> dict[str, list[Any] | None]:
        """Return empty result dict for missing components."""
        return {
            "component_accessions": None,
            "component_ids": None,
            "component_types": None,
            "component_relationships": None,
            "component_descriptions": None,
        }

    def _extract_basic_component_fields(
        self, components: list[dict[str, Any]]
    ) -> dict[str, list[Any] | None]:
        """Extract basic fields from component list via dict_transformers."""
        return {
            "component_accessions": extract_list_field(components, "accession"),
            "component_ids": extract_list_field(components, "component_id", safe_int),
            "component_types": extract_list_field(components, "component_type"),
            "component_relationships": extract_list_field(components, "relationship"),
            "component_descriptions": extract_list_field(
                components, "component_description"
            ),
        }

    def _aggregate_synonyms(
        self, components: list[dict[str, Any]] | None
    ) -> str | int | float | bool | None:
        """Aggregate synonyms from all components into a single JSON list.

        Uses aggregate_nested_lists from dict_transformers.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            JSON string of list of synonyms, or None.

        """
        synonyms = aggregate_nested_lists(components, "target_component_synonyms")
        return self.serialize_json(synonyms) if synonyms else None

    def _aggregate_component_xrefs(
        self, components: list[dict[str, Any]] | None
    ) -> str | int | float | bool | None:
        """Aggregate cross-references from all target components.

        Uses aggregate_nested_lists from dict_transformers.
        ChEMBL API stores cross-references inside each component's
        target_component_xrefs field, not at the target level.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            JSON string of aggregated xrefs, or None if empty.

        """
        xrefs = aggregate_nested_lists(components, "target_component_xrefs")
        return self.serialize_json(xrefs) if xrefs else None

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Target business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated target_id value.

        Returns:
            Dictionary of Target business fields.

        """
        # Extract target_components with proper typing
        target_components = cast(
            "list[dict[str, Any]] | None", record.get("target_components")
        )

        # Extract flattened components
        flattened_components = self._flatten_target_components(target_components)

        # Extract primary component_id (first element) for enricher join key
        component_ids = flattened_components.get("component_ids")
        primary_component_id = component_ids[0] if component_ids else None

        # Handle downgraded field: convert to bool if it's 0/1
        # Use safe_int to handle "0"/"1" strings correctly
        downgraded_val = safe_int(record.get("downgraded"))
        # Default to False if missing or invalid, to ensure boolean dtype for Gold schema
        downgraded = bool(downgraded_val) if downgraded_val is not None else False

        # Validate taxonomy_id using TaxonomyId Value Object
        raw_tax_id = record.get("tax_id")
        taxonomy_id_vo = TaxonomyId.from_raw(
            cast("str | int | None", raw_tax_id) if raw_tax_id is not None else None
        )
        taxonomy_id = taxonomy_id_vo.value if taxonomy_id_vo else None

        return {
            # Primary identifier
            "target_id": str(primary_id),
            # Primary component ID (for target_component enricher join)
            "primary_component_id": primary_component_id,
            # Core metadata
            "pref_name": record.get("pref_name"),
            "target_type": record.get("target_type"),
            "organism": record.get("organism"),
            # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
            "taxonomy_id": taxonomy_id,
            "description": record.get("description"),
            "species_group_flag": record.get("species_group_flag"),
            "downgraded": downgraded,
            "pipeline_stages": self.serialize_json(record.get("pipeline_stages")),
            # Complex fields (JSON serialized)
            "target_components": self.serialize_json(target_components),
            "target_component_synonyms": self._aggregate_synonyms(target_components),
            "cross_references": self._aggregate_component_xrefs(target_components),
            # Flattened components
            **flattened_components,
        }
