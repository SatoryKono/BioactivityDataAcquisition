"""Pure domain text similarity functions.

Provides text normalization and Jaccard similarity for cross-validation
of publication fields between seed and enricher records.

These are domain-layer equivalents of infrastructure title_matching.py,
placed here to comply with ARCH-001 import boundaries (application layer
cannot import from infrastructure).
"""

from __future__ import annotations

import string

__all__ = [
    "jaccard_similarity",
    "normalize_text",
]


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Lowercases, replaces punctuation with spaces, collapses whitespace.

    Args:
        text: Raw text string.

    Returns:
        Normalized text. Empty string if input is empty/None-like.
    """
    if not text:
        return ""
    translator = str.maketrans(string.punctuation, " " * len(string.punctuation))
    cleaned = text.translate(translator)
    return " ".join(cleaned.lower().strip().split())


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute word-level Jaccard similarity between two texts.

    Normalizes both texts, splits into word sets, and computes
    |intersection| / |union|.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Jaccard similarity in [0.0, 1.0]. Returns 0.0 if either text is empty.
    """
    a_words = set(normalize_text(text_a).split())
    b_words = set(normalize_text(text_b).split())
    if not a_words or not b_words:
        return 0.0
    intersection = len(a_words & b_words)
    union = len(a_words | b_words)
    return intersection / union if union > 0 else 0.0
