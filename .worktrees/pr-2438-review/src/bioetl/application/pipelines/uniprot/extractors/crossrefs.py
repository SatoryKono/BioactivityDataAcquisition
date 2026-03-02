"""Cross-reference data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.domain.serialization import serialize_to_json

# Any: UniProt REST API returns untyped JSON; dict values are heterogeneous
# (str | int | float | list | dict | None). All public methods accept
# ``object`` for the xrefs parameter and narrow via isinstance.


class CrossRefExtractor:
    """Extracts cross-reference data from UniProt records.

    Handles GO terms, DrugBank, ChEMBL, and other database references.
    """

    # Valid GO term aspects
    GO_ASPECTS = frozenset(("F", "P", "C"))

    @classmethod
    def extract_go_terms(cls, xrefs: Any) -> str | None:  # Any: untyped API JSON
        """Extract GO terms with structured data.

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of GO terms.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        go_terms: list[dict[str, Any]] = []  # Any: JSON values
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
    def _parse_properties(properties: list[Any]) -> dict[str, str]:  # Any: untyped JSON
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
    def extract_xref_ids(xrefs: Any, database: str) -> str | None:  # Any: untyped JSON
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

        pdb_entry: dict[str, Any] = {"id": str(pdb_id)}  # Any: JSON values
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
    def extract_pdb_xrefs(cls, xrefs: Any) -> str | None:  # Any: untyped API JSON
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

    @classmethod
    def _build_interpro_entry(cls, xref: dict[str, Any]) -> dict[str, Any] | None:
        """Build an InterPro entry from a cross-reference dict."""
        interpro_id = xref.get("id")
        if not interpro_id:
            return None

        interpro_entry: dict[str, Any] = {"id": str(interpro_id)}  # Any: JSON values
        props = cls._parse_properties(xref.get("properties", []))

        if props.get("EntryName"):
            interpro_entry["name"] = props["EntryName"]

        return interpro_entry

    @classmethod
    def extract_interpro_xrefs(cls, xrefs: Any) -> str | None:  # Any: untyped API JSON
        """Extract InterPro cross-references with domain family information.

        InterPro provides protein domain and family classification based on
        predictive models. Valuable for functional annotation.

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of InterPro reference objects with id and name, or None.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        interpro_refs = [
            entry
            for xref in xrefs
            if isinstance(xref, dict) and xref.get("database") == "InterPro"
            for entry in [cls._build_interpro_entry(xref)]
            if entry is not None
        ]

        return (
            serialize_to_json(interpro_refs, ensure_ascii=False)
            if interpro_refs
            else None
        )

    @classmethod
    def _build_pfam_entry(cls, xref: dict[str, Any]) -> dict[str, Any] | None:
        """Build a Pfam entry from a cross-reference dict."""
        pfam_id = xref.get("id")
        if not pfam_id:
            return None

        pfam_entry: dict[str, Any] = {"id": str(pfam_id)}  # Any: JSON values
        props = cls._parse_properties(xref.get("properties", []))

        if props.get("EntryName"):
            pfam_entry["name"] = props["EntryName"]
        if props.get("MatchStatus"):
            pfam_entry["match_status"] = props["MatchStatus"]

        return pfam_entry

    @classmethod
    def extract_pfam_xrefs(cls, xrefs: Any) -> str | None:  # Any: untyped API JSON
        """Extract Pfam cross-references with protein family information.

        Pfam is a database of protein families represented by multiple
        sequence alignments and hidden Markov models.

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of Pfam reference objects with id, name, and match_status,
            or None.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        pfam_refs = [
            entry
            for xref in xrefs
            if isinstance(xref, dict) and xref.get("database") == "Pfam"
            for entry in [cls._build_pfam_entry(xref)]
            if entry is not None
        ]

        return serialize_to_json(pfam_refs, ensure_ascii=False) if pfam_refs else None

    @classmethod
    def _build_reactome_entry(cls, xref: dict[str, Any]) -> dict[str, Any] | None:
        """Build a Reactome entry from a cross-reference dict."""
        reactome_id = xref.get("id")
        if not reactome_id:
            return None

        reactome_entry: dict[str, Any] = {"id": str(reactome_id)}  # Any: JSON values
        props = cls._parse_properties(xref.get("properties", []))

        if props.get("PathwayName"):
            reactome_entry["pathway_name"] = props["PathwayName"]

        return reactome_entry

    @classmethod
    def extract_reactome_xrefs(cls, xrefs: Any) -> str | None:  # Any: untyped API JSON
        """Extract Reactome cross-references with pathway information.

        Reactome is a free, open-source, curated and peer-reviewed pathway
        database. Valuable for understanding protein involvement in pathways.

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of Reactome reference objects with id and pathway_name,
            or None.
        """
        if not xrefs or not isinstance(xrefs, list):
            return None

        reactome_refs = [
            entry
            for xref in xrefs
            if isinstance(xref, dict) and xref.get("database") == "Reactome"
            for entry in [cls._build_reactome_entry(xref)]
            if entry is not None
        ]

        return (
            serialize_to_json(reactome_refs, ensure_ascii=False)
            if reactome_refs
            else None
        )

    @classmethod
    def extract_go_by_aspect(
        cls, xrefs: Any, aspect: str
    ) -> str | None:  # Any: untyped UniProt JSON
        """Extract GO terms filtered by aspect.

        Args:
            xrefs: List of cross-reference objects.
            aspect: GO aspect to filter by (F, P, or C).

        Returns:
            JSON array of GO terms with matching aspect, or None.
        """
        if aspect not in cls.GO_ASPECTS:
            return None

        if not xrefs or not isinstance(xrefs, list):
            return None

        go_terms: list[dict[str, Any]] = []  # Any: JSON values
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if xref.get("database") != "GO":
                continue

            go_id = xref.get("id")
            if not go_id:
                continue

            props = cls._parse_properties(xref.get("properties", []))
            parsed_aspect, term = cls._parse_go_term_value(props.get("GoTerm", ""))

            if parsed_aspect != aspect:
                continue

            go_terms.append(
                {
                    "id": go_id,
                    "term": term,
                    "evidence": props.get("GoEvidenceType"),
                }
            )

        return serialize_to_json(go_terms, ensure_ascii=False) if go_terms else None

    @classmethod
    def extract_molecular_function(cls, xrefs: Any) -> str | None:  # Any: untyped JSON
        """Extract GO terms for molecular function (F aspect).

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of molecular function GO terms, or None.
        """
        return cls.extract_go_by_aspect(xrefs, "F")

    @classmethod
    def extract_cellular_component(cls, xrefs: Any) -> str | None:  # Any: untyped JSON
        """Extract GO terms for cellular component (C aspect).

        Args:
            xrefs: List of cross-reference objects.

        Returns:
            JSON array of cellular component GO terms, or None.
        """
        return cls.extract_go_by_aspect(xrefs, "C")
