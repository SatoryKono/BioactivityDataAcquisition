"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

__all__ = ["TargetTransformer"]


from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, cast

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
from bioetl.domain.entities import Target
from bioetl.domain.transformations import safe_int
from bioetl.domain.types import GoldRecord, JsonDict
from bioetl.domain.value_objects.taxonomy_id import TaxonomyId

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord


class TargetTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    entity_class = Target
    primary_id_field = "target_id"
    _PROVIDER_ALIASES: ClassVar[Mapping[str, str]] = {"target_id": "target_chembl_id"}
    _UNKNOWN_PIPE_SENTINEL = "unknown"

    _XREF_DERIVED_COLUMNS: tuple[str, ...] = (
        "target_xref_iuphar_ids",
        "target_xref_pdb_ids",
        "target_xref_go_component",
        "target_xref_go_function",
        "target_xref_go_process",
        "target_xref_reactome_ids",
    )

    _XREF_SOURCE_TO_COLUMN: dict[str, str] = {
        "GUIDE_TO_PHARMACOLOGY": "target_xref_iuphar_ids",
        "GUIDETOPHARMACOLOGY": "target_xref_iuphar_ids",
        "IUPHAR": "target_xref_iuphar_ids",
        "GTOPDB": "target_xref_iuphar_ids",
        "PDB": "target_xref_pdb_ids",
        "PDBE": "target_xref_pdb_ids",
        "GOCOMPONENT": "target_xref_go_component",
        "GO_COMPONENT": "target_xref_go_component",
        "GOFUNCTION": "target_xref_go_function",
        "GO_FUNCTION": "target_xref_go_function",
        "GOPROCESS": "target_xref_go_process",
        "GO_PROCESS": "target_xref_go_process",
        "REACTOME": "target_xref_reactome_ids",
    }

    @staticmethod
    def _normalize_xref_source(value: object) -> str | None:
        """Normalize xref source label for canonical column lookup."""
        if not isinstance(value, str):
            return None

        normalized = value.strip()
        if not normalized:
            return None

        normalized = normalized.upper()
        for char in (" ", "-", "/", ":", "."):
            normalized = normalized.replace(char, "_")

        while "__" in normalized:
            normalized = normalized.replace("__", "_")

        return normalized.strip("_") or None

    @staticmethod
    def _clean_pipe_value(value: object) -> str | None:
        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        return cleaned.replace("|", r"\|")

    @staticmethod
    def _append_unique_xref_id(values: list[str], seen: set[str], value: str) -> None:
        """Append a normalized xref id preserving first-seen order."""
        if value in seen:
            return

        seen.add(value)
        values.append(value)

    def _collect_component_xrefs(
        self,
        components: list[JsonDict] | None,  # Any: untyped ChEMBL API JSON
    ) -> list[JsonDict]:
        """Collect raw target component xrefs without dropping payload."""
        xrefs = aggregate_nested_lists(
            components,
            "target_component_xrefs",
            deduplicate=False,
        )
        if not isinstance(xrefs, list):
            return []

        return [item for item in xrefs if isinstance(item, dict)]

    def _project_component_xrefs(
        self,
        xrefs: list[JsonDict],  # Any: raw xref entries
    ) -> dict[str, str]:
        """Project whitelisted xref sources into pipe-separated derived columns."""
        buckets: dict[str, list[str]] = {
            column: [] for column in self._XREF_DERIVED_COLUMNS
        }
        seen_by_column: dict[str, set[str]] = {
            column: set() for column in self._XREF_DERIVED_COLUMNS
        }

        for item in xrefs:
            if not isinstance(item, dict):
                continue

            xref_id = self._clean_pipe_value(item.get("xref_id"))
            source = self._normalize_xref_source(item.get("xref_src_db"))
            if not xref_id or not source:
                continue

            column = self._XREF_SOURCE_TO_COLUMN.get(source)
            if column is None:
                continue

            self._append_unique_xref_id(
                buckets[column],
                seen_by_column[column],
                xref_id,
            )

        return {
            column: self._pipe_or_unknown(values)
            for column, values in buckets.items()
        }

    def _prepare_record(
        self,
        record: BronzeRecord,
    ) -> BronzeRecord:
        """Normalize provider-native target identifiers at the ingestion boundary."""
        return normalize_provider_aliases(record, self._PROVIDER_ALIASES)

    def _flatten_target_components(
        self,
        components: list[JsonDict] | None,  # Any: untyped ChEMBL API JSON
    ) -> dict[str, list[Any] | None]:  # Any: heterogeneous component field values
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

    def _empty_component_result(
        self,
    ) -> dict[str, list[Any] | None]:  # Any: heterogeneous component field values
        """Return empty result dict for missing components."""
        return {
            "component_accessions": None,
            "component_ids": None,
            "component_types": None,
            "component_relationships": None,
            "component_descriptions": None,
        }

    def _extract_basic_component_fields(
        self,
        components: list[JsonDict],  # Any: untyped ChEMBL API JSON
    ) -> dict[str, list[Any] | None]:  # Any: heterogeneous component field values
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
        self,
        components: list[JsonDict] | None,  # Any: untyped ChEMBL API JSON
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

    @staticmethod
    def _append_unique_pipe_escaped(
        values: list[str],
        seen: set[str],
        raw_value: object,
    ) -> None:
        """Append a normalized, pipe-escaped value once while preserving first-seen order."""
        if raw_value is None:
            return

        normalized = str(raw_value).strip()
        if not normalized:
            return

        normalized = normalized.replace("|", "\\|")
        if normalized in seen:
            return

        seen.add(normalized)
        values.append(normalized)

    @staticmethod
    def _synonym_target_field(syn_type: object) -> str | None:
        """Resolve syn_type to the target synonym bucket name."""
        if not isinstance(syn_type, str):
            return None

        normalized_type = syn_type.strip().upper()
        if not normalized_type:
            return None

        if normalized_type == "UNIPROT":
            return "target_protein_synonyms"

        if normalized_type == "EC_NUMBER":
            return "target_ec_numbers"

        if normalized_type == "GENE_SYMBOL" or normalized_type.startswith("GENE_SYMBOL_"):
            return "target_gene_synonyms"

        return None

    @staticmethod
    def _iter_component_synonym_payloads(
        components: list[JsonDict],
    ):
        """Yield validated synonym payload dicts from target components."""
        for component in components:
            if not isinstance(component, Mapping):
                continue

            raw_synonyms = component.get("target_component_synonyms")
            if not isinstance(raw_synonyms, list):
                continue

            for synonym_payload in raw_synonyms:
                if isinstance(synonym_payload, Mapping):
                    yield synonym_payload

    @staticmethod
    def _project_single_synonym(
        payload: JsonDict,
        buckets: dict[str, list[str]],
        seen_by_field: dict[str, set[str]],
    ) -> None:
        """Apply one synonym payload into the proper accumulator."""
        field = TargetTransformer._synonym_target_field(payload.get("syn_type"))
        if not field:
            return

        TargetTransformer._append_unique_pipe_escaped(
            buckets[field],
            seen_by_field[field],
            payload.get("component_synonym"),
        )

    @classmethod
    def _empty_synonym_projection(cls) -> dict[str, str]:
        """Return projection output with unknown sentinels."""
        return {
            "target_protein_synonyms": cls._UNKNOWN_PIPE_SENTINEL,
            "target_gene_synonyms": cls._UNKNOWN_PIPE_SENTINEL,
            "target_ec_numbers": cls._UNKNOWN_PIPE_SENTINEL,
        }

    @classmethod
    def _pipe_or_unknown(cls, values: list[str]) -> str:
        """Join ordered values or emit the configured missing sentinel."""
        return "|".join(values) if values else cls._UNKNOWN_PIPE_SENTINEL

    def _project_component_synonyms(
        self,
        components: list[JsonDict] | None,  # Any: untyped ChEMBL API JSON
    ) -> dict[str, str]:
        """Project categorized synonym strings from raw target component payloads."""
        if not components or not isinstance(components, list):
            return self._empty_synonym_projection()

        buckets: dict[str, list[str]] = {
            "target_protein_synonyms": [],
            "target_gene_synonyms": [],
            "target_ec_numbers": [],
        }
        seen_by_field: dict[str, set[str]] = {
            "target_protein_synonyms": set(),
            "target_gene_synonyms": set(),
            "target_ec_numbers": set(),
        }

        for synonym_payload in self._iter_component_synonym_payloads(components):
            self._project_single_synonym(
                synonym_payload,
                buckets,
                seen_by_field,
            )

        return {
            "target_protein_synonyms": self._pipe_or_unknown(
                buckets["target_protein_synonyms"]
            ),
            "target_gene_synonyms": self._pipe_or_unknown(
                buckets["target_gene_synonyms"]
            ),
            "target_ec_numbers": self._pipe_or_unknown(
                buckets["target_ec_numbers"]
            ),
        }

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
        projected_synonyms = self._project_component_synonyms(target_components)
        component_xrefs = self._collect_component_xrefs(target_components)
        xref_projection = self._project_component_xrefs(component_xrefs)

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
            # Primary component ID (for target_component enricher join)
            "primary_component_id": primary_component_id,
            # Core metadata
            "pref_name": record.get("pref_name"),
            "target_type": record.get("target_type"),
            "organism": organism_name,
            # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
            "taxonomy_id": taxonomy_id,
            # Shared domain normalization owns deterministic cellularity derivation.
            "organism_class": record.get("organism_class"),
            "species_group_flag": record.get("species_group_flag"),
            "target_description": record.get("target_description")
            or record.get("description"),
            # Keep provider raw value here; shared bool coercion lives in the
            # domain normalization profile and must preserve null semantics.
            "downgraded": record.get("downgraded"),
            "pipeline_stages": self.serialize_json(record.get("pipeline_stages")),
            # Complex fields (JSON serialized)
            "target_components": self.serialize_json(target_components),
            "target_component_synonyms": self._aggregate_synonyms(target_components),
            **projected_synonyms,
            "cross_references": self.serialize_json(component_xrefs)
            if component_xrefs
            else None,
            "target_xref_iuphar_ids": xref_projection["target_xref_iuphar_ids"],
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
            "target_xref_reactome_ids": xref_projection["target_xref_reactome_ids"],
            # Flattened components
            **serialized_flattened_components,
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
