"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

__all__ = ["TargetTransformer"]

from collections.abc import Mapping
from typing import TYPE_CHECKING, ClassVar, cast

from bioetl.application.core.dict_transformers import (
    aggregate_nested_lists,
    extract_list_field,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.application.pipelines.chembl.provider_aliases import (
    normalize_provider_aliases,
)
from bioetl.application.pipelines.chembl.target_helpers import (
    ComponentHelper,
    SynonymHelper,
    XrefHelper,
)
from bioetl.domain.entities import Target
from bioetl.domain.types import GoldRecord, JsonDict
from bioetl.domain.value_objects.taxonomy_id import TaxonomyId

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord

_MULTIFUNCTIONAL_TARGET_L1_NAME = "Multifunctional target"
_PROTEIN_CLASSIFICATION_ID_KEYS = (
    "leaf_id",
    "protein_classification_id",
    "protein_class_id",
)


class TargetTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    entity_class = Target
    primary_id_field = "target_id"
    _PROVIDER_ALIASES: ClassVar[dict[str, str]] = {"target_id": "target_chembl_id"}

    def _prepare_record(
        self,
        record: BronzeRecord,
    ) -> BronzeRecord:
        """Normalize provider-native target identifiers at the ingestion boundary."""
        return normalize_provider_aliases(record, self._PROVIDER_ALIASES)

    def _flatten_target_components(
        self,
        components: list[JsonDict] | None,
    ) -> dict[str, list | None]:
        """Flatten target components into aggregated lists.

        Args:
            components: List of component dicts from ChEMBL API.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships,
            and descriptions.

        """
        return ComponentHelper.flatten_target_components(
            components,
            extract_list_field,
        )

    def _aggregate_synonyms(
        self,
        components: list[JsonDict] | None,
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

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> GoldRecord:
        """Extract Target business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated target_id value.

        Returns:
            Dictionary of Target business fields.

        """
        # Extract target_components with proper typing
        target_components = cast(
            "list[JsonDict] | None",  # Any: untyped ChEMBL API JSON
            record.get("target_components"),
        )

        # Extract flattened components
        flattened_components = self._flatten_target_components(target_components)
        serialized_flattened_components = {
            key: self.serialize_json_list(value) if isinstance(value, list) else None
            for key, value in flattened_components.items()
        }

        # Extract primary component_id (first element) for enricher join key
        component_ids = flattened_components.get("component_ids")
        primary_component_id = component_ids[0] if component_ids else None
        projected_synonyms = SynonymHelper.project_component_synonyms(
            target_components
        )
        component_xrefs = XrefHelper.collect_component_xrefs(target_components)
        xref_projection = XrefHelper.project_component_xrefs(component_xrefs)
        protein_classifications = self._project_protein_classifications(
            target_components
        )

        # Validate taxonomy_id using TaxonomyId Value Object
        raw_tax_id = record.get("tax_id")
        taxonomy_id_vo = TaxonomyId.from_raw(
            cast("str | int | None", raw_tax_id) if raw_tax_id is not None else None
        )
        taxonomy_id = taxonomy_id_vo.value if taxonomy_id_vo else None

        organism_name = cast("str | None", record.get("organism"))

        return {
            # Primary identifier
            "target_id": str(primary_id),
            # Core metadata
            "target_type": record.get("target_type"),
            "pref_name": record.get("pref_name"),
            # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
            "taxonomy_id": taxonomy_id,
            "organism": organism_name,
            # Shared domain normalization owns deterministic cellularity derivation.
            "organism_class": record.get("organism_class"),
            "species_group_flag": record.get("species_group_flag"),
            "target_description": record.get("target_description")
            or record.get("description"),
            **projected_synonyms,
            "target_xref_pdb_ids": xref_projection["target_xref_pdb_ids"],
            "target_xref_go_component": xref_projection[
                "target_xref_go_component"
            ],
            "target_xref_go_function": xref_projection[
                "target_xref_go_function"
            ],
            "target_xref_go_process": xref_projection[
                "target_xref_go_process"
            ],
            "target_xref_hgnc_ids": xref_projection["target_xref_hgnc_ids"],
            "target_xref_reactome_ids": xref_projection["target_xref_reactome_ids"],
            "target_xref_uniprot_ids": xref_projection["target_xref_uniprot_ids"],
            # Primary component ID (for target_component enricher join)
            "primary_component_id": primary_component_id,
            "protein_classifications": protein_classifications,
            # Flattened components
            **serialized_flattened_components,
            # Complex fields (JSON serialized)
            "target_components": self.serialize_json(target_components),
            "cross_references": self.serialize_json(component_xrefs)
            if component_xrefs
            else None,
            "target_component_synonyms": self._aggregate_synonyms(target_components),
        }

    def _postprocess_pre_silver_record(
        self,
        silver_record: SilverRecord,
        *,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Align silver output with the published target schema field name."""
        description = silver_record.get("target_description")
        if description is None:
            description = silver_record.pop("description", None)
        if description is None:
            description = business_data.get("target_description")
        if description is None:
            description = business_data.get("description")
        silver_record.pop("description", None)
        silver_record["target_description"] = description
        silver_record["protein_classifications"] = business_data.get(
            "protein_classifications"
        )
        return silver_record

    def transform_for_gold(
        self,
        context: PipelineContext,
        silver_record: GoldRecord,
    ) -> GoldRecord:
        """Project the Silver field name back to the published Gold contract."""
        gold_record = super().transform_for_gold(context, silver_record)
        description = gold_record.pop("target_description", None)
        gold_record["description"] = description
        return gold_record

    def _project_protein_classifications(
        self,
        components: list[JsonDict] | None,
    ) -> str | None:
        """Project component protein classifications into target-level JSON."""
        classifications = _collect_protein_classifications(components)
        if not classifications:
            return None
        if len(classifications) == 1:
            return self.serialize_json_list(classifications)
        return self.serialize_json_list(
            [
                {
                    "classification_status": "resolved",
                    "l1_name": _MULTIFUNCTIONAL_TARGET_L1_NAME,
                    "source_classifications": classifications,
                    "source_hierarchy_count": len(classifications),
                    "source_leaf_ids": [
                        classification["leaf_id"]
                        for classification in classifications
                    ],
                }
            ]
        )


def _collect_protein_classifications(
    components: list[JsonDict] | None,
) -> list[JsonDict]:
    """Collect unique component classification payloads in leaf-id order."""
    if not components:
        return []

    by_leaf_id: dict[int, JsonDict] = {}
    for component in components:
        raw_classifications = component.get("protein_classifications")
        if not isinstance(raw_classifications, list):
            continue
        for raw_classification in raw_classifications:
            classification = _normalize_protein_classification(raw_classification)
            if classification is None:
                continue
            leaf_id = cast("int", classification["leaf_id"])
            by_leaf_id.setdefault(leaf_id, classification)
    return [by_leaf_id[leaf_id] for leaf_id in sorted(by_leaf_id)]


def _normalize_protein_classification(value: object) -> JsonDict | None:
    """Normalize one protein classification item for deterministic JSON output."""
    if not isinstance(value, Mapping):
        return None
    leaf_id = _protein_classification_leaf_id(value)
    if leaf_id is None:
        return None

    classification: JsonDict = {
        str(key): item
        for key, item in value.items()
        if item is not None and str(key).strip()
    }
    classification["classification_status"] = "resolved"
    classification["leaf_id"] = leaf_id
    classification.setdefault("protein_classification_id", leaf_id)
    return classification


def _protein_classification_leaf_id(value: Mapping[object, object]) -> int | None:
    """Extract a positive protein classification leaf ID from a raw item."""
    for key in _PROTEIN_CLASSIFICATION_ID_KEYS:
        leaf_id = _coerce_positive_int(value.get(key))
        if leaf_id is not None:
            return leaf_id
    return None


def _coerce_positive_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return _positive_int_or_none(value)
    if isinstance(value, float):
        return _coerce_positive_int_from_float(value)
    if isinstance(value, str):
        return _coerce_positive_int_from_str(value)
    return None


def _positive_int_or_none(value: int) -> int | None:
    """Return positive integers unchanged, otherwise None."""
    return value if value > 0 else None


def _coerce_positive_int_from_float(value: float) -> int | None:
    """Coerce integral positive floats to int."""
    if not value.is_integer():
        return None
    return _positive_int_or_none(int(value))


def _coerce_positive_int_from_str(value: str) -> int | None:
    """Coerce positive integer strings to int."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        coerced = int(stripped)
    except ValueError:
        return None
    return _positive_int_or_none(coerced)
