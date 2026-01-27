"""Cross-reference data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json


class CrossRefExtractor:
    """Extracts cross-reference data from UniProt records.

    Handles GO terms, DrugBank, ChEMBL, and other database references.
    """

    # Valid GO term aspects
    GO_ASPECTS = frozenset(("F", "P", "C"))

    @classmethod
    def extract_go_terms(cls, xrefs: Any) -> str | None:
        """Extract GO terms with structured data.

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of GO terms.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        go_terms: list[dict[str, Any]] = []
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if xref.get("database") != "GO":
                continue

            go_id = xref.get("id")
            if not go_id:
                continue

            props = cls._parse_properties(xref.get("properties", []))
            aspect, term = cls._parse_go_term_value(props.get("GoTerm", ""))

            go_terms.append(
                {
                    "id": go_id,
                    "term": term,
                    "aspect": aspect,
                    "evidence": props.get("GoEvidenceType"),
                }
            )

        return serialize_to_json(go_terms, ensure_ascii=False) if go_terms else None

    @staticmethod
    def _parse_properties(properties: list[Any]) -> dict[str, str]:
        """Parse cross-reference properties into key-value dict.

        Args:
            properties: List of property objects.

        Returns:
            Dict mapping property keys to values.
        """
        props: dict[str, str] = {}
        if not isinstance(properties, list):
            return props
        for prop in properties:
            if isinstance(prop, dict):
                key = prop.get("key")
                value = prop.get("value")
                if key and value:
                    props[key] = value
        return props

    @classmethod
    def _parse_go_term_value(cls, go_term_value: str) -> tuple[str | None, str | None]:
        """Parse GO term value "F:ATP binding" into aspect and term.

        Args:
            go_term_value: Raw GO term string like "F:ATP binding".

        Returns:
            Tuple of (aspect, term) where aspect is F/P/C or None.
        """
        if not go_term_value or ":" not in go_term_value:
            return None, None

        parts = go_term_value.split(":", 1)
        if len(parts) != 2:
            return None, None

        aspect_candidate = parts[0].strip()
        aspect = aspect_candidate if aspect_candidate in cls.GO_ASPECTS else None
        term = parts[1].strip() if parts[1].strip() else None
        return aspect, term

    @staticmethod
    def extract_xref_ids(xrefs: Any, database: str) -> str | None:
        """Extract cross-reference IDs for specific database.

        Args:
            xrefs: List of cross-reference objects.
            database: Database name (DrugBank, ChEMBL, GuidetoPHARMACOLOGY, PDB).

        Returns:
            JSON array of IDs or None.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        ids: list[str] = []
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if xref.get("database") != database:
                continue

            xref_id = xref.get("id")
            if xref_id:
                ids.append(str(xref_id))

        return serialize_to_json(ids, ensure_ascii=False) if ids else None

    @classmethod
    def _build_pdb_entry(cls, xref: dict[str, Any]) -> dict[str, Any] | None:
        """Build a PDB entry from a cross-reference dict."""
        pdb_id = xref.get("id")
        if not pdb_id:
            return None

        pdb_entry: dict[str, Any] = {"id": str(pdb_id)}
        props = cls._parse_properties(xref.get("properties", []))

        for key, field in [
            ("Method", "method"),
            ("Resolution", "resolution"),
            ("Chains", "chains"),
        ]:
            if props.get(key):
                pdb_entry[field] = props[key]

        return pdb_entry

    @classmethod
    def extract_pdb_xrefs(cls, xrefs: Any) -> str | None:
        """Extract PDB cross-references with structural details.

        PDB references include information about 3D structure availability,
        chains, and resolution which is valuable for structural biology.

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of PDB reference objects with id, method, resolution,
            and chains, or None.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        pdb_refs = [
            entry
            for xref in xrefs
            if isinstance(xref, dict) and xref.get("database") == "PDB"
            for entry in [cls._build_pdb_entry(xref)]
            if entry is not None
        ]

        return serialize_to_json(pdb_refs, ensure_ascii=False) if pdb_refs else None
