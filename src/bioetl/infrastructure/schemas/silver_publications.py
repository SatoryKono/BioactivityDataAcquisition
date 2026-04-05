"""Publication-oriented Silver layer schemas."""

from __future__ import annotations

import pyarrow as pa

from bioetl.infrastructure.schemas.silver_publication_field_blocks import (
    build_crossref_publication_fields,
    build_openalex_publication_fields,
    build_publication_dq_suffix_fields,
    build_publication_system_prefix_fields,
    build_pubmed_publication_fields,
    build_semanticscholar_publication_fields,
)

__all__ = [
    "CROSSREF_PUBLICATION_SCHEMA",
    "OPENALEX_PUBLICATION_SCHEMA",
    "PUBMED_PUBLICATION_SCHEMA",
    "SEMANTICSCHOLAR_PUBLICATION_SCHEMA",
]


def _build_publication_schema(provider_fields: list[pa.Field]) -> pa.Schema:
    """Assemble a provider Silver publication schema from shared field blocks."""
    return pa.schema(
        [
            *build_publication_system_prefix_fields(),
            *provider_fields,
            *build_publication_dq_suffix_fields(),
        ]
    )


PUBMED_PUBLICATION_SCHEMA = _build_publication_schema(build_pubmed_publication_fields())

SEMANTICSCHOLAR_PUBLICATION_SCHEMA = _build_publication_schema(
    build_semanticscholar_publication_fields()
)

CROSSREF_PUBLICATION_SCHEMA = _build_publication_schema(
    build_crossref_publication_fields()
)

OPENALEX_PUBLICATION_SCHEMA = _build_publication_schema(
    build_openalex_publication_fields()
)
