# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for PubMed ClassificationExtractor.

Tests the new extraction methods for chemicals, gene symbols, and databanks.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from bioetl.application.pipelines.pubmed.extractors import ClassificationExtractor


pytestmark = pytest.mark.unit


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


# ---------------------------------------------------------------------------
# Tests merged from orphan tests/unit/pipelines/pubmed/extractors/test_classification_extractor.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseKeywords:
    """Tests for parse_keywords method."""

    def test_keywords_extracted(self) -> None:
        """Test extracting keywords from KeywordList."""
        xml = """
        <MedlineCitation>
            <KeywordList>
                <Keyword>bioinformatics</Keyword>
                <Keyword>drug discovery</Keyword>
                <Keyword>machine learning</Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == ["bioinformatics", "drug discovery", "machine learning"]

    def test_single_keyword(self) -> None:
        """Test single keyword extraction."""
        xml = """
        <MedlineCitation>
            <KeywordList>
                <Keyword>proteomics</Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == ["proteomics"]

    def test_empty_keyword_list(self) -> None:
        """Test empty KeywordList."""
        xml = """
        <MedlineCitation>
            <KeywordList>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == []

    def test_no_keyword_list(self) -> None:
        """Test missing KeywordList element."""
        xml = "<MedlineCitation></MedlineCitation>"
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == []

    def test_none_node_returns_empty(self) -> None:
        """Test that None node returns empty list."""
        keywords = ClassificationExtractor.parse_keywords(None)
        assert keywords == []

    def test_keywords_stripped(self) -> None:
        """Test that keyword whitespace is stripped."""
        xml = """
        <MedlineCitation>
            <KeywordList>
                <Keyword>  spaced keyword  </Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == ["spaced keyword"]


@pytest.mark.unit
class TestParseMeshTerms:
    """Tests for parse_mesh_terms method."""

    def test_mesh_terms_extracted(self) -> None:
        """Test extracting MeSH terms from MeshHeadingList."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
                <MeshHeading>
                    <DescriptorName>Proteins</DescriptorName>
                </MeshHeading>
                <MeshHeading>
                    <DescriptorName>Drug Discovery</DescriptorName>
                </MeshHeading>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == ["Proteins", "Drug Discovery"]

    def test_mesh_heading_with_qualifiers(self) -> None:
        """Test MeSH heading with qualifiers (only descriptor extracted)."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
                <MeshHeading>
                    <DescriptorName>Neoplasms</DescriptorName>
                    <QualifierName>drug therapy</QualifierName>
                    <QualifierName>genetics</QualifierName>
                </MeshHeading>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == ["Neoplasms"]

    def test_empty_mesh_list(self) -> None:
        """Test empty MeshHeadingList."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == []

    def test_no_mesh_list(self) -> None:
        """Test missing MeshHeadingList element."""
        xml = "<MedlineCitation></MedlineCitation>"
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == []

    def test_parse_mesh_terms__node_returns_empty__e9ada348(self) -> None:
        """Test that None node returns empty list."""
        terms = ClassificationExtractor.parse_mesh_terms(None)
        assert terms == []


@pytest.mark.unit
class TestParsePublicationTypes:
    """Tests for parse_publication_types method."""

    def test_publication_types_extracted(self) -> None:
        """Test extracting publication types."""
        xml = """
        <Article>
            <PublicationTypeList>
                <PublicationType>Journal Article</PublicationType>
                <PublicationType>Research Support, N.I.H.</PublicationType>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == ["Journal Article", "Research Support, N.I.H."]

    def test_single_publication_type(self) -> None:
        """Test single publication type."""
        xml = """
        <Article>
            <PublicationTypeList>
                <PublicationType>Review</PublicationType>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == ["Review"]

    def test_empty_publication_type_xml_list(self) -> None:
        """Test empty PublicationTypeList."""
        xml = """
        <Article>
            <PublicationTypeList>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == []

    def test_no_publication_type_xml_list(self) -> None:
        """Test missing PublicationTypeList element."""
        xml = "<Article></Article>"
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == []

    def test_publication_types_stripped(self) -> None:
        """Test that publication type whitespace is stripped."""
        xml = """
        <Article>
            <PublicationTypeList>
                <PublicationType>  Case Reports  </PublicationType>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == ["Case Reports"]
