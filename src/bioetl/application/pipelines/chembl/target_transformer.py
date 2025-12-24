"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.transform_utils import (
    aggregate_nested_lists,
    extract_list_field,
)
from bioetl.domain.entities import Target
from bioetl.domain.transformations import generate_entity_id, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TargetTransformer(BaseTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    def __init__(self, provider: str = "chembl"):
        """Initialize ChEMBL target transformer.

        Args:
            provider: Data provider identifier.

        """
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

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships,
            descriptions, organisms, tax_ids, and protein classifications.

        """
        if not components or not isinstance(components, list):
            return self._empty_component_result()

        basic_fields = self._extract_basic_component_fields(components)
        classifications = self._extract_protein_classifications(components)

        return {**basic_fields, **classifications}

    def _empty_component_result(self) -> dict[str, None]:
        """Return empty result dict for missing components."""
        return {
            "component_accessions": None,
            "component_ids": None,
            "component_types": None,
            "component_relationships": None,
            "component_descriptions": None,
            "component_organisms": None,
            "component_tax_ids": None,
            "protein_classifications": None,
            "protein_classification_ids": None,
            "protein_classification_names": None,
        }

    def _extract_basic_component_fields(
        self, components: list[dict[str, Any]]
    ) -> dict[str, list[Any] | None]:
        """Extract basic fields from component list via transform_utils."""
        return {
            "component_accessions": extract_list_field(components, "accession"),
            "component_ids": extract_list_field(components, "component_id", safe_int),
            "component_types": extract_list_field(components, "component_type"),
            "component_relationships": extract_list_field(components, "relationship"),
            "component_descriptions": extract_list_field(
                components, "component_description"
            ),
            "component_organisms": extract_list_field(components, "organism"),
            "component_tax_ids": extract_list_field(components, "tax_id", safe_int),
        }

    def _extract_protein_classifications(
        self, components: list[dict[str, Any]]
    ) -> dict[str, list[Any] | None]:
        """Extract protein classification details from components."""
        short_names: list[str] = []
        ids: list[int] = []
        pref_names: list[str] = []

        for c in components:
            pcs = c.get("protein_classifications")
            if not pcs or not isinstance(pcs, list):
                continue
            for pc in pcs:
                if not isinstance(pc, dict):
                    continue
                self._collect_classification_fields(pc, short_names, ids, pref_names)

        return {
            "protein_classifications": short_names or None,
            "protein_classification_ids": ids or None,
            "protein_classification_names": pref_names or None,
        }

    def _collect_classification_fields(
        self,
        pc: dict[str, Any],
        short_names: list[str],
        ids: list[int],
        pref_names: list[str],
    ) -> None:
        """Collect fields from a single protein classification dict."""
        if short_name := pc.get("short_name"):
            short_names.append(short_name)
        if (pc_id := safe_int(pc.get("protein_classification_id"))) is not None:
            ids.append(pc_id)
        if pref_name := pc.get("pref_name"):
            pref_names.append(pref_name)

    def _aggregate_synonyms(
        self, components: list[dict[str, Any]] | None
    ) -> str | None:
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
    ) -> str | None:
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
