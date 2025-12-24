"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Target
from bioetl.domain.transformations import generate_entity_id, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


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

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships,
            descriptions, organisms, tax_ids, and protein classifications.
        """
        if not components or not isinstance(components, list):
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

        accessions = [c.get("accession") for c in components if c.get("accession")]
        ids = [
            safe_int(c.get("component_id"))
            for c in components
            if c.get("component_id") is not None
        ]
        types = [c.get("component_type") for c in components if c.get("component_type")]
        relationships = [
            c.get("relationship") for c in components if c.get("relationship")
        ]
        descriptions = [
            c.get("component_description")
            for c in components
            if c.get("component_description")
        ]

        # Extract organisms and tax_ids from components
        organisms = [c.get("organism") for c in components if c.get("organism")]
        tax_ids = [
            safe_int(c.get("tax_id"))
            for c in components
            if c.get("tax_id") is not None
        ]

        # Flatten protein classifications with full details
        classification_short_names: list[str] = []
        classification_ids: list[int] = []
        classification_pref_names: list[str] = []

        for c in components:
            pcs = c.get("protein_classifications")
            if pcs and isinstance(pcs, list):
                for pc in pcs:
                    if isinstance(pc, dict):
                        # Extract short_name
                        short_name = pc.get("short_name")
                        if short_name:
                            classification_short_names.append(short_name)

                        # Extract protein_classification_id
                        pc_id = safe_int(pc.get("protein_classification_id"))
                        if pc_id is not None:
                            classification_ids.append(pc_id)

                        # Extract pref_name (class name)
                        pref_name = pc.get("pref_name")
                        if pref_name:
                            classification_pref_names.append(pref_name)

        return {
            "component_accessions": accessions if accessions else None,
            "component_ids": ids if ids else None,
            "component_types": types if types else None,
            "component_relationships": relationships if relationships else None,
            "component_descriptions": descriptions if descriptions else None,
            "component_organisms": organisms if organisms else None,
            "component_tax_ids": tax_ids if tax_ids else None,
            "protein_classifications": (
                classification_short_names if classification_short_names else None
            ),
            "protein_classification_ids": (
                classification_ids if classification_ids else None
            ),
            "protein_classification_names": (
                classification_pref_names if classification_pref_names else None
            ),
        }

    def _aggregate_synonyms(
        self, components: list[dict[str, Any]] | None
    ) -> str | None:
        """Aggregate synonyms from all components into a single JSON list.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            JSON string of list of synonyms, or None.
        """
        if not components or not isinstance(components, list):
            return None

        all_synonyms = []
        for comp in components:
            synonyms = comp.get("target_component_synonyms")
            if synonyms and isinstance(synonyms, list):
                all_synonyms.extend(synonyms)

        return self.serialize_json(all_synonyms) if all_synonyms else None

    def _aggregate_component_xrefs(
        self, components: list[dict[str, Any]] | None
    ) -> str | None:
        """Aggregate cross-references from all target components.

        ChEMBL API stores cross-references inside each component's
        target_component_xrefs field, not at the target level.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            JSON string of aggregated xrefs, or None if empty.
        """
        if not components or not isinstance(components, list):
            return None

        all_xrefs: list[dict[str, Any]] = []
        for comp in components:
            xrefs = comp.get("target_component_xrefs")
            if xrefs and isinstance(xrefs, list):
                all_xrefs.extend(xrefs)

        return self.serialize_json(all_xrefs) if all_xrefs else None
