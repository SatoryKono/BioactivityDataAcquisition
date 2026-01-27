"""Shared title matching utilities for fallback search.

Provides consistent title comparison across all adapters that support
title-based fallback when DOI resolution fails.

Used by:
- CrossRef adapter
- OpenAlex adapter
- SemanticScholar adapter
"""

from __future__ import annotations

import string


def normalize_title(title: str) -> str:
    """Normalize title for comparison.

    Normalizes whitespace, converts to lowercase, and removes punctuation.
    Punctuation is replaced by spaces to handle cases like "Non-linear" vs "Non linear".

    Args:
        title: Title string to normalize.

    Returns:
        Normalized title (lowercase, no punctuation, single spaces).
    """
    if not title:
        return ""
    # Replace punctuation with spaces
    translator = str.maketrans(string.punctuation, " " * len(string.punctuation))
    cleaned = title.translate(translator)
    # Normalize whitespace
    return " ".join(cleaned.lower().strip().split())


# Minimum word count for substring matching to avoid false positives
# Shorter titles use fuzzy matching instead
MIN_WORDS_FOR_SUBSTRING = 4


def titles_match(
    query_title: str,
    found_title: str,
    threshold: float = 0.8,
    method: str = "substring",
) -> bool:
    """Check if titles match using specified method.

    Supports multiple matching strategies for different use cases:
    - "exact": Requires exact match (after normalization)
    - "substring": Matches if one title contains the other (default)
    - "fuzzy": Uses Jaccard similarity on word sets

    For "substring" method with short titles (< 4 words), automatically
    falls back to "fuzzy" matching to avoid false positives like
    "Cancer" matching "Breast Cancer Research Methods".

    Args:
        query_title: The title we're searching for.
        found_title: The title found in API response.
        threshold: Similarity threshold for fuzzy matching (default 0.8).
        method: Matching method: "exact", "substring", or "fuzzy".

    Returns:
        True if titles match according to the specified method.

    Examples:
        >>> titles_match("Machine Learning", "machine learning", method="exact")
        True
        >>> titles_match("Neural Networks", "Deep Neural Networks", method="substring")
        True
        >>> titles_match("ML Models", "Machine Learning", method="fuzzy", threshold=0.5)
        True
        >>> titles_match("Cancer", "Breast Cancer Research", method="substring")
        False  # Short title, falls back to fuzzy
    """
    q = normalize_title(query_title)
    f = normalize_title(found_title)

    if method == "exact":
        return q == f

    if method == "substring":
        # Exact match is always valid
        if q == f:
            return True

        # For short titles, use fuzzy matching to avoid false positives
        q_words = q.split()
        f_words = f.split()
        if len(q_words) < MIN_WORDS_FOR_SUBSTRING or len(f_words) < MIN_WORDS_FOR_SUBSTRING:
            # Fall back to fuzzy matching for short titles
            if not q_words or not f_words:
                return False
            intersection = len(set(q_words) & set(f_words))
            union = len(set(q_words) | set(f_words))
            return (intersection / union) >= threshold

        # Standard substring containment for longer titles
        return q in f or f in q

    if method == "fuzzy":
        # Jaccard similarity on word sets
        q_word_set = set(q.split())
        f_word_set = set(f.split())
        if not q_word_set or not f_word_set:
            return False
        intersection = len(q_word_set & f_word_set)
        union = len(q_word_set | f_word_set)
        return (intersection / union) >= threshold

    # Default to exact match for unknown methods
    return q == f
