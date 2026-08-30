"""Parsing helpers for UniProt ID mapping responses."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Protocol, cast

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.common.response_shapes import extract_response_items
from bioetl.infrastructure.adapters.uniprot._idmapping_url_policy import (
    trusted_idmapping_url,
)


class IDMappingParserDependencies(Protocol):
    """Host attributes required by ID-mapping response parsing."""

    base_url: str


class IDMappingParserMixin:
    """Pure parsing and selection logic for ID mapping payloads."""

    def _append_mapping_results(
        self,
        data: object,
        entries_by_id: dict[str, list[JsonDict]],
    ) -> bool:
        """Append valid mapping entries and report whether the payload is usable."""
        if not isinstance(data, dict):
            return False
        for mapping in extract_response_items(data, "results"):
            if not isinstance(mapping, dict):
                continue
            from_id, entry_data = self._parse_mapping_entry(mapping)
            if from_id in entries_by_id and entry_data:
                entries_by_id[from_id].append(entry_data)
        return True

    @staticmethod
    def _select_primary_entry(
        entries: list[JsonDict],  # Any: untyped API JSON
    ) -> JsonDict | None:  # Any: untyped API JSON
        """Select primary entry from list, handling multiple mappings.

        Returns:
            Best-ranked entry dict if found, None if entries is empty.
        """
        if not entries:
            return None
        if len(entries) == 1:
            return entries[0]

        sorted_entries = sorted(
            entries,
            key=lambda entry: (
                -int(entry.get("reviewed") or False),
                -int(entry.get("annotation_score") or 0),
            ),
        )
        primary = dict(sorted_entries[0])
        all_accessions = [entry["uniprot_accession"] for entry in sorted_entries]
        primary["all_mappings"] = json.dumps(all_accessions)
        return primary

    def _get_next_page_url(self, headers: Mapping[str, str]) -> str | None:
        """Extract next page URL from Link header.

        Returns:
            Next page URL string if a rel="next" link is present, None otherwise.
        """
        link_header = headers.get("Link", headers.get("link", ""))
        if not link_header:
            return None

        match = re.search(r'<([^>]+)>;\s*rel="next"', str(link_header))
        if not match:
            return None
        base_url = cast("IDMappingParserDependencies", self).base_url
        return trusted_idmapping_url(base_url, match.group(1))

    @staticmethod
    def _extract_organism_info(
        organism: object,
    ) -> tuple[str | None, str | None, int | None]:
        """Extract organism metadata from entry.

        Returns:
            Tuple of (scientific name, common name, taxonomy ID) or all-None if invalid.
        """
        if not isinstance(organism, dict):
            return None, None, None
        return (
            organism.get("scientificName"),
            organism.get("commonName"),
            organism.get("taxonId"),
        )

    @staticmethod
    def _extract_protein_name(protein_desc: object) -> str | None:
        """Extract recommended protein name from description.

        Returns:
            Recommended full protein name string if found, None otherwise.
        """
        if not isinstance(protein_desc, dict):
            return None
        recommended = protein_desc.get("recommendedName", {})
        if not isinstance(recommended, dict):
            return None
        full_name = recommended.get("fullName", {})
        if not isinstance(full_name, dict):
            return None
        return full_name.get("value")

    @staticmethod
    def _extract_gene_primary(genes: object) -> str | None:
        """Extract primary gene name from genes list.

        Returns:
            Primary gene name string if found, None otherwise.
        """
        if not isinstance(genes, list) or not genes:
            return None
        first_gene = genes[0]
        if not isinstance(first_gene, dict):
            return None
        gene_name_obj = first_gene.get("geneName", {})
        if not isinstance(gene_name_obj, dict):
            return None
        return gene_name_obj.get("value")

    @staticmethod
    def _extract_sequence_info(
        sequence: object,
    ) -> tuple[int | None, int | None]:
        """Extract sequence length and mass from entry.

        Returns:
            Tuple of (sequence length, molecular weight) or (None, None) if invalid.
        """
        if not isinstance(sequence, dict):
            return None, None
        return sequence.get("length"), sequence.get("molWeight")

    @classmethod
    def _parse_mapping_entry(
        cls,
        mapping: JsonDict,  # Any: untyped API JSON
    ) -> tuple[str | None, JsonDict | None]:  # Any: untyped API JSON
        """Parse a single mapping entry from API response.

        Returns:
            Tuple of (source ID string, mapped entry dict) or (None, None) if unparseable.
        """
        from_id = mapping.get("from")
        to_entry = mapping.get("to", {})

        if isinstance(to_entry, str):
            return from_id, {"uniprot_accession": to_entry}
        if not isinstance(to_entry, dict):
            return from_id, None

        accession = to_entry.get("primaryAccession")
        if not accession:
            return from_id, None

        org_sci, org_common, tax_id = cls._extract_organism_info(
            to_entry.get("organism")
        )
        protein_name = cls._extract_protein_name(to_entry.get("proteinDescription"))
        gene_primary = cls._extract_gene_primary(to_entry.get("genes"))
        seq_len, seq_mass = cls._extract_sequence_info(to_entry.get("sequence"))

        entry_type = to_entry.get("entryType", "")
        reviewed = "Swiss-Prot" in entry_type if entry_type else None

        return from_id, {
            "uniprot_accession": str(accession),
            "uniprot_entry_name": to_entry.get("uniProtkbId"),
            "organism_scientific": org_sci,
            "organism_common": org_common,
            "taxonomy_id": tax_id,
            "protein_name": protein_name,
            "gene_primary": gene_primary,
            "sequence_length": seq_len,
            "sequence_mass": seq_mass,
            "reviewed": reviewed,
            "annotation_score": to_entry.get("annotationScore"),
        }
