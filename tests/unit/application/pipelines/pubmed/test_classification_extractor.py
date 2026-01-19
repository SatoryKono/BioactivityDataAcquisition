"""Unit tests for PubMed ClassificationExtractor.

Tests the new extraction methods for chemicals, gene symbols, and databanks.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors import ClassificationExtractor


class TestParseChemicals:
    """Tests for parse_chemicals method."""

    def test_parse_chemicals_basic(self) -> None:
        """Should extract chemical names from ChemicalList."""
        xml = """
        <MedlineCitation>
            <ChemicalList>
                <Chemical>
                    <RegistryNumber>0</RegistryNumber>
                    <NameOfSubstance UI="D000082">Acetaminophen</NameOfSubstance>
                </Chemical>
                <Chemical>
                    <RegistryNumber>50-78-2</RegistryNumber>
                    <NameOfSubstance UI="D001241">Aspirin</NameOfSubstance>
                </Chemical>
            </ChemicalList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_chemicals(medline)
        assert result == ["Acetaminophen", "Aspirin"]

    def test_parse_chemicals_empty_list(self) -> None:
        """Should return empty list when ChemicalList is empty."""
        xml = """
        <MedlineCitation>
            <ChemicalList></ChemicalList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_chemicals(medline)
        assert result == []

    def test_parse_chemicals_no_list(self) -> None:
        """Should return empty list when ChemicalList is missing."""
        xml = "<MedlineCitation></MedlineCitation>"
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_chemicals(medline)
        assert result == []

    def test_parse_chemicals_none_input(self) -> None:
        """Should return empty list for None input."""
        result = ClassificationExtractor.parse_chemicals(None)
        assert result == []

    def test_parse_chemicals_strips_whitespace(self) -> None:
        """Should strip whitespace from chemical names."""
        xml = """
        <MedlineCitation>
            <ChemicalList>
                <Chemical>
                    <NameOfSubstance>  Aspirin  </NameOfSubstance>
                </Chemical>
            </ChemicalList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_chemicals(medline)
        assert result == ["Aspirin"]


class TestParseGeneSymbols:
    """Tests for parse_gene_symbols method."""

    def test_parse_gene_symbols_basic(self) -> None:
        """Should extract gene symbols from GeneSymbolList."""
        xml = """
        <MedlineCitation>
            <GeneSymbolList>
                <GeneSymbol>TP53</GeneSymbol>
                <GeneSymbol>BRCA1</GeneSymbol>
                <GeneSymbol>EGFR</GeneSymbol>
            </GeneSymbolList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_gene_symbols(medline)
        assert result == ["TP53", "BRCA1", "EGFR"]

    def test_parse_gene_symbols_empty_list(self) -> None:
        """Should return empty list when GeneSymbolList is empty."""
        xml = """
        <MedlineCitation>
            <GeneSymbolList></GeneSymbolList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_gene_symbols(medline)
        assert result == []

    def test_parse_gene_symbols_no_list(self) -> None:
        """Should return empty list when GeneSymbolList is missing."""
        xml = "<MedlineCitation></MedlineCitation>"
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_gene_symbols(medline)
        assert result == []

    def test_parse_gene_symbols_none_input(self) -> None:
        """Should return empty list for None input."""
        result = ClassificationExtractor.parse_gene_symbols(None)
        assert result == []

    def test_parse_gene_symbols_strips_whitespace(self) -> None:
        """Should strip whitespace from gene symbols."""
        xml = """
        <MedlineCitation>
            <GeneSymbolList>
                <GeneSymbol>  TP53  </GeneSymbol>
            </GeneSymbolList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_gene_symbols(medline)
        assert result == ["TP53"]


class TestParseDatabanks:
    """Tests for parse_databanks method."""

    def test_parse_databanks_basic(self) -> None:
        """Should extract databank references with accession numbers."""
        xml = """
        <MedlineCitation>
            <DataBankList>
                <DataBank>
                    <DataBankName>ClinicalTrials.gov</DataBankName>
                    <AccessionNumberList>
                        <AccessionNumber>NCT01234567</AccessionNumber>
                        <AccessionNumber>NCT07654321</AccessionNumber>
                    </AccessionNumberList>
                </DataBank>
            </DataBankList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_databanks(medline)
        assert len(result) == 1
        assert result[0]["databank_name"] == "ClinicalTrials.gov"
        assert result[0]["accession_numbers"] == ["NCT01234567", "NCT07654321"]

    def test_parse_databanks_multiple_banks(self) -> None:
        """Should extract multiple databank references."""
        xml = """
        <MedlineCitation>
            <DataBankList>
                <DataBank>
                    <DataBankName>ClinicalTrials.gov</DataBankName>
                    <AccessionNumberList>
                        <AccessionNumber>NCT123</AccessionNumber>
                    </AccessionNumberList>
                </DataBank>
                <DataBank>
                    <DataBankName>GEO</DataBankName>
                    <AccessionNumberList>
                        <AccessionNumber>GSE456</AccessionNumber>
                    </AccessionNumberList>
                </DataBank>
            </DataBankList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_databanks(medline)
        assert len(result) == 2
        assert result[0]["databank_name"] == "ClinicalTrials.gov"
        assert result[1]["databank_name"] == "GEO"

    def test_parse_databanks_no_accessions(self) -> None:
        """Should handle databank without accession numbers."""
        xml = """
        <MedlineCitation>
            <DataBankList>
                <DataBank>
                    <DataBankName>PDB</DataBankName>
                </DataBank>
            </DataBankList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_databanks(medline)
        assert len(result) == 1
        assert result[0]["databank_name"] == "PDB"
        assert result[0]["accession_numbers"] == []

    def test_parse_databanks_empty_list(self) -> None:
        """Should return empty list when DataBankList is empty."""
        xml = """
        <MedlineCitation>
            <DataBankList></DataBankList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_databanks(medline)
        assert result == []

    def test_parse_databanks_no_list(self) -> None:
        """Should return empty list when DataBankList is missing."""
        xml = "<MedlineCitation></MedlineCitation>"
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_databanks(medline)
        assert result == []

    def test_parse_databanks_none_input(self) -> None:
        """Should return empty list for None input."""
        result = ClassificationExtractor.parse_databanks(None)
        assert result == []

    def test_parse_databanks_strips_whitespace(self) -> None:
        """Should strip whitespace from names and accession numbers."""
        xml = """
        <MedlineCitation>
            <DataBankList>
                <DataBank>
                    <DataBankName>  ClinicalTrials.gov  </DataBankName>
                    <AccessionNumberList>
                        <AccessionNumber>  NCT123  </AccessionNumber>
                    </AccessionNumberList>
                </DataBank>
            </DataBankList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_databanks(medline)
        assert result[0]["databank_name"] == "ClinicalTrials.gov"
        assert result[0]["accession_numbers"] == ["NCT123"]

    def test_parse_databanks_skips_empty_bank_name(self) -> None:
        """Should skip databanks without name."""
        xml = """
        <MedlineCitation>
            <DataBankList>
                <DataBank>
                    <AccessionNumberList>
                        <AccessionNumber>NCT123</AccessionNumber>
                    </AccessionNumberList>
                </DataBank>
                <DataBank>
                    <DataBankName>Valid</DataBankName>
                </DataBank>
            </DataBankList>
        </MedlineCitation>
        """
        medline = ET.fromstring(xml)
        result = ClassificationExtractor.parse_databanks(medline)
        assert len(result) == 1
        assert result[0]["databank_name"] == "Valid"
