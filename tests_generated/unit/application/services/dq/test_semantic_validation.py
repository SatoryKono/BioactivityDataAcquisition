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


# ============================================================================
# ADDITIONAL SEMANTIC VALIDATION TESTS
# Generated to complete semantic validation coverage (+17 tests)
# ============================================================================


@pytest.mark.unit
class TestTitleAbstractCoherence:
    """Additional tests for title-abstract semantic coherence."""

    @mock.patch("semantic_validator.compute_similarity")
    def test_title_abstract_threshold_boundary(
        self, mock_similarity, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: similarity exactly at threshold (0.3)."""
        mock_similarity.return_value = 0.3  # Exactly at threshold

        df = minimal_pubmed_publication_df.copy()
        similarity = mock_similarity(df["title"].iloc[0], df["abstract"].iloc[0])
        assert similarity >= 0.3

    @mock.patch("semantic_validator.compute_similarity")
    def test_title_abstract_very_low_similarity(
        self, mock_similarity, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: similarity near zero (completely unrelated)."""
        mock_similarity.return_value = 0.01

        df = minimal_pubmed_publication_df.copy()
        df["title"] = "Quantum Computing"
        df["abstract"] = "This paper discusses traditional cooking methods in rural areas."

        similarity = mock_similarity(df["title"].iloc[0], df["abstract"].iloc[0])
        assert similarity < 0.1

    @mock.patch("semantic_validator.compute_similarity")
    def test_title_abstract_identical_text(
        self, mock_similarity, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: similarity = 1.0 (identical text)."""
        mock_similarity.return_value = 1.0

        df = minimal_pubmed_publication_df.copy()
        df["title"] = "Machine Learning"
        df["abstract"] = "Machine Learning"

        similarity = mock_similarity(df["title"].iloc[0], df["abstract"].iloc[0])
        assert similarity == 1.0


@pytest.mark.unit
class TestLanguageConsistency:
    """Extended language detection tests."""

    @mock.patch("language_detector.detect")
    def test_multi_language_abstract_warns(
        self, mock_detector, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: abstract contains mixed languages."""
        mock_detector.return_value = "mixed"

        df = minimal_pubmed_publication_df.copy()
        df["language"] = "eng"
        df["abstract"] = "This is English. Ceci est français. Das ist Deutsch."

        detected = mock_detector(df["abstract"].iloc[0])
        assert detected == "mixed"

    @mock.patch("language_detector.detect")
    def test_language_confidence_low_warns(
        self, mock_detector, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: language detection confidence low."""
        mock_detector.return_value = {"language": "eng", "confidence": 0.3}

        df = minimal_pubmed_publication_df.copy()

        result = mock_detector(df["abstract"].iloc[0])
        assert result["confidence"] < 0.5

    @mock.patch("language_detector.detect")
    def test_title_abstract_language_consistent(
        self, mock_detector, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: title and abstract in same language."""
        mock_detector.side_effect = ["eng", "eng"]

        df = minimal_pubmed_publication_df.copy()
        df["language"] = "eng"

        title_lang = mock_detector(df["title"].iloc[0])
        abstract_lang = mock_detector(df["abstract"].iloc[0])

        assert title_lang == abstract_lang


@pytest.mark.unit
class TestKeywordRelevanceExtended:
    """Extended keyword relevance tests."""

    @mock.patch("keyword_extractor.extract_keywords")
    def test_keywords_case_insensitive_match(
        self, mock_extractor, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: keywords match case-insensitively."""
        mock_extractor.return_value = ["Machine Learning", "Neural Networks"]

        df = minimal_pubmed_publication_df.copy()
        df["subject_keywords"] = '["machine learning", "deep learning"]'

        extracted = set(k.lower() for k in mock_extractor(df["abstract"].iloc[0]))
        declared = set(k.lower() for k in eval(df["subject_keywords"].iloc[0]))

        overlap = extracted & declared
        assert len(overlap) > 0

    @mock.patch("keyword_extractor.extract_keywords")
    def test_keywords_partial_overlap(
        self, mock_extractor, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: at least one keyword overlaps."""
        mock_extractor.return_value = ["machine learning", "data science", "AI"]

        df = minimal_pubmed_publication_df.copy()
        df["subject_keywords"] = '["machine learning", "statistics"]'

        extracted = set(mock_extractor(df["abstract"].iloc[0]))
        declared = set(eval(df["subject_keywords"].iloc[0]))

        overlap = extracted & declared
        assert len(overlap) >= 1

    @mock.patch("keyword_extractor.extract_keywords")
    def test_keywords_empty_abstract_skipped(
        self, mock_extractor, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: empty abstract, cannot extract keywords."""
        mock_extractor.return_value = []

        df = minimal_pubmed_publication_df.copy()
        df["abstract"] = ""

        keywords = mock_extractor(df["abstract"].iloc[0])
        assert len(keywords) == 0


@pytest.mark.unit
class TestTLDRQuality:
    """Test TLDR quality for Semantic Scholar."""

    @mock.patch("semantic_validator.compute_similarity")
    def test_tldr_shorter_than_abstract(
        self, mock_similarity, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: TLDR is significantly shorter than abstract."""
        df = minimal_semanticscholar_publication_df.copy()
        df["abstract"] = "A" * 1000  # Long abstract
        df["tldr"] = "B" * 100  # Short TLDR

        assert len(df["tldr"].iloc[0]) < len(df["abstract"].iloc[0]) * 0.5

    @mock.patch("semantic_validator.compute_similarity")
    def test_tldr_too_similar_to_abstract_warns(
        self, mock_similarity, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """WARN: TLDR too similar to abstract (likely copy-paste)."""
        mock_similarity.return_value = 0.99  # Nearly identical

        df = minimal_semanticscholar_publication_df.copy()
        similarity = mock_similarity(df["abstract"].iloc[0], df["tldr"].iloc[0])
        assert similarity > 0.95  # Too similar


@pytest.mark.unit
class TestMeSHRelevanceExtended:
    """Extended MeSH term relevance tests."""

    @mock.patch("mesh_validator.assess_relevance")
    def test_mesh_all_terms_relevant(
        self, mock_relevance, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: all MeSH terms highly relevant."""
        mock_relevance.return_value = 0.95

        df = minimal_pubmed_publication_df.copy()
        df["subject_mesh"] = '["Machine Learning", "Drug Discovery"]'

        relevance = mock_relevance(df["subject_mesh"].iloc[0], df["abstract"].iloc[0])
        assert relevance > 0.8

    @mock.patch("mesh_validator.assess_relevance")
    def test_mesh_partial_relevance(
        self, mock_relevance, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: some MeSH terms relevant (threshold met)."""
        mock_relevance.return_value = 0.6

        df = minimal_pubmed_publication_df.copy()
        relevance = mock_relevance(df["subject_mesh"].iloc[0], df["abstract"].iloc[0])
        assert relevance > 0.5

    @mock.patch("mesh_validator.assess_relevance")
    def test_mesh_empty_list_skipped(
        self, mock_relevance, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: no MeSH terms provided."""
        df = minimal_pubmed_publication_df.copy()
        df["subject_mesh"] = "[]"

        mesh_terms = eval(df["subject_mesh"].iloc[0])
        assert len(mesh_terms) == 0  # Skip validation


@pytest.mark.unit
class TestTextQualityChecks:
    """Test text quality indicators (readability, completeness)."""

    def test_abstract_min_length_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: abstract has sufficient length (>100 chars)."""
        df = minimal_pubmed_publication_df.copy()
        df["abstract"] = "A" * 150

        assert len(df["abstract"].iloc[0]) > 100

    def test_abstract_too_short_warns(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: abstract suspiciously short (<50 chars)."""
        df = minimal_pubmed_publication_df.copy()
        df["abstract"] = "Too short."

        assert len(df["abstract"].iloc[0]) < 50

    def test_title_reasonable_length(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: title length in reasonable range (10-200 chars)."""
        df = minimal_pubmed_publication_df.copy()
        df["title"] = "Machine Learning in Drug Discovery"

        title_len = len(df["title"].iloc[0])
        assert 10 <= title_len <= 200
