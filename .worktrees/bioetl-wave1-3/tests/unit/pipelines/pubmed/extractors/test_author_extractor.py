"""Unit tests for AuthorExtractor."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor


class TestParseAuthors:
    """Tests for parse_authors method."""

    def test_author_with_initials(self):
        """Test author with LastName and Initials."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>J</Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, J"]

    def test_author_with_forename(self):
        """Test author with LastName and ForeName (no Initials)."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Smith</LastName>
                    <ForeName>John</ForeName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Smith, John"]

    def test_author_lastname_only(self):
        """Test author with only LastName."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Johnson</LastName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Johnson"]

    def test_collective_author(self):
        """Test collective/group author."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <CollectiveName>WHO Working Group</CollectiveName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["WHO Working Group"]

    def test_multiple_authors(self):
        """Test multiple authors."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>J</Initials>
                </Author>
                <Author>
                    <LastName>Smith</LastName>
                    <Initials>AB</Initials>
                </Author>
                <Author>
                    <LastName>Johnson</LastName>
                    <ForeName>Mary</ForeName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, J", "Smith, AB", "Johnson, Mary"]

    def test_mixed_individual_and_collective(self):
        """Test mix of individual and collective authors."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>J</Initials>
                </Author>
                <Author>
                    <CollectiveName>Research Consortium</CollectiveName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, J", "Research Consortium"]

    def test_empty_author_list(self):
        """Test empty AuthorList."""
        xml = """
        <Article>
            <AuthorList>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == []

    def test_no_author_list(self):
        """Test article without AuthorList element."""
        xml = "<Article></Article>"
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == []

    def test_author_with_both_initials_and_forename(self):
        """Test author with both Initials and ForeName (Initials takes precedence)."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>JM</Initials>
                    <ForeName>John Michael</ForeName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, JM"]

    def test_author_with_empty_elements(self):
        """Test author with empty text elements."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName></LastName>
                    <Initials></Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == []


class TestParseAffiliations:
    """Tests for parse_affiliations method."""

    def test_single_author_affiliation(self):
        """Test single author with affiliation."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>University of Example</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_affiliations(node)
        assert affs == ["University of Example"]

    def test_multiple_authors_same_affiliation(self):
        """Test multiple authors with same affiliation (deduplication)."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>University of Example</Affiliation>
                    </AffiliationInfo>
                </Author>
                <Author>
                    <LastName>Smith</LastName>
                    <AffiliationInfo>
                        <Affiliation>University of Example</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_affiliations(node)
        assert affs == ["University of Example"]

    def test_multiple_affiliations(self):
        """Test multiple distinct affiliations."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>Inst A</Affiliation>
                    </AffiliationInfo>
                </Author>
                <Author>
                    <LastName>Smith</LastName>
                    <AffiliationInfo>
                        <Affiliation>Inst B</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_affiliations(node)
        # Sorted order
        assert affs == ["Inst A", "Inst B"]

    def test_author_multiple_affiliations(self):
        """Test one author with multiple affiliations."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>Inst A</Affiliation>
                    </AffiliationInfo>
                    <AffiliationInfo>
                        <Affiliation>Inst B</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_affiliations(node)
        assert affs == ["Inst A", "Inst B"]

    def test_no_affiliations(self):
        """Test author without affiliations."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_affiliations(node)
        assert affs == []


class TestParseStructuredAffiliations:
    """Tests for parse_structured_affiliations method."""

    def test_basic_structured_affiliation(self):
        """Test extracting structured affiliation without identifier."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>University of Example, Department of Science</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        assert len(affs) == 1
        assert affs[0]["text"] == "University of Example, Department of Science"
        assert affs[0]["identifier"] is None
        assert affs[0]["identifier_source"] is None

    def test_affiliation_with_ror_identifier(self):
        """Test extracting affiliation with ROR identifier."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>Harvard University</Affiliation>
                        <Identifier Source="ROR">https://ror.org/03vek6s52</Identifier>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        assert len(affs) == 1
        assert affs[0]["text"] == "Harvard University"
        assert affs[0]["identifier"] == "https://ror.org/03vek6s52"
        assert affs[0]["identifier_source"] == "ROR"

    def test_affiliation_with_grid_identifier(self):
        """Test extracting affiliation with GRID identifier."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Smith</LastName>
                    <AffiliationInfo>
                        <Affiliation>MIT</Affiliation>
                        <Identifier Source="GRID">grid.116068.8</Identifier>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        assert len(affs) == 1
        assert affs[0]["identifier"] == "grid.116068.8"
        assert affs[0]["identifier_source"] == "GRID"

    def test_ror_takes_precedence_over_grid(self):
        """Test that ROR identifier takes precedence over GRID."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>University</Affiliation>
                        <Identifier Source="GRID">grid.12345.6</Identifier>
                        <Identifier Source="ROR">https://ror.org/primary</Identifier>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        assert len(affs) == 1
        assert affs[0]["identifier"] == "https://ror.org/primary"
        assert affs[0]["identifier_source"] == "ROR"

    def test_affiliation_with_email(self):
        """Test extracting email from affiliation text."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>University of Example. Electronic address: john.doe@example.edu</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        assert len(affs) == 1
        assert affs[0]["email"] == "john.doe@example.edu"

    def test_multiple_authors_same_affiliation_deduped(self):
        """Test that duplicate affiliations from multiple authors are deduplicated."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>Shared Institution</Affiliation>
                    </AffiliationInfo>
                </Author>
                <Author>
                    <LastName>Smith</LastName>
                    <AffiliationInfo>
                        <Affiliation>Shared Institution</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        # Should be deduplicated by text
        assert len(affs) == 1
        assert affs[0]["text"] == "Shared Institution"

    def test_multiple_distinct_affiliations(self):
        """Test extracting multiple distinct structured affiliations."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>Institution A</Affiliation>
                        <Identifier Source="ROR">https://ror.org/inst-a</Identifier>
                    </AffiliationInfo>
                </Author>
                <Author>
                    <LastName>Smith</LastName>
                    <AffiliationInfo>
                        <Affiliation>Institution B</Affiliation>
                        <Identifier Source="GRID">grid.inst-b</Identifier>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        # Sorted by text
        assert len(affs) == 2
        assert affs[0]["text"] == "Institution A"
        assert affs[0]["identifier_source"] == "ROR"
        assert affs[1]["text"] == "Institution B"
        assert affs[1]["identifier_source"] == "GRID"

    def test_no_author_list_returns_empty(self):
        """Test that missing AuthorList returns empty list."""
        xml = "<Article></Article>"
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)
        assert affs == []

    def test_author_with_multiple_affiliations(self):
        """Test one author with multiple affiliations."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <AffiliationInfo>
                        <Affiliation>Primary Institution</Affiliation>
                    </AffiliationInfo>
                    <AffiliationInfo>
                        <Affiliation>Secondary Institution</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        affs = AuthorExtractor.parse_structured_affiliations(node)

        assert len(affs) == 2


class TestEmailExtraction:
    """Tests for email extraction from affiliation text."""

    def test_extract_email_standard_format(self):
        """Test extracting standard format email."""
        extractor = AuthorExtractor()
        email = extractor._extract_email_from_text("Contact: user@domain.com for info")
        assert email == "user@domain.com"

    def test_extract_email_with_subdomain(self):
        """Test extracting email with subdomain."""
        extractor = AuthorExtractor()
        email = extractor._extract_email_from_text(
            "Electronic address: researcher@dept.university.edu"
        )
        assert email == "researcher@dept.university.edu"

    def test_no_email_returns_none(self):
        """Test that text without email returns None."""
        extractor = AuthorExtractor()
        email = extractor._extract_email_from_text("University of Example, Department")
        assert email is None

    def test_multiple_emails_returns_first(self):
        """Test that multiple emails returns the first one."""
        extractor = AuthorExtractor()
        email = extractor._extract_email_from_text(
            "Contact: first@example.com or second@example.org"
        )
        assert email == "first@example.com"
