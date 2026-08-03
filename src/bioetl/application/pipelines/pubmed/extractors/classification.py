"""Classification extraction from PubMed XML elements.

Handles extraction of keywords, MeSH terms, and publication types.
"""

from __future__ import annotations

__all__ = ["ClassificationExtractor", "NormalizedClassification", "RawClassification"]


from typing import TypedDict, cast
from xml.etree.ElementTree import Element  # nosec B405

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.domain.types import JsonDict


class RawClassification(TypedDict):
    """Raw classification data before normalization."""

    keywords: list[str | None]
    mesh_terms: list[str | None]
    publication_types: list[str | None]


class NormalizedClassification(TypedDict):
    """Normalized classification data."""

    keywords: list[str]
    mesh_terms: list[str]
    publication_types: list[str]


class ClassificationExtractor(BaseFieldExtractor):
    """Extractor for classification data from PubMed XML.

    Handles:
    - Keywords from KeywordList
    - MeSH terms from MeshHeadingList
    - Publication types from PublicationTypeList
    """

    def extract(self, element: Element | None) -> RawClassification | None:
        """Extract raw classification data from XML.

        Args:
            element: Root PubmedArticle element.

        Returns:
            Dict with raw keywords, mesh_terms, and publication_types.
        """
        if element is None:
            return None

        medline = element.find(".//MedlineCitation")
        article = element.find(".//Article")

        return RawClassification(
            keywords=self._extract_keywords_raw(medline),
            mesh_terms=self._extract_mesh_raw(medline),
            publication_types=self._extract_pub_types_raw(article),
        )

    def normalize(self, raw_value: object) -> NormalizedClassification:
        """Normalize classification data.

        Args:
            raw_value: Raw classification dict.

        Returns:
            Normalized classification dict with cleaned lists.
        """
        raw_classification = cast("RawClassification", raw_value)
        return NormalizedClassification(
            keywords=self._normalize_list(raw_classification["keywords"]),
            mesh_terms=self._normalize_list(raw_classification["mesh_terms"]),
            publication_types=self._normalize_list(
                raw_classification["publication_types"]
            ),
        )

    def _extract_keywords_raw(self, medline: Element | None) -> list[str | None]:
        """Extract raw keyword texts."""
        if medline is None:
            return []
        keyword_list = medline.find(".//KeywordList")
        if keyword_list is None:
            return []
        return [kw.text for kw in keyword_list.findall("Keyword")]

    def _extract_mesh_raw(self, medline: Element | None) -> list[str | None]:
        """Extract raw MeSH descriptor texts."""
        if medline is None:
            return []
        mesh_list = medline.find(".//MeshHeadingList")
        if mesh_list is None:
            return []
        texts = []
        for heading in mesh_list.findall("MeshHeading"):
            descriptor = heading.find("DescriptorName")
            if descriptor is not None:
                texts.append(descriptor.text)
        return texts

    def _extract_pub_types_raw(self, article: Element | None) -> list[str | None]:
        """Extract raw publication type texts."""
        if article is None:
            return []
        type_list = article.find(".//PublicationTypeList")
        if type_list is None:
            return []
        return [pt.text for pt in type_list.findall("PublicationType")]

    def _normalize_list(self, raw_list: list[str | None]) -> list[str]:
        """Normalize a list by stripping and filtering empty values."""
        return [text.strip() for text in raw_list if text and text.strip()]

    @classmethod
    def parse_keywords(cls, medline_citation: Element | None) -> list[str]:
        """Extract keywords from KeywordList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of keyword strings.
        """
        extractor = cls()
        raw = extractor._extract_keywords_raw(medline_citation)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_mesh_terms(cls, medline_citation: Element | None) -> list[str]:
        """Extract MeSH terms from MeshHeadingList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of MeSH descriptor names.
        """
        extractor = cls()
        raw = extractor._extract_mesh_raw(medline_citation)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_publication_types(cls, article_node: Element) -> list[str]:
        """Extract publication types from PublicationTypeList.

        Args:
            article_node: The Article element.

        Returns:
            List of publication type strings.
        """
        extractor = cls()
        raw = extractor._extract_pub_types_raw(article_node)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_chemicals(cls, medline_citation: Element | None) -> list[str]:
        """Extract chemical substance names from ChemicalList.

        Extracts NameOfSubstance text from each Chemical element.

        XML structure:
            <ChemicalList>
              <Chemical>
                <RegistryNumber>0</RegistryNumber>
                <NameOfSubstance UI="D000123">Aspirin</NameOfSubstance>
              </Chemical>
            </ChemicalList>

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of chemical substance names.
        """
        if medline_citation is None:
            return []
        chemical_list = medline_citation.find(".//ChemicalList")
        if chemical_list is None:
            return []
        raw: list[str | None] = []
        for chem in chemical_list.findall("Chemical"):
            name_elem = chem.find("NameOfSubstance")
            if name_elem is not None:
                raw.append(name_elem.text)
        return cls()._normalize_list(raw)

    @classmethod
    def parse_gene_symbols(cls, medline_citation: Element | None) -> list[str]:
        """Extract gene symbols from GeneSymbolList.

        XML structure:
            <GeneSymbolList>
              <GeneSymbol>TP53</GeneSymbol>
              <GeneSymbol>BRCA1</GeneSymbol>
            </GeneSymbolList>

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of gene symbols.
        """
        if medline_citation is None:
            return []
        gene_list = medline_citation.find(".//GeneSymbolList")
        if gene_list is None:
            return []
        raw = [gs.text for gs in gene_list.findall("GeneSymbol")]
        return cls()._normalize_list(raw)

    @classmethod
    def parse_databanks(
        cls, medline_citation: Element | None
    ) -> list[JsonDict]:  # Any: untyped API JSON record
        """Extract data bank references from DataBankList.

        Returns structured data with bank name and accession numbers.

        XML structure:
            <DataBankList>
              <DataBank>
                <DataBankName>ClinicalTrials.gov</DataBankName>
                <AccessionNumberList>
                  <AccessionNumber>NCT123456</AccessionNumber>
                </AccessionNumberList>
              </DataBank>
            </DataBankList>

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of dicts with 'databank_name' and 'accession_numbers' keys.
        """
        if medline_citation is None:
            return []
        databank_list = medline_citation.find(".//DataBankList")
        if databank_list is None:
            return []

        result: list[JsonDict] = []  # Any: untyped API JSON record
        for databank in databank_list.findall("DataBank"):
            name_elem = databank.find("DataBankName")
            if name_elem is None or not name_elem.text:
                continue

            accession_list = databank.find("AccessionNumberList")
            accessions: list[str] = []
            if accession_list is not None:
                accessions = [
                    acc.text.strip()
                    for acc in accession_list.findall("AccessionNumber")
                    if acc.text and acc.text.strip()
                ]

            result.append(
                {
                    "databank_name": name_elem.text.strip(),
                    "accession_numbers": accessions,
                }
            )

        return result
