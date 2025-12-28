"""Abstract text reconstruction from OpenAlex inverted index format.

OpenAlex stores abstracts as inverted indices to reduce storage.
The format maps words to their positions: {"word": [0, 5, 12], ...}

This module provides functions to reconstruct plain text from
the inverted index format.

Example:
    >>> index = {"The": [0], "quick": [1], "fox": [2, 4], "is": [3]}
    >>> reconstruct_abstract(index)
    'The quick fox is fox'

"""

from __future__ import annotations


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct abstract text from OpenAlex inverted index format.

    OpenAlex stores abstracts as inverted indices where keys are words
    and values are lists of positions where the word appears.

    Args:
        inverted_index: Dictionary mapping words to position lists.
            Example: {"The": [0], "quick": [1], "brown": [2]}

    Returns:
        Reconstructed abstract text as string, or None if input is None/empty.

    Example:
        >>> index = {"Hello": [0], "world": [1]}
        >>> reconstruct_abstract(index)
        'Hello world'

    """
    if not inverted_index:
        return None

    # Build list of (position, word) tuples
    positions: list[tuple[int, str]] = []
    for word, indices in inverted_index.items():
        for idx in indices:
            positions.append((idx, word))

    # Sort by position and join words
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


def estimate_abstract_length(inverted_index: dict[str, list[int]] | None) -> int:
    """Estimate the word count of an abstract from its inverted index.

    Args:
        inverted_index: Dictionary mapping words to position lists.

    Returns:
        Estimated word count (sum of all position list lengths).

    """
    if not inverted_index:
        return 0

    return sum(len(positions) for positions in inverted_index.values())
