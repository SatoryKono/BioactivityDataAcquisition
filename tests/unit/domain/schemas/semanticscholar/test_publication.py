"""Same-path owner tests for Semantic Scholar publication schema module."""

from __future__ import annotations

import pytest

from bioetl.domain.schemas.common.publication_base import PublicationBaseSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
    __all__,
)


pytestmark = pytest.mark.unit

def test_semanticscholar_publication_schema_extends_publication_base_schema() -> None:
    assert issubclass(SemanticScholarPublicationSchema, PublicationBaseSchema)


def test_semanticscholar_publication_schema_declares_provider_specific_columns() -> (
    None
):
    schema = SemanticScholarPublicationSchema.to_schema()
    assert "paper_id" in schema.columns
    assert "_lookup_method" in schema.columns
    assert "tldr" in schema.columns
    assert "SemanticScholarPublicationSchema" in __all__
