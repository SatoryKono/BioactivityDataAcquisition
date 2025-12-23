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

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL target to normalized format using Domain Entity."""
        target_chembl_id = record.get("target_chembl_id")

        if not target_chembl_id:
            return None

        try:
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

            entity = Target(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )

        except ValueError as e:
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                target_chembl_id=target_chembl_id,
            )
            return None

        # Convert Entity to SilverRecord for storage
        silver_record = self.entity_to_silver_record(entity)

        return cast("SilverRecord", silver_record)

    def _flatten_target_components(
        self, components: list[dict[str, Any]] | None
    ) -> dict[str, list[Any] | None]:
        """Flatten target components into aggregated lists.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships, and descriptions.
        """
        if not components or not isinstance(components, list):
            return {
                "component_accessions": None,
                "component_ids": None,
                "component_types": None,
                "component_relationships": None,
                "component_descriptions": None,
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

        return {
            "component_accessions": accessions if accessions else None,
            "component_ids": ids if ids else None,
            "component_types": types if types else None,
            "component_relationships": relationships if relationships else None,
            "component_descriptions": descriptions if descriptions else None,
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
