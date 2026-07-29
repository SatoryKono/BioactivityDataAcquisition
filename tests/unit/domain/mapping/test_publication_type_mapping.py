# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for publication type mapping and normalization."""

from __future__ import annotations

import pytest

from bioetl.domain.mapping.publication_type_mapping import (
    PUBLICATION_TYPE_MAPPING,
    normalize_publication_type,
)
from bioetl.domain.types import PublicationType


pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Mapping integrity
# ---------------------------------------------------------------------------


class TestPublicationTypeMappingIntegrity:
    """Verify all mapping values are valid canonical PublicationType members."""

    def test_all_values_are_valid_canonical(self) -> None:
        """Every value in PUBLICATION_TYPE_MAPPING must be a valid PublicationType."""
        valid_values = {member.value for member in PublicationType}
        for raw, canonical in PUBLICATION_TYPE_MAPPING.items():
            assert canonical in valid_values, (
                f"Mapping key {raw!r} → {canonical!r} is not a valid "
                f"PublicationType member. Valid: {sorted(valid_values)}"
            )

    def test_mapping_is_non_empty(self) -> None:
        assert len(PUBLICATION_TYPE_MAPPING) > 0

    def test_canonical_values_are_kebab_case_lowercase(self) -> None:
        for raw, canonical in PUBLICATION_TYPE_MAPPING.items():
            assert canonical == canonical.lower(), (
                f"Canonical value {canonical!r} for key {raw!r} is not lowercase"
            )
            assert " " not in canonical, (
                f"Canonical value {canonical!r} for key {raw!r} contains spaces"
            )


# ---------------------------------------------------------------------------
# normalize_publication_type() — basic behavior
# ---------------------------------------------------------------------------


class TestNormalizePublicationType:
    """Test the normalize_publication_type function."""

    def test_publication_type__none_returns_none__27d0ae42(self) -> None:
        assert normalize_publication_type(None) is None

    def test_unknown_value_returns_lowercase(self) -> None:
        assert normalize_publication_type("UNKNOWN_TYPE") == "unknown_type"

    def test_unknown_mixed_case_returns_lowercase(self) -> None:
        assert normalize_publication_type("SomeNewType") == "somenewtype"

    def test_empty_string_returns_empty(self) -> None:
        assert normalize_publication_type("") == ""

    def test_pipe_separated_normalization(self) -> None:
        result = normalize_publication_type("Journal Article|Review")
        assert result == "journal-article|review"

    def test_pipe_separated_with_unknown(self) -> None:
        result = normalize_publication_type("Journal Article|UnknownType")
        assert result == "journal-article|unknowntype"

    def test_pipe_separated_with_whitespace(self) -> None:
        result = normalize_publication_type("Journal Article | Review")
        assert result == "journal-article|review"

    def test_idempotent_for_canonical_values(self) -> None:
        """Normalizing an already-canonical value returns the same value."""
        assert normalize_publication_type("journal-article") == "journal-article"
        assert normalize_publication_type("book") == "book"
        assert normalize_publication_type("dataset") == "dataset"


# ---------------------------------------------------------------------------
# Provider-specific parametrized tests
# ---------------------------------------------------------------------------


class TestChemblNormalization:
    """Test ChEMBL raw values → canonical."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("PUBLICATION", "journal-article"),
            ("BOOK", "book"),
            ("DATASET", "dataset"),
            ("PATENT", "patent"),
        ],
    )
    def test_chembl_mapping(self, raw: str, expected: str) -> None:
        assert normalize_publication_type(raw) == expected


class TestPubMedNormalization:
    """Test PubMed raw values → canonical."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Journal Article", "journal-article"),
            ("Review", "review"),
            ("Letter", "letter"),
            ("Editorial", "editorial"),
            ("Clinical Trial", "clinical-trial"),
            ("Meta-Analysis", "meta-analysis"),
            ("Case Reports", "case-reports"),
            ("Comparative Study", "comparative-study"),
            ("Evaluation Study", "evaluation-study"),
            ("Preprint", "preprint"),
        ],
    )
    def test_pubmed_mapping(self, raw: str, expected: str) -> None:
        assert normalize_publication_type(raw) == expected

    def test_pubmed_pipe_separated(self) -> None:
        """PubMed records may have multiple types joined by pipe."""
        result = normalize_publication_type("Journal Article|Review")
        assert result == "journal-article|review"


class TestCrossRefNormalization:
    """Test CrossRef raw values → canonical (identity mapping)."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("journal-article", "journal-article"),
            ("book-chapter", "book-chapter"),
            ("proceedings-article", "proceedings-article"),
            ("posted-content", "posted-content"),
            ("book", "book"),
            ("report", "report"),
            ("dataset", "dataset"),
            ("standard", "standard"),
        ],
    )
    def test_crossref_mapping(self, raw: str, expected: str) -> None:
        assert normalize_publication_type(raw) == expected


class TestOpenAlexNormalization:
    """Test OpenAlex raw values → canonical."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("article", "journal-article"),
            ("dissertation", "dissertation"),
            ("preprint", "preprint"),
            ("review", "review"),
            ("letter", "letter"),
            ("editorial", "editorial"),
            ("other", "other"),
            ("book", "book"),
            ("book-chapter", "book-chapter"),
            ("dataset", "dataset"),
        ],
    )
    def test_openalex_mapping(self, raw: str, expected: str) -> None:
        assert normalize_publication_type(raw) == expected


class TestSemanticScholarNormalization:
    """Test Semantic Scholar raw values → canonical."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("JournalArticle", "journal-article"),
            ("Conference", "proceedings-article"),
            ("Review", "review"),
            ("CaseReport", "case-reports"),
            ("ClinicalTrial", "clinical-trial"),
            ("MetaAnalysis", "meta-analysis"),
            ("Dataset", "dataset"),
            ("Book", "book"),
            ("BookSection", "book-chapter"),
            ("LettersAndComments", "letter"),
            ("Editorial", "editorial"),
        ],
    )
    def test_s2_mapping(self, raw: str, expected: str) -> None:
        assert normalize_publication_type(raw) == expected

    def test_s2_pipe_separated(self) -> None:
        """Semantic Scholar may have multiple types joined by pipe."""
        result = normalize_publication_type("JournalArticle|Review")
        assert result == "journal-article|review"
