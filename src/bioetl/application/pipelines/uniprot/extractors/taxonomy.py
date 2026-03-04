"""Taxonomy lineage extraction for UniProt records."""

from __future__ import annotations

__all__ = ["TaxonomyExtractor"]


from typing import Any

# Any: UniProt API returns untyped JSON; lineage parameter is narrowed
# via isinstance checks inside each method.


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
    def _is_valid_lineage(lineage: Any) -> bool:  # Any: untyped API JSON
        """Check if lineage is a valid non-empty list.

        Args:
            lineage: Value to validate.

        Returns:
            True if lineage is a non-empty list, False otherwise.
        """
        return isinstance(lineage, list) and len(lineage) > 0

    @staticmethod
    def extract_superkingdom(lineage: Any) -> str | None:  # Any: untyped API JSON
        """Extract superkingdom (domain of life) from taxonomy lineage.

        Superkingdom is always at index 0 in the lineage list.

        Args:
            lineage: List of taxonomic ranks from UniProt API.

        Returns:
            Superkingdom name (Bacteria, Archaea, Eukaryota, Viruses) or None.
        """
        if not TaxonomyExtractor._is_valid_lineage(lineage):
            return None

        superkingdom = lineage[0]
        if not isinstance(superkingdom, str) or not superkingdom.strip():
            return None

        return superkingdom.strip()

    @staticmethod
    def extract_phylum(lineage: Any) -> str | None:  # Any: untyped API JSON
        """Extract phylum from taxonomy lineage.

        Phylum is at index 1 in the lineage list.

        Args:
            lineage: List of taxonomic ranks from UniProt API.

        Returns:
            Phylum name or None if not available.
        """
        if not TaxonomyExtractor._is_valid_lineage(lineage):
            return None

        if len(lineage) < 2:
            return None

        phylum = lineage[1]
        if not isinstance(phylum, str) or not phylum.strip():
            return None

        return phylum.strip()

    @staticmethod
    def extract_genus(lineage: Any) -> str | None:  # Any: untyped API JSON
        """Extract genus from taxonomy lineage.

        Genus is the second-to-last element in the lineage list (index len-2).
        Requires at least 2 elements to distinguish from species.

        Args:
            lineage: List of taxonomic ranks from UniProt API.

        Returns:
            Genus name or None if lineage is too short.
        """
        if not TaxonomyExtractor._is_valid_lineage(lineage):
            return None

        if len(lineage) < 2:
            return None

        genus = lineage[-2]
        if not isinstance(genus, str) or not genus.strip():
            return None

        return genus.strip()

    @classmethod
    def extract_all(cls, lineage: Any) -> dict[str, str | None]:  # Any: untyped JSON
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
