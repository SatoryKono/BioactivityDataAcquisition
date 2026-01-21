"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.transform_utils import (
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
    from bioetl.domain.types import BronzeRecord


class TargetTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    entity_class = Target
    primary_id_field = "target_chembl_id"

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
            "component_organisms": None,
            # Standardized to 'taxonomy_ids' for NCBI consistency
            "component_taxonomy_ids": None,
        }

    def _extract_basic_component_fields(
        self, components: list[dict[str, Any]]
    ) -> dict[str, list[Any] | None]:
        """Extract basic fields from component list via transform_utils."""
        # Extract taxonomy IDs and validate using TaxonomyId Value Object
        raw_tax_ids = extract_list_field(components, "tax_id", safe_int)
        validated_tax_ids: list[int] | None = None
        if raw_tax_ids:
            validated_list: list[int] = []
            for tid in raw_tax_ids:
                vo = TaxonomyId.from_raw(tid)
                if vo is not None:
                    validated_list.append(vo.value)
            validated_tax_ids = validated_list if validated_list else None

        return {
            "component_accessions": extract_list_field(components, "accession"),
            "component_ids": extract_list_field(components, "component_id", safe_int),
            "component_types": extract_list_field(components, "component_type"),
            "component_relationships": extract_list_field(components, "relationship"),
            "component_descriptions": extract_list_field(
                components, "component_description"
            ),
            "component_organisms": extract_list_field(components, "organism"),
            # Standardized to 'taxonomy_ids' for NCBI consistency
            "component_taxonomy_ids": validated_tax_ids,
        }

    def _aggregate_synonyms(
        self, components: list[dict[str, Any]] | None
    ) -> str | int | float | bool | None:
        """Aggregate synonyms from all components into a single JSON list.

        Uses aggregate_nested_lists from transform_utils.

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

        Uses aggregate_nested_lists from transform_utils.
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
            primary_id: Validated target_chembl_id value.

        Returns:
            Dictionary of Target business fields.

        """
        # Extract target_components with proper typing
        target_components = cast(
            "list[dict[str, Any]] | None", record.get("target_components")
        )

        # Extract flattened components
        flattened_components = self._flatten_target_components(target_components)

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
            "target_chembl_id": str(primary_id),
            # Core metadata
            "pref_name": record.get("pref_name"),
            "target_type": record.get("target_type"),
            "organism": record.get("organism"),
            # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
            "taxonomy_id": taxonomy_id,
            "species_group_flag": record.get("species_group_flag"),
            "description": record.get("description"),
            "downgraded": downgraded,
            # Optional fields (present for specific target types)
            "dap_id": safe_int(record.get("dap_id")),
            "pipeline_stages": self.serialize_json(record.get("pipeline_stages")),
            "target_constraints": self.serialize_json(record.get("target_constraints")),
            # Complex fields (JSON serialized)
            "target_components": self.serialize_json(target_components),
            "target_component_synonyms": self._aggregate_synonyms(target_components),
            "cross_references": self._aggregate_component_xrefs(target_components),
            # Flattened components
            **flattened_components,
        }
