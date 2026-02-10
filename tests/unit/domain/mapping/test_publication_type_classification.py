"""Tests for unified publication type classification module."""

from __future__ import annotations

import pytest

from bioetl.domain.mapping.publication_type_classification import (
    CLASSIFICATION_TABLE_SIZE,
    PublicationTypeEntry,
    _CLASSIFICATION_TABLE,
    _CROSSREF_LOOKUP,
    _OPENALEX_LOOKUP,
    _PUBMED_LOOKUP,
    _S2_LOOKUP,
    classify_publication_type,
)


class TestClassificationTableIntegrity:
    """Verify the classification table is well-formed."""

    def test_table_has_214_entries(self) -> None:
        assert CLASSIFICATION_TABLE_SIZE == 214

    def test_all_entries_have_valid_class_codes(self) -> None:
        valid_codes = {"EXP", "REV", "PEER"}
        for row in _CLASSIFICATION_TABLE:
            assert row[2] in valid_codes, f"Invalid class_code in row: {row[0]}"

    def test_unified_types_are_unique(self) -> None:
        types = [row[0] for row in _CLASSIFICATION_TABLE]
        assert len(types) == len(set(types)), "Duplicate unified_type found"


class TestOpenAlexClassification:
    """Test OpenAlex provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified", "expected_class"),
        [
            ("article", "Journal Article", "EXP"),
            ("preprint", "Preprint", "EXP"),
            ("dataset", "Dataset", "EXP"),
            ("review", "Review", "REV"),
            ("book", "Book", "REV"),
            ("book-chapter", "Book Chapter", "REV"),
            ("editorial", "Editorial", "REV"),
            ("letter", "Letter", "REV"),
            ("erratum", "Erratum", "REV"),
            ("retraction", "Retraction notice", "REV"),
            ("peer-review", "Peer Review", "PEER"),
            ("other", "Other", "REV"),
            ("report", "Report", "EXP"),
            ("dissertation", "Dissertation", "EXP"),
            ("software", "Software", "EXP"),
            ("paratext", "Paratext", "REV"),
            ("libguides", "Libguides", "REV"),
            ("grant", "Grant", "REV"),
            ("standard", "Standard", "REV"),
            ("reference-entry", "Reference Entry", "REV"),
            ("database", "Database", "EXP"),
            ("supplementary-materials", "Supplementary Materials", "EXP"),
            ("report-component", "Report Component", "EXP"),
            ("book-section", "Book Section", "REV"),
        ],
    )
    def test_known_types(
        self, raw_type: str, expected_unified: str, expected_class: str
    ) -> None:
        entry = classify_publication_type("openalex", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified
        assert entry.class_code == expected_class

    def test_unknown_type_returns_none(self) -> None:
        assert classify_publication_type("openalex", raw_type="nonexistent") is None

    def test_case_insensitive(self) -> None:
        entry = classify_publication_type("openalex", raw_type="ARTICLE")
        assert entry is not None
        assert entry.unified_type == "Journal Article"

    def test_article_star_maps_to_conference_paper(self) -> None:
        """article* in CSV adds 'article' as additional key for Conference Paper.

        But since 'article' already maps to Journal Article (row 2, primary),
        the primary mapping wins. Conference Paper is only via 'article*' which
        doesn't override.
        """
        entry = _OPENALEX_LOOKUP.get("article")
        assert entry is not None
        assert entry.unified_type == "Journal Article"


class TestCrossRefClassification:
    """Test CrossRef provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified", "expected_class"),
        [
            ("journal-article", "Journal Article", "EXP"),
            ("proceedings-article", "Conference Paper", "EXP"),
            ("posted-content", "Preprint", "EXP"),
            ("dataset", "Dataset", "EXP"),
            ("book", "Book", "REV"),
            ("book-chapter", "Book Chapter", "REV"),
            ("monograph", "Monograph", "REV"),
            ("edited-book", "Edited Book", "REV"),
            ("peer-review", "Peer Review", "PEER"),
            ("other", "Other", "REV"),
            ("component", "Component (figure/table/suppl)", "EXP"),
            ("journal", "Journal (container)", "REV"),
            ("journal-issue", "Journal Issue", "REV"),
            ("proceedings", "Proceedings (container)", "REV"),
            ("grant", "Grant", "REV"),
            ("standard", "Standard", "REV"),
        ],
    )
    def test_known_types(
        self, raw_type: str, expected_unified: str, expected_class: str
    ) -> None:
        entry = classify_publication_type("crossref", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified
        assert entry.class_code == expected_class

    def test_unknown_type_returns_none(self) -> None:
        assert classify_publication_type("crossref", raw_type="nonexistent") is None


class TestPubMedClassification:
    """Test PubMed provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified"),
        [
            ("Journal Article", "Journal Article"),
            ("Review", "Review"),
            ("Systematic Review", "Systematic Review"),
            ("Meta-Analysis", "Meta-Analysis"),
            ("Clinical Trial", "Clinical Trial"),
            ("Randomized Controlled Trial", "Randomized Controlled Trial"),
            ("Case Reports", "Case Report"),
            ("Editorial", "Editorial"),
            ("Letter", "Letter"),
            ("Practice Guideline", "Practice Guideline"),
            ("Preprint", "Preprint"),
            ("Patent", "Patent"),
            ("Published Erratum", "Erratum"),
            ("Retraction of Publication", "Retraction notice"),
            ("Observational Study", "Observational Study"),
            ("Comparative Study", "Comparative Study"),
        ],
    )
    def test_known_types(self, raw_type: str, expected_unified: str) -> None:
        entry = classify_publication_type("pubmed", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified

    def test_case_insensitive(self) -> None:
        entry = classify_publication_type("pubmed", raw_type="journal article")
        assert entry is not None
        assert entry.unified_type == "Journal Article"

    def test_multi_type_most_specific(self) -> None:
        """PubMed multi-type: should return most specific (highest specificity)."""
        types = ["Journal Article", "Randomized Controlled Trial"]
        entry = classify_publication_type("pubmed", raw_types_list=types)
        assert entry is not None
        assert entry.unified_type == "Randomized Controlled Trial"
        assert entry.specificity > 2  # More specific than Journal Article (row 2)

    def test_multi_type_with_unknown(self) -> None:
        """Unknown types should be ignored when others match."""
        types = ["UnknownType", "Clinical Trial"]
        entry = classify_publication_type("pubmed", raw_types_list=types)
        assert entry is not None
        assert entry.unified_type == "Clinical Trial"

    def test_multi_type_all_unknown(self) -> None:
        types = ["UnknownType1", "UnknownType2"]
        entry = classify_publication_type("pubmed", raw_types_list=types)
        assert entry is None

    def test_empty_list(self) -> None:
        entry = classify_publication_type("pubmed", raw_types_list=[])
        assert entry is None

    def test_clinical_trial_phases_specificity(self) -> None:
        """Phase-specific clinical trial types should be more specific than generic."""
        generic = classify_publication_type("pubmed", raw_type="Clinical Trial")
        phase_iii = classify_publication_type(
            "pubmed", raw_type="Clinical Trial, Phase III"
        )
        assert generic is not None
        assert phase_iii is not None
        assert phase_iii.specificity > generic.specificity


class TestSemanticScholarClassification:
    """Test Semantic Scholar provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified"),
        [
            ("JournalArticle", "Journal Article"),
            ("Conference", "Conference Paper"),
            ("Review", "Review"),
            ("Editorial", "Editorial"),
            ("LettersAndComments", "Letter"),
            ("Book", "Book"),
            ("BookSection", "Book Chapter"),
            ("Dataset", "Dataset"),
            ("CaseReport", "Case Report"),
            ("Study", "Clinical Study"),
            ("ClinicalTrial", "Clinical Trial"),
            ("MetaAnalysis", "Meta-Analysis"),
            ("News", "News"),
        ],
    )
    def test_known_types(self, raw_type: str, expected_unified: str) -> None:
        entry = classify_publication_type("semanticscholar", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified

    def test_multi_type_most_specific(self) -> None:
        """S2 multi-type: should return most specific."""
        types = ["JournalArticle", "ClinicalTrial"]
        entry = classify_publication_type("semanticscholar", raw_types_list=types)
        assert entry is not None
        assert entry.unified_type == "Clinical Trial"

    def test_case_insensitive(self) -> None:
        entry = classify_publication_type("semanticscholar", raw_type="journalarticle")
        assert entry is not None
        assert entry.unified_type == "Journal Article"

    def test_provider_aliases(self) -> None:
        """Both 'semanticscholar' and 's2' should work."""
        entry1 = classify_publication_type("semanticscholar", raw_type="JournalArticle")
        entry2 = classify_publication_type("s2", raw_type="JournalArticle")
        assert entry1 == entry2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_raw_type(self) -> None:
        assert classify_publication_type("openalex") is None

    def test_none_raw_types_list(self) -> None:
        assert classify_publication_type("pubmed") is None

    def test_unknown_provider(self) -> None:
        assert classify_publication_type("unknown_provider", raw_type="article") is None

    def test_entry_is_frozen(self) -> None:
        entry = classify_publication_type("openalex", raw_type="article")
        assert entry is not None
        with pytest.raises(AttributeError):
            entry.unified_type = "changed"  # type: ignore[misc]

    def test_all_lookups_built(self) -> None:
        """Verify all four lookup dicts are non-empty."""
        assert len(_OPENALEX_LOOKUP) > 0
        assert len(_CROSSREF_LOOKUP) > 0
        assert len(_PUBMED_LOOKUP) > 0
        assert len(_S2_LOOKUP) > 0

    def test_pubmed_lookup_has_all_mapped_types(self) -> None:
        """PubMed has the most mappings — verify count is reasonable."""
        assert len(_PUBMED_LOOKUP) >= 150  # Most of 214 types have PubMed mappings

    def test_s2_lettesandcomments_maps_to_letter(self) -> None:
        """LettersAndComments appears in both Letter and Comment rows.

        Letter (row 46) has lower specificity than Comment (row 47).
        The first mapping wins, so 'lettersandcomments' maps to Letter.
        """
        entry = _S2_LOOKUP.get("lettersandcomments")
        assert entry is not None
        assert entry.unified_type == "Letter"
