"""Gene data extraction for UniProt records."""

from __future__ import annotations

__all__ = ["GeneExtractor"]


from bioetl.domain.serialization import serialize_to_json


class GeneExtractor:
    """Extracts gene-related data from UniProt records."""

    @staticmethod
    def _iter_gene_dicts(genes: object) -> list[dict[str, object]]:
        """Return only mapping gene entries from a raw genes payload."""
        if not isinstance(genes, list):
            return []
        return [gene for gene in genes if isinstance(gene, dict)]

    @staticmethod
    def _collect_named_values(
        genes: object,
        field_name: str,
    ) -> list[str]:
        """Collect ``value`` strings from nested UniProt gene sub-lists."""
        values: list[str] = []
        for gene in GeneExtractor._iter_gene_dicts(genes):
            nested_values = gene.get(field_name, [])
            if not isinstance(nested_values, list):
                continue
            for nested in nested_values:
                if not isinstance(nested, dict):
                    continue
                value = nested.get("value")
                if value:
                    values.append(str(value))
        return values

    @staticmethod
    def extract_gene_names(genes: object) -> list[str]:
        """Extract gene names from genes list.

        Args:
            genes: List of gene objects.

        Returns:
            List of gene name strings.
        """
        names: list[str] = []
        for gene in GeneExtractor._iter_gene_dicts(genes):
            gene_name = gene.get("geneName", {})
            if isinstance(gene_name, dict):
                name = gene_name.get("value")
                if name:
                    names.append(str(name))
        return names

    @staticmethod
    def extract_primary_gene(genes: object) -> str | None:
        """Extract primary gene name.

        Args:
            genes: List of gene objects.

        Returns:
            Primary gene name or None.
        """
        for gene in GeneExtractor._iter_gene_dicts(genes):
            gene_name = gene.get("geneName", {})
            if not isinstance(gene_name, dict):
                continue
            value = gene_name.get("value")
            if value:
                return str(value)
        return None

    @staticmethod
    def extract_gene_synonyms(genes: object) -> str | None:
        """Extract gene synonyms.

        Args:
            genes: List of gene objects.

        Returns:
            JSON array of gene synonyms or None.
        """
        all_synonyms = GeneExtractor._collect_named_values(genes, "synonyms")
        return (
            serialize_to_json(all_synonyms, ensure_ascii=False)
            if all_synonyms
            else None
        )

    @staticmethod
    def extract_gene_orf_names(genes: object) -> str | None:
        """Extract ORF names from genes.

        Args:
            genes: List of gene objects.

        Returns:
            JSON array of ORF names or None.
        """
        all_orf = GeneExtractor._collect_named_values(genes, "orfNames")
        return serialize_to_json(all_orf, ensure_ascii=False) if all_orf else None
