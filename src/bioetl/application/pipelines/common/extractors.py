"""Common field extraction functions for publication pipelines.

Provides reusable pure functions for extracting fields from different
provider API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different providers

Note: Provider-specific logic (e.g., CrossRef's given+family combination)
should remain in provider-specific extractors.
"""

from __future__ import annotations

__all__ = ["extract_author_names"]


from bioetl.domain.types import JsonDict


def extract_author_names(
    items: list[JsonDict] | None,  # Any: untyped API JSON record
    name_field: str = "name",
    nested_field: str | None = None,
) -> list[str]:
    """Universal author name extractor for pre-combined name fields.

    Supports different provider formats where author names are stored
    as single strings (not combined from multiple fields):

    - OpenAlex: items=[{author: {display_name: "..."}}, ...],
                nested_field="author", name_field="display_name"
    - SemanticScholar: items=[{name: "..."}, ...],
                       name_field="name"

    Note: CrossRef uses separate "given" and "family" fields that must
    be combined - use the provider-specific extract_authors() function
    for that format.

    Args:
        items: List of author dictionaries.
        name_field: Key containing author name within the target dict.
        nested_field: If author data is nested, key to access the inner dict.

    Returns:
        List of author name strings. Empty list if items is None or empty.

    Example:
        >>> # OpenAlex format
        >>> extract_author_names(
        ...     [{"author": {"display_name": "John Doe"}}],
        ...     name_field="display_name",
        ...     nested_field="author"
        ... )
        ['John Doe']

        >>> # SemanticScholar format
        >>> extract_author_names(
        ...     [{"authorId": "123", "name": "Jane Smith"}],
        ...     name_field="name"
        ... )
        ['Jane Smith']

        >>> # Empty or None input
        >>> extract_author_names(None)
        []

    """
    if not items:
        return []

    authors: list[str] = []
    for item in items:
        # Navigate to nested dict if specified
        target = item.get(nested_field) if nested_field else item

        # Skip if target is not a dict
        if not isinstance(target, dict):
            continue

        # Extract and validate name
        name = target.get(name_field)
        if name and isinstance(name, str):
            stripped = name.strip()
            if stripped:
                authors.append(stripped)

    return authors
