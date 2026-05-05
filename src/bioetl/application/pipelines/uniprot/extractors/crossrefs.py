"""Cross-reference data extraction facade for UniProt records."""

from __future__ import annotations

__all__ = ["CrossRefExtractor"]


from bioetl.application.pipelines.uniprot.extractors._crossref_common import (
    parse_properties,
)
from bioetl.application.pipelines.uniprot.extractors._crossref_go import (
    GO_ASPECTS,
    extract_go_by_aspect,
    extract_go_terms,
    parse_go_term_value,
)
from bioetl.application.pipelines.uniprot.extractors._crossref_structured import (
    build_interpro_entry,
    build_pdb_entry,
    build_pfam_entry,
    build_reactome_entry,
    extract_structured_xrefs,
    extract_xref_ids,
)
from bioetl.domain.types import JsonDict


class CrossRefExtractor:
    """Compatibility facade for UniProt cross-reference extraction."""

    GO_ASPECTS = GO_ASPECTS

    @classmethod
    def extract_go_terms(cls, xrefs: list[JsonDict] | None) -> str | None:
        """Extract GO terms with structured data.

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.

        Returns:
            JSON-serialized list of GO term dicts (id, term, aspect, evidence),
            or None if no GO cross-references are present.
        """
        return extract_go_terms(xrefs)

    @staticmethod
    def _parse_properties(properties: object) -> dict[str, str]:
        """Parse cross-reference properties into key-value dict."""
        return parse_properties(properties)

    @classmethod
    def _parse_go_term_value(
        cls,
        go_term_value: object,
    ) -> tuple[str | None, str | None]:
        """Parse GO term value ``F:ATP binding`` into aspect and term."""
        return parse_go_term_value(go_term_value)

    @staticmethod
    def extract_xref_ids(xrefs: list[JsonDict] | None, database: str) -> str | None:
        """Extract cross-reference IDs for the requested database.

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.
            database: Database name string to filter on.

        Returns:
            JSON-serialized list of ID strings for the database, or None if empty.
        """
        return extract_xref_ids(xrefs, database)

    @classmethod
    def _build_pdb_entry(
        cls,
        xref: JsonDict,  # Any: untyped API JSON record
    ) -> JsonDict | None:  # Any: untyped JSON fragment from UniProt API
        """Build a PDB entry from a cross-reference dict."""
        return build_pdb_entry(xref)

    @classmethod
    def extract_pdb_xrefs(cls, xrefs: list[JsonDict] | None) -> str | None:
        """Extract PDB cross-references with structural details.

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.

        Returns:
            JSON-serialized list of PDB entry dicts (id, method, resolution, chains),
            or None if no PDB cross-references are present.
        """
        return extract_structured_xrefs(
            xrefs,
            database="PDB",
            mapper=build_pdb_entry,
        )

    @classmethod
    def _build_interpro_entry(
        cls,
        xref: JsonDict,  # Any: untyped API JSON record
    ) -> JsonDict | None:  # Any: untyped JSON fragment from UniProt API
        """Build an InterPro entry from a cross-reference dict."""
        return build_interpro_entry(xref)

    @classmethod
    def extract_interpro_xrefs(cls, xrefs: list[JsonDict] | None) -> str | None:
        """Extract InterPro cross-references with domain family information.

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.

        Returns:
            JSON-serialized list of InterPro entry dicts (id, name),
            or None if no InterPro cross-references are present.
        """
        return extract_structured_xrefs(
            xrefs,
            database="InterPro",
            mapper=build_interpro_entry,
        )

    @classmethod
    def _build_pfam_entry(
        cls,
        xref: JsonDict,  # Any: untyped API JSON record
    ) -> JsonDict | None:  # Any: untyped JSON fragment from UniProt API
        """Build a Pfam entry from a cross-reference dict."""
        return build_pfam_entry(xref)

    @classmethod
    def extract_pfam_xrefs(cls, xrefs: list[JsonDict] | None) -> str | None:
        """Extract Pfam cross-references with protein family information.

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.

        Returns:
            JSON-serialized list of Pfam entry dicts (id, name, match_status),
            or None if no Pfam cross-references are present.
        """
        return extract_structured_xrefs(
            xrefs,
            database="Pfam",
            mapper=build_pfam_entry,
        )

    @classmethod
    def _build_reactome_entry(
        cls,
        xref: JsonDict,  # Any: untyped API JSON record
    ) -> JsonDict | None:  # Any: untyped JSON fragment from UniProt API
        """Build a Reactome entry from a cross-reference dict."""
        return build_reactome_entry(xref)

    @classmethod
    def extract_reactome_xrefs(cls, xrefs: list[JsonDict] | None) -> str | None:
        """Extract Reactome cross-references with pathway information.

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.

        Returns:
            JSON-serialized list of Reactome entry dicts (id, pathway_name),
            or None if no Reactome cross-references are present.
        """
        return extract_structured_xrefs(
            xrefs,
            database="Reactome",
            mapper=build_reactome_entry,
        )

    @classmethod
    def extract_go_by_aspect(
        cls,
        xrefs: list[JsonDict] | None,
        aspect: str,
    ) -> str | None:
        """Extract GO terms filtered by aspect.

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.
            aspect: GO aspect character to filter on ('F', 'P', or 'C').

        Returns:
            JSON-serialized list of GO term dicts for the given aspect, or None if
            no matching terms are found or aspect is invalid.
        """
        return extract_go_by_aspect(xrefs, aspect)

    @classmethod
    def extract_molecular_function(cls, xrefs: list[JsonDict] | None) -> str | None:
        """Extract GO terms for molecular function (F aspect).

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.

        Returns:
            JSON-serialized list of molecular function GO term dicts, or None if absent.
        """
        return extract_go_by_aspect(xrefs, "F")

    @classmethod
    def extract_cellular_component(cls, xrefs: list[JsonDict] | None) -> str | None:
        """Extract GO terms for cellular component (C aspect).

        Args:
            xrefs: List of UniProt cross-reference dicts from the API response, or None.

        Returns:
            JSON-serialized list of cellular component GO term dicts, or None if absent.
        """
        return extract_go_by_aspect(xrefs, "C")
