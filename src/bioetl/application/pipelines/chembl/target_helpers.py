"""Helper classes for TargetTransformer refactoring."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, ClassVar

from bioetl.application.core.dict_transformers import aggregate_nested_lists
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import Callable


class XrefHelper:
    """Helper for cross-reference operations in target transformation."""

    _XREF_DERIVED_COLUMNS: ClassVar[tuple[str, ...]] = (
        "target_xref_pdb_ids",
        "target_xref_go_component",
        "target_xref_go_function",
        "target_xref_go_process",
        "target_xref_hgnc_ids",
        "target_xref_reactome_ids",
        "target_xref_uniprot_ids",
    )

    _XREF_SOURCE_TO_PROJECTION: ClassVar[dict[str, tuple[str, str]]] = {
        "PDB": ("target_xref_pdb_ids", "xref_id"),
        "PDBE": ("target_xref_pdb_ids", "xref_id"),
        "GOCOMPONENT": ("target_xref_go_component", "xref_name"),
        "GO_COMPONENT": ("target_xref_go_component", "xref_name"),
        "GOFUNCTION": ("target_xref_go_function", "xref_name"),
        "GO_FUNCTION": ("target_xref_go_function", "xref_name"),
        "GOPROCESS": ("target_xref_go_process", "xref_name"),
        "GO_PROCESS": ("target_xref_go_process", "xref_name"),
        "HGNC": ("target_xref_hgnc_ids", "xref_id"),
        "UNIPROT": ("target_xref_uniprot_ids", "xref_id"),
        "REACTOME": ("target_xref_reactome_ids", "xref_id"),
    }

    _UNKNOWN_PIPE_SENTINEL: ClassVar[str] = "unknown"

    @staticmethod
    def normalize_xref_source(value: object) -> str | None:
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
    def clean_pipe_value(value: object) -> str | None:
        """Clean a value for pipe-separated storage."""
        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        if not cleaned:
            return None

        return cleaned.replace("|", r"\|")

    @staticmethod
    def append_unique_pipe_value(values: list[str], seen: set[str], value: str) -> None:
        """Append a normalized pipe-safe value preserving first-seen order."""
        if value in seen:
            return

        seen.add(value)
        values.append(value)

    @staticmethod
    def collect_component_xrefs(
        components: list[JsonDict] | None,
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

    @classmethod
    def project_component_xrefs(cls, xrefs: list[JsonDict]) -> dict[str, str]:
        """Project whitelisted xref sources into pipe-separated derived columns."""
        buckets: dict[str, list[str]] = {
            column: [] for column in cls._XREF_DERIVED_COLUMNS
        }
        seen_by_column: dict[str, set[str]] = {
            column: set() for column in cls._XREF_DERIVED_COLUMNS
        }

        for item in xrefs:
            if not isinstance(item, dict):
                continue

            source = cls.normalize_xref_source(item.get("xref_src_db"))
            if not source:
                continue

            projection = cls._XREF_SOURCE_TO_PROJECTION.get(source)
            if projection is None:
                continue

            column, value_field = projection
            value = cls.clean_pipe_value(item.get(value_field))
            if not value:
                continue

            cls.append_unique_pipe_value(
                buckets[column],
                seen_by_column[column],
                value,
            )

        return {
            column: cls.pipe_or_unknown(values)
            for column, values in buckets.items()
        }

    @classmethod
    def pipe_or_unknown(cls, values: list[str]) -> str:
        """Join ordered values or emit the configured missing sentinel."""
        return "|".join(values) if values else cls._UNKNOWN_PIPE_SENTINEL


class SynonymHelper:
    """Helper for synonym operations in target transformation."""

    _UNKNOWN_PIPE_SENTINEL: ClassVar[str] = "unknown"

    @staticmethod
    def append_unique_pipe_escaped(
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
    def synonym_target_field(syn_type: object) -> str | None:
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
    def iter_component_synonym_payloads(
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

    @classmethod
    def project_single_synonym(
        cls,
        payload: JsonDict,
        buckets: dict[str, list[str]],
        seen_by_field: dict[str, set[str]],
    ) -> None:
        """Apply one synonym payload into the proper accumulator."""
        field = cls.synonym_target_field(payload.get("syn_type"))
        if not field:
            return

        cls.append_unique_pipe_escaped(
            buckets[field],
            seen_by_field[field],
            payload.get("component_synonym"),
        )

    @classmethod
    def empty_synonym_projection(cls) -> dict[str, str]:
        """Return projection output with unknown sentinels."""
        return {
            "target_protein_synonyms": cls._UNKNOWN_PIPE_SENTINEL,
            "target_gene_synonyms": cls._UNKNOWN_PIPE_SENTINEL,
            "target_ec_numbers": cls._UNKNOWN_PIPE_SENTINEL,
        }

    @classmethod
    def pipe_or_unknown(cls, values: list[str]) -> str:
        """Join ordered values or emit the configured missing sentinel."""
        return "|".join(values) if values else cls._UNKNOWN_PIPE_SENTINEL

    @classmethod
    def project_component_synonyms(
        cls,
        components: list[JsonDict] | None,
    ) -> dict[str, str]:
        """Project categorized synonym strings from raw target component payloads."""
        if not components or not isinstance(components, list):
            return cls.empty_synonym_projection()

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

        for synonym_payload in cls.iter_component_synonym_payloads(components):
            cls.project_single_synonym(
                synonym_payload,
                buckets,
                seen_by_field,
            )

        return {
            "target_protein_synonyms": cls.pipe_or_unknown(
                buckets["target_protein_synonyms"]
            ),
            "target_gene_synonyms": cls.pipe_or_unknown(
                buckets["target_gene_synonyms"]
            ),
            "target_ec_numbers": cls.pipe_or_unknown(
                buckets["target_ec_numbers"]
            ),
        }


class ComponentHelper:
    """Helper for component flattening operations in target transformation."""

    @staticmethod
    def flatten_target_components(
        components: list[JsonDict] | None,
        extract_list_field: Callable,
    ) -> dict[str, list | None]:
        """Flatten target components into aggregated lists.

        Args:
            components: List of component dicts from ChEMBL API.
            extract_list_field: Function to extract list fields from components.

        Returns:
            Dict with aggregated lists for accessions, IDs, types, relationships,
            and descriptions.

        Note:
            protein_classifications are projected separately because enriched
            target payloads may carry component classification sidecars.

        """
        if not components or not isinstance(components, list):
            return ComponentHelper.empty_component_result()

        return ComponentHelper.extract_basic_component_fields(
            components,
            extract_list_field,
        )

    @staticmethod
    def empty_component_result() -> dict[str, list | None]:
        """Return empty result dict for missing components."""
        return {
            "component_accessions": None,
            "component_ids": None,
            "component_types": None,
            "component_relationships": None,
            "component_descriptions": None,
        }

    @staticmethod
    def extract_basic_component_fields(
        components: list[JsonDict],
        extract_list_field: Callable,
    ) -> dict[str, list | None]:
        """Extract basic fields from component list via dict_transformers."""
        from bioetl.domain.transformations import safe_int

        return {
            "component_accessions": extract_list_field(components, "accession"),
            "component_ids": extract_list_field(components, "component_id", safe_int),
            "component_types": extract_list_field(components, "component_type"),
            "component_relationships": extract_list_field(components, "relationship"),
            "component_descriptions": extract_list_field(
                components, "component_description"
            ),
        }
