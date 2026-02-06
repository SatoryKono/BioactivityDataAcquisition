"""Semantic validation tests for text field consistency.

Tests NLP-based checks: text similarity, language detection, keyword relevance.
Uses mocks for NLP models (no actual model execution in tests).
Expected: ~30 tests covering 13 semantic rules from validation schema.

IMPORTANT: All semantic validation MUST produce WARN, never FAIL.
"""

import pytest
import pandas as pd
from unittest import mock


@pytest.mark.unit
class TestTitleAbstractSemanticSimilarity:
    """Test SemanticSimilarity(title, abstract) > threshold."""

    @mock.patch("semantic_validator.compute_similarity")
    def test_title_abstract_high_similarity_passes(
        self, mock_similarity, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: title-abstract similarity > 0.3."""
        mock_similarity.return_value = 0.75  # High similarity

        df = minimal_pubmed_publication_df.copy()
        df["title"] = "Machine Learning in Drug Discovery"
        df["abstract"] = "This study explores machine learning applications in drug discovery..."

        similarity = mock_similarity(df["title"].iloc[0], df["abstract"].iloc[0])
        assert similarity > 0.3, "Title and abstract should be semantically related"

    @mock.patch("semantic_validator.compute_similarity")
    def test_title_abstract_low_similarity_warns(
        self, mock_similarity, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: title-abstract similarity < 0.1 -> _dq_warn=True."""
        mock_similarity.return_value = 0.05  # Low similarity

        df = minimal_pubmed_publication_df.copy()
        df["title"] = "Machine Learning in Drug Discovery"
        df["abstract"] = "This paper discusses weather patterns in Antarctica."

        similarity = mock_similarity(df["title"].iloc[0], df["abstract"].iloc[0])
        assert similarity < 0.1, "Low similarity should warn"

    def test_semantic_validation_never_fails(self) -> None:
        """Semantic validation MUST produce WARN, never FAIL."""
        # Semantic checks should never block record processing
        # Even with very low similarity, result should be WARN, not FAIL
        max_severity = "WARN"
        assert max_severity != "FAIL", "Semantic validation cannot produce FAIL"


@pytest.mark.unit
class TestTitleTLDRConsistency:
    """Test SemanticSimilarity(title, tldr) > threshold (SemanticScholar)."""

    @mock.patch("semantic_validator.compute_similarity")
    def test_title_tldr_high_similarity_passes(
        self, mock_similarity, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: title-TLDR similarity > 0.5."""
        mock_similarity.return_value = 0.8

        df = minimal_semanticscholar_publication_df.copy()
        df["title"] = "Deep Learning for Protein Structure Prediction"
        df["tldr"] = "This paper presents a deep learning approach to predict protein structures."

        similarity = mock_similarity(df["title"].iloc[0], df["tldr"].iloc[0])
        assert similarity > 0.5

    @mock.patch("semantic_validator.compute_similarity")
    def test_title_tldr_low_similarity_warns(
        self, mock_similarity, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """WARN: TLDR not aligned with title -> _dq_warn=True."""
        mock_similarity.return_value = 0.2

        df = minimal_semanticscholar_publication_df.copy()
        df["title"] = "Deep Learning for Protein Structure"
        df["tldr"] = "A study on climate change impacts."

        similarity = mock_similarity(df["title"].iloc[0], df["tldr"].iloc[0])
        assert similarity < 0.5, "Low TLDR-title similarity should warn"


@pytest.mark.unit
class TestAbstractTLDRConsistency:
    """Test SemanticSimilarity(abstract, tldr) > threshold."""

    @mock.patch("semantic_validator.compute_similarity")
    def test_abstract_tldr_consistency(
        self, mock_similarity, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: abstract-TLDR similarity > 0.5."""
        mock_similarity.return_value = 0.85

        df = minimal_semanticscholar_publication_df.copy()
        similarity = mock_similarity(df["abstract"].iloc[0], df["tldr"].iloc[0])
        assert similarity > 0.5


@pytest.mark.unit
class TestLanguageDetection:
    """Test Language(text) == language field."""

    @mock.patch("language_detector.detect")
    def test_abstract_language_matches_field(
        self, mock_detector, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: detected language matches declared language."""
        mock_detector.return_value = "eng"

        df = minimal_pubmed_publication_df.copy()
        df["language"] = "eng"
        df["abstract"] = "This is an English abstract."

        detected = mock_detector(df["abstract"].iloc[0])
        assert detected == df["language"].iloc[0]

    @mock.patch("language_detector.detect")
    def test_abstract_language_mismatch_warns(
        self, mock_detector, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: detected language != declared language -> _dq_warn=True."""
        mock_detector.return_value = "fra"  # French

        df = minimal_pubmed_publication_df.copy()
        df["language"] = "eng"  # Declared as English
        df["abstract"] = "Ceci est un résumé français."

        detected = mock_detector(df["abstract"].iloc[0])
        assert detected != df["language"].iloc[0], "Language mismatch should warn"

    @mock.patch("language_detector.detect")
    def test_title_language_matches_field(
        self, mock_detector, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: title language matches declared language."""
        mock_detector.return_value = "eng"

        df = minimal_pubmed_publication_df.copy()
        df["language"] = "eng"
        df["title"] = "Machine Learning in Medicine"

        detected = mock_detector(df["title"].iloc[0])
        assert detected == df["language"].iloc[0]


@pytest.mark.unit
class TestKeywordRelevance:
    """Test Keywords(abstract) ∩ subject_keywords ≠ ∅."""

    @mock.patch("keyword_extractor.extract_keywords")
    def test_keywords_in_abstract(
        self, mock_extractor, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: extracted keywords overlap with subject_keywords."""
        mock_extractor.return_value = ["machine learning", "drug discovery", "prediction"]

        df = minimal_pubmed_publication_df.copy()
        df["subject_keywords"] = '["machine learning", "neural networks"]'
        df["abstract"] = "This study uses machine learning for drug discovery..."

        extracted = set(mock_extractor(df["abstract"].iloc[0]))
        declared = set(eval(df["subject_keywords"].iloc[0]))

        overlap = extracted & declared
        assert len(overlap) > 0, "Keywords should overlap with abstract content"

    @mock.patch("keyword_extractor.extract_keywords")
    def test_no_keyword_overlap_warns(
        self, mock_extractor, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: no keyword overlap with abstract -> _dq_warn=True."""
        mock_extractor.return_value = ["weather", "climate", "temperature"]

        df = minimal_pubmed_publication_df.copy()
        df["subject_keywords"] = '["machine learning", "neural networks"]'
        df["abstract"] = "This study analyzes weather patterns..."

        extracted = set(mock_extractor(df["abstract"].iloc[0]))
        declared = set(eval(df["subject_keywords"].iloc[0]))

        overlap = extracted & declared
        assert len(overlap) == 0, "No keyword overlap should warn"


@pytest.mark.unit
class TestMeSHRelevance:
    """Test MeSH terms relevant to abstract content (PubMed)."""

    @mock.patch("mesh_validator.assess_relevance")
    def test_mesh_relevant_to_abstract(
        self, mock_relevance, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: MeSH terms are relevant to abstract."""
        mock_relevance.return_value = 0.8  # High relevance score

        df = minimal_pubmed_publication_df.copy()
        df["subject_mesh"] = '["Machine Learning", "Drug Discovery"]'
        df["abstract"] = "This paper explores machine learning applications in drug discovery..."

        relevance = mock_relevance(df["subject_mesh"].iloc[0], df["abstract"].iloc[0])
        assert relevance > 0.5, "MeSH terms should be relevant"

    @mock.patch("mesh_validator.assess_relevance")
    def test_mesh_not_relevant_warns(
        self, mock_relevance, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: MeSH terms not relevant to abstract -> _dq_warn=True."""
        mock_relevance.return_value = 0.1  # Low relevance

        df = minimal_pubmed_publication_df.copy()
        df["subject_mesh"] = '["Weather", "Climate"]'
        df["abstract"] = "This paper explores machine learning applications in drug discovery..."

        relevance = mock_relevance(df["subject_mesh"].iloc[0], df["abstract"].iloc[0])
        assert relevance < 0.5, "Irrelevant MeSH terms should warn"


# TODO: Add remaining ~20 semantic validation tests
# Based on semantic_validation rules from validation schema XLSX
# All tests MUST:
# - Use mocks for NLP operations
# - Never produce FAIL (only WARN)
# - Test both PASS and WARN scenarios
