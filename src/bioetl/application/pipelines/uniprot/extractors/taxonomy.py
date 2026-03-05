"""Taxonomy lineage extraction for UniProt records."""

from __future__ import annotations

__all__ = ["TaxonomyExtractor"]


class TaxonomyExtractor:
    """Extracts taxonomy lineage components from UniProt organism data.

    UniProt API returns organism.lineage as a list of taxonomic ranks:
    Superkingdom -> Phylum -> Class -> Order -> Family -> Genus -> Species

    Index positions:
        - Superkingdom: index 0 (Bacteria, Archaea, Eukaryota, Viruses)
        - Phylum: index 1
        - Genus: second-to-last element (len-2)
    """

    # Known superkingdoms (domains of life)
    SUPERKINGDOMS = frozenset(("Bacteria", "Archaea", "Eukaryota", "Viruses"))

    @staticmethod
    def _as_lineage(lineage: object) -> list[object] | None:
        """Return lineage as list when valid, otherwise None.

        Args:
            lineage: Value to validate.

        Returns:
            Non-empty lineage list or None.
        """
        if not isinstance(lineage, list) or len(lineage) == 0:
            return None
        return lineage

    @staticmethod
    def extract_superkingdom(lineage: object) -> str | None:
        """Extract superkingdom (domain of life) from taxonomy lineage.

        Superkingdom is always at index 0 in the lineage list.

        Args:
            lineage: List of taxonomic ranks from UniProt API.

        Returns:
            Superkingdom name (Bacteria, Archaea, Eukaryota, Viruses) or None.
        """
        lineage_values = TaxonomyExtractor._as_lineage(lineage)
        if lineage_values is None:
            return None

        superkingdom = lineage_values[0]
        if not isinstance(superkingdom, str) or not superkingdom.strip():
            return None

        return superkingdom.strip()

    @staticmethod
    def extract_phylum(lineage: object) -> str | None:
        """Extract phylum from taxonomy lineage.

        Phylum is at index 1 in the lineage list.

        Args:
            lineage: List of taxonomic ranks from UniProt API.

        Returns:
            Phylum name or None if not available.
        """
        lineage_values = TaxonomyExtractor._as_lineage(lineage)
        if lineage_values is None:
            return None

        if len(lineage_values) < 2:
            return None

        phylum = lineage_values[1]
        if not isinstance(phylum, str) or not phylum.strip():
            return None

        return phylum.strip()

    @staticmethod
    def extract_genus(lineage: object) -> str | None:
        """Extract genus from taxonomy lineage.

        Genus is the second-to-last element in the lineage list (index len-2).
        Requires at least 2 elements to distinguish from species.

        Args:
            lineage: List of taxonomic ranks from UniProt API.

        Returns:
            Genus name or None if lineage is too short.
        """
        lineage_values = TaxonomyExtractor._as_lineage(lineage)
        if lineage_values is None:
            return None

        if len(lineage_values) < 2:
            return None

        genus = lineage_values[-2]
        if not isinstance(genus, str) or not genus.strip():
            return None

        return genus.strip()

    @classmethod
    def extract_all(cls, lineage: object) -> dict[str, str | None]:
        """Extract all taxonomy components at once.

        Args:
            lineage: List of taxonomic ranks from UniProt API.

        Returns:
            Dict with keys 'superkingdom', 'phylum', 'genus' and their values.
        """
        return {
            "superkingdom": cls.extract_superkingdom(lineage),
            "phylum": cls.extract_phylum(lineage),
            "genus": cls.extract_genus(lineage),
        }
