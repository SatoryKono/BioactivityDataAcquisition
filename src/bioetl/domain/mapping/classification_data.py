"""Classification data value object for publication type taxonomy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassificationData:
    """Immutable container for publication type classification data.

    Loaded from JSON asset at runtime by the infrastructure loader.
    Passed to ``initialize_classification()`` in the domain module.

    Attributes:
        entry_cores: Ordered tuples of (unified_type, subclass, class_code).
        openalex_row_index: OpenAlex raw-key → 1-based row index.
        crossref_row_index: CrossRef raw-key → 1-based row index.
        pubmed_row_index: PubMed raw-key → 1-based row index.
        s2_row_index: Semantic Scholar raw-key → 1-based row index.
    """

    entry_cores: tuple[tuple[str, str, str], ...]
    openalex_row_index: dict[str, int]
    crossref_row_index: dict[str, int]
    pubmed_row_index: dict[str, int]
    s2_row_index: dict[str, int]
