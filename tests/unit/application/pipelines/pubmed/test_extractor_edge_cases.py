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
"""Extended edge case tests for PubMed XML extractors.

Tests for real-world edge cases encountered in PubMed data.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor
from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor
from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)
from bioetl.application.pipelines.pubmed.xml_parser import get_int, get_text

pytestmark = pytest.mark.unit


class TestAbstractExtractorEdgeCases:
    """Edge case tests for AbstractExtractor."""

    def test_abstract_with_nested_inline_elements(self):
        """Test abstract with multiple nested inline elements."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText>
                    This has <i>italic <b>nested bold</b></i> and
                    <sup>superscript</sup> and <sub>subscript</sub> text.
                </AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert "italic" in abstract
        assert "nested bold" in abstract
        assert "superscript" in abstract
        assert "subscript" in abstract

    def test_abstract_with_copyright_section(self):
        """Test abstract that may have CopyrightInformation sibling."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText>Main abstract content.</AbstractText>
                <CopyrightInformation>Copyright 2023</CopyrightInformation>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        # CopyrightInformation is not AbstractText, so should not be included
        assert abstract == "Main abstract content."
        assert "Copyright" not in abstract

    def test_abstract_with_nlmcategory_attribute(self):
        """Test abstract with NlmCategory attribute (common in structured abstracts)."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText Label="OBJECTIVE" NlmCategory="OBJECTIVE">
                    Study objective text.
                </AbstractText>
                <AbstractText Label="DESIGN" NlmCategory="METHODS">
                    Study design text.
                </AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert "OBJECTIVE: Study objective text." in abstract
        assert "DESIGN: Study design text." in abstract

    def test_abstract_with_only_whitespace_content(self):
        """Test abstract with AbstractText containing only whitespace."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText>

                </AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract is None

    def test_abstract_with_mixed_empty_and_content_sections(self):
        """Test abstract with some empty labeled sections."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText Label="BACKGROUND">Real background.</AbstractText>
                <AbstractText Label="METHODS">   </AbstractText>
                <AbstractText Label="RESULTS">Real results.</AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert "BACKGROUND: Real background." in abstract
        assert "RESULTS: Real results." in abstract
        assert "METHODS:" not in abstract


class TestDateExtractorEdgeCases:
    """Edge case tests for DateExtractor."""

    def test_medline_date_month_range(self):
        """Test handling of MedlineDate with month range (end-of-period)."""
        xml = """
        <PubDate>
            <MedlineDate>2023 Jan-Feb</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # MedlineDate "2023 Jan-Feb" → year=2023, month=Feb (end of range)
        assert year_int == 2023
        assert date_str == "2023-02-28"  # Feb last valid day

    def test_medline_date_season_spring(self):
        """Test handling of MedlineDate with season (Spring)."""
        xml = """
        <PubDate>
            <MedlineDate>2023 Spring</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # Spring → May (end of Mar-May period)
        assert year_int == 2023
        assert date_str == "2023-05-31"  # May has 31 days

    def test_medline_date_season_winter(self):
        """Test handling of MedlineDate with season (Winter)."""
        xml = """
        <PubDate>
            <MedlineDate>2023 Winter</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # Winter → Feb (end of Dec-Feb period)
        assert year_int == 2023
        assert date_str == "2023-02-28"  # Feb last valid day

    def test_medline_date_quarter(self):
        """Test handling of MedlineDate with quarter."""
        xml = """
        <PubDate>
            <MedlineDate>2023 2nd Quart</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # 2nd Quart (Q2) → Jun (end of Apr-Jun)
        assert year_int == 2023
        assert date_str == "2023-06-30"

    def test_medline_date_single_month(self):
        """Test handling of MedlineDate with single month."""
        xml = """
        <PubDate>
            <MedlineDate>2023 September</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert year_int == 2023
        assert date_str == "2023-09-30"

    def test_medline_date_year_only(self):
        """Test handling of MedlineDate with year only."""
        xml = """
        <PubDate>
            <MedlineDate>2023</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # Year only → end-of-year (Dec 31)
        assert year_int == 2023
        assert date_str == "2023-12-31"

    def test_medline_date_cross_year_range(self):
        """Test handling of MedlineDate with cross-year range."""
        xml = """
        <PubDate>
            <MedlineDate>2022 Dec-2023 Jan</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # Cross-year: take second year (2023) and second month (Jan)
        assert year_int == 2023
        assert date_str == "2023-01-31"  # Jan has 31 days

    def test_medline_date_invalid(self):
        """Test handling of invalid MedlineDate (no year)."""
        xml = """
        <PubDate>
            <MedlineDate>TBD</MedlineDate>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # No valid year found
        assert date_str is None
        assert year_int is None

    def test_season_in_month_field(self):
        """Test handling of season names in Month field."""
        # Sometimes PubMed uses seasons like "Winter", "Summer"
        xml = """
        <PubDate>
            <Year>2023</Year>
            <Month>Winter</Month>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert year_int == 2023
        # "Win" maps to "01" (January) in the month map
        assert date_str == "2023-01" or date_str.startswith("2023")

    def test_year_with_invalid_text(self):
        """Test handling of non-numeric year (end-of-period: day 30)."""
        xml = """
        <PubDate>
            <Year>TBD</Year>
            <Month>03</Month>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # Year is not numeric, but it's still used in date_str
        # End-of-period strategy adds day 30 for year+month without day
        assert date_str == "TBD-03-30"
        assert year_int is None

    def test_partial_date_month_only_no_year(self):
        """Test date with month but no year."""
        xml = """
        <PubDate>
            <Month>06</Month>
            <Day>15</Day>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        # No year means no date string
        assert date_str is None
        assert year_int is None

    def test_history_with_multiple_same_status(self):
        """Test history with multiple dates of same PubStatus (takes first)."""
        xml = """
        <History>
            <PubMedPubDate PubStatus="received">
                <Year>2022</Year><Month>01</Month><Day>01</Day>
            </PubMedPubDate>
            <PubMedPubDate PubStatus="received">
                <Year>2022</Year><Month>02</Month><Day>15</Day>
            </PubMedPubDate>
        </History>
        """
        history = ET.fromstring(xml)
        result = DateExtractor.extract_history_date(history, "received")
        # Should return first matching date
        assert result == "2022-01-01"

    def test_article_date_nested_in_article(self):
        """Test ArticleDate at different nesting levels."""
        xml = """
        <Article>
            <ELocationID>10.1234/test</ELocationID>
            <ArticleDate DateType="Electronic">
                <Year>2023</Year><Month>05</Month><Day>20</Day>
            </ArticleDate>
        </Article>
        """
        article = ET.fromstring(xml)
        result = DateExtractor.extract_article_date(article, "Electronic")
        assert result == "2023-05-20"

    def test_long_month_name(self):
        """Test full month name handling."""
        xml = """
        <PubDate>
            <Year>2023</Year>
            <Month>September</Month>
            <Day>15</Day>
        </PubDate>
        """
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert year_int == 2023
        assert date_str == "2023-09-15"


class TestAuthorExtractorEdgeCases:
    """Edge case tests for AuthorExtractor."""

    def test_author_with_affiliation(self):
        """Test author with AffiliationInfo child (should be ignored)."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Smith</LastName>
                    <Initials>J</Initials>
                    <AffiliationInfo>
                        <Affiliation>University of Test</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Smith, J"]

    def test_author_with_identifier(self):
        """Test author with Identifier child (ORCID, etc.)."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>JM</Initials>
                    <Identifier Source="ORCID">0000-0001-2345-6789</Identifier>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, JM"]

    def test_author_with_valid_yn_attribute(self):
        """Test author with ValidYN attribute."""
        xml = """
        <Article>
            <AuthorList>
                <Author ValidYN="Y">
                    <LastName>Valid</LastName>
                    <Initials>A</Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Valid, A"]

    def test_author_list_complete_yn_attribute(self):
        """Test AuthorList with CompleteYN attribute."""
        xml = """
        <Article>
            <AuthorList CompleteYN="N">
                <Author>
                    <LastName>First</LastName>
                    <Initials>A</Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        # Should still extract authors even with CompleteYN="N"
        assert authors == ["First, A"]

    def test_author_with_suffix(self):
        """Test author with Suffix element."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Smith</LastName>
                    <Initials>J</Initials>
                    <Suffix>Jr</Suffix>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        # Suffix is not included in current implementation
        assert authors == ["Smith, J"]

    def test_many_authors(self):
        """Test extraction of many authors."""
        authors_xml = ""
        for i in range(100):
            authors_xml += f"""
                <Author>
                    <LastName>Author{i}</LastName>
                    <Initials>A{i}</Initials>
                </Author>
            """
        xml = f"""
        <Article>
            <AuthorList>
                {authors_xml}
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert len(authors) == 100
        assert authors[0] == "Author0, A0"
        assert authors[99] == "Author99, A99"


class TestIdentifierExtractorEdgeCases:
    """Edge case tests for IdentifierExtractor."""

    def test_multiple_elocationid_elements(self):
        """Test extraction when multiple ELocationID elements exist."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="pii">S1234-5678(23)00001-2</ELocationID>
                <ELocationID EIdType="doi">10.1234/correct.doi</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/correct.doi"

    def test_empty_doi_element(self):
        """Test handling of empty DOI element."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi"></ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi is None

    def test_doi_with_special_characters(self):
        """Test DOI with special characters."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.1234/abc-def.2023(05)_123</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/abc-def.2023(05)_123"

    def test_pmc_id_variants(self):
        """Test various PMC ID formats."""
        test_cases = [
            ("PMC123456", "PMC123456"),
            ("PMC9876543", "PMC9876543"),
        ]
        for pmc_value, expected in test_cases:
            xml = f"""
            <PubmedArticle>
                <ArticleIdList>
                    <ArticleId IdType="pmc">{pmc_value}</ArticleId>
                </ArticleIdList>
            </PubmedArticle>
            """
            root = ET.fromstring(xml)
            result = IdentifierExtractor.extract_pmc_id(root)
            assert result == expected

    def test_article_id_list_multiple_types(self):
        """Test ArticleIdList with many different ID types."""
        xml = """
        <PubmedArticle>
            <Article>
                <Title>Test</Title>
            </Article>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345678</ArticleId>
                <ArticleId IdType="pii">S1234-5678</ArticleId>
                <ArticleId IdType="mid">NIHMS123456</ArticleId>
                <ArticleId IdType="pmc">PMC7654321</ArticleId>
                <ArticleId IdType="doi">10.1234/final.doi</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        pmc = IdentifierExtractor.extract_pmc_id(root)
        assert doi == "10.1234/final.doi"
        assert pmc == "PMC7654321"


class TestClassificationExtractorEdgeCases:
    """Edge case tests for ClassificationExtractor."""

    def test_multiple_keyword_lists(self):
        """Test extraction with multiple KeywordList elements."""
        xml = """
        <MedlineCitation>
            <KeywordList Owner="NOTNLM">
                <Keyword>keyword1</Keyword>
                <Keyword>keyword2</Keyword>
            </KeywordList>
            <KeywordList Owner="NLM">
                <Keyword>keyword3</Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        # Should extract from first KeywordList only (based on .find())
        assert keywords == ["keyword1", "keyword2"]

    def test_keyword_with_major_topic_attribute(self):
        """Test keyword with MajorTopicYN attribute."""
        xml = """
        <MedlineCitation>
            <KeywordList>
                <Keyword MajorTopicYN="Y">major keyword</Keyword>
                <Keyword MajorTopicYN="N">minor keyword</Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == ["major keyword", "minor keyword"]

    def test_mesh_terms_with_qualifiers(self):
        """Test that only DescriptorName is extracted, not QualifierName."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
                <MeshHeading>
                    <DescriptorName UI="D000123" MajorTopicYN="Y">Cancer</DescriptorName>
                    <QualifierName UI="Q000235" MajorTopicYN="N">genetics</QualifierName>
                    <QualifierName UI="Q000628" MajorTopicYN="N">therapy</QualifierName>
                </MeshHeading>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        mesh_terms = ClassificationExtractor.parse_mesh_terms(node)
        assert mesh_terms == ["Cancer"]
        assert "genetics" not in mesh_terms
        assert "therapy" not in mesh_terms

    def test_empty_mesh_descriptor(self):
        """Test MeshHeading with empty DescriptorName."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
                <MeshHeading>
                    <DescriptorName></DescriptorName>
                </MeshHeading>
                <MeshHeading>
                    <DescriptorName>Valid Term</DescriptorName>
                </MeshHeading>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        mesh_terms = ClassificationExtractor.parse_mesh_terms(node)
        assert mesh_terms == ["Valid Term"]

    def test_publication_types_with_ui_attribute(self):
        """Test publication types with UI attribute."""
        xml = """
        <Article>
            <PublicationTypeList>
                <PublicationType UI="D016428">Journal Article</PublicationType>
                <PublicationType UI="D016454">Review</PublicationType>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == ["Journal Article", "Review"]

    def test_many_mesh_terms(self):
        """Test extraction of many MeSH terms."""
        mesh_xml = ""
        for i in range(50):
            mesh_xml += f"""
                <MeshHeading>
                    <DescriptorName>Term{i}</DescriptorName>
                </MeshHeading>
            """
        xml = f"""
        <MedlineCitation>
            <MeshHeadingList>
                {mesh_xml}
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        mesh_terms = ClassificationExtractor.parse_mesh_terms(node)
        assert len(mesh_terms) == 50


class TestXmlUtilsEdgeCases:
    """Edge case tests for xml_parser functions."""

    def test_get_text_with_child_elements(self):
        """Test get_text when element has child elements."""
        xml = "<Element>Text <child>with</child> children</Element>"
        node = ET.fromstring(xml)
        result = get_text(node)
        # get_text only returns direct text content, not child text
        assert result == "Text"

    def test_get_text_tail_text_ignored(self):
        """Test that tail text is not included."""
        xml = "<Root><Element>inner</Element> tail text</Root>"
        root = ET.fromstring(xml)
        elem = root.find("Element")
        result = get_text(elem)
        assert result == "inner"

    def test_get_int_with_leading_zeros(self):
        """Test get_int with leading zeros."""
        xml = "<Element>0042</Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result == 42

    def test_get_int_with_plus_sign(self):
        """Test get_int with plus sign (should fail)."""
        xml = "<Element>+10</Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        # Python int() actually accepts +10
        assert result == 10

    def test_get_int_very_large_number(self):
        """Test get_int with very large number."""
        xml = "<Element>99999999999999999999</Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result == 99999999999999999999

    def test_get_text_newlines_preserved(self):
        """Test that newlines are stripped from get_text."""
        xml = "<Element>\n  multi\n  line\n  </Element>"
        node = ET.fromstring(xml)
        result = get_text(node)
        # strip() removes leading/trailing whitespace including newlines
        assert result == "multi\n  line"


class TestExtractorProcessMethod:
    """Tests for the Template Method process() in extractors."""

    def test_abstract_extractor_process(self):
        """Test AbstractExtractor.process() template method."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText>Test abstract.</AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        extractor = AbstractExtractor()
        result = extractor.process(node)
        assert result == "Test abstract."

    def test_author_extractor_process(self):
        """Test AuthorExtractor.process() template method."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Test</LastName>
                    <Initials>A</Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        extractor = AuthorExtractor()
        result = extractor.process(node)
        assert result == ["Test, A"]

    def test_date_extractor_normalize_returns_typed_dict(self):
        """Test DateExtractor.normalize() returns proper NormalizedDate."""
        extractor = DateExtractor()
        raw = {"year": "2023", "month": "06", "day": "15"}
        result = extractor.normalize(raw)
        assert result["date_str"] == "2023-06-15"
        assert result["year_int"] == 2023

    def test_identifier_extractor_normalize(self):
        """Test IdentifierExtractor.normalize() trims whitespace."""
        extractor = IdentifierExtractor()
        raw = {"doi": "  10.1234/test  ", "pmc_id": "  PMC123  "}
        result = extractor.normalize(raw)
        assert result["doi"] == "10.1234/test"
        assert result["pmc_id"] == "PMC123"
