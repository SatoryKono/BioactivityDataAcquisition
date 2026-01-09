"""Gene data extraction for UniProt records."""

from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.uniprot.extractors.utils import ExtractorUtils


class GeneExtractor:
    """Extracts gene-related data from UniProt records."""

    @staticmethod
    def extract_gene_names(genes: Any) -> list[str]:
        """Extract gene names from genes list.

        Args:
            genes: List of gene objects.

        Returns:
            List of gene name strings.
        """
        if not genes or not isinstance(genes, list):
            return []

        names: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            gene_name = gene.get("geneName", {})
            if isinstance(gene_name, dict):
                name = gene_name.get("value")
                if name:
                    names.append(str(name))
        return names

    @staticmethod
    def extract_primary_gene(genes: Any) -> str | None:
        """Extract primary gene name.

        Args:
            genes: List of gene objects.

        Returns:
            Primary gene name or None.
        """
        if not genes or not isinstance(genes, list):
            return None

        for gene in genes:
            if isinstance(gene, dict):
                gene_name = gene.get("geneName", {})
                if isinstance(gene_name, dict):
                    value = gene_name.get("value")
                    if value:
                        return str(value)
        return None

    @staticmethod
    def extract_gene_synonyms(genes: Any) -> str | None:
        """Extract gene synonyms.

        Args:
            genes: List of gene objects.

        Returns:
            JSON array of gene synonyms or None.
        """
        if not genes or not isinstance(genes, list):
            return None

        all_synonyms: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            synonyms = gene.get("synonyms", [])
            if isinstance(synonyms, list):
                for syn in synonyms:
                    if isinstance(syn, dict):
                        value = syn.get("value")
                        if value:
                            all_synonyms.append(str(value))
        return ExtractorUtils.to_json(all_synonyms)

    @staticmethod
    def extract_gene_orf_names(genes: Any) -> str | None:
        """Extract ORF names from genes.

        Args:
            genes: List of gene objects.

        Returns:
            JSON array of ORF names or None.
        """
        if not genes or not isinstance(genes, list):
            return None

        all_orf: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            orf_names = gene.get("orfNames", [])
            if isinstance(orf_names, list):
                for orf in orf_names:
                    if isinstance(orf, dict):
                        value = orf.get("value")
                        if value:
                            all_orf.append(str(value))
        return ExtractorUtils.to_json(all_orf)
