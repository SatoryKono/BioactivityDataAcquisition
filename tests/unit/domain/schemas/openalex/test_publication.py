"""Same-path owner tests for OpenAlex publication schema module."""

from __future__ import annotations

import pytest

from bioetl.domain.schemas.common.publication_base import PublicationBaseSchema
from bioetl.domain.schemas.openalex.publication import (
    OpenAlexPublicationSchema,
    __all__,
)


pytestmark = pytest.mark.unit


def test_openalex_publication_schema_extends_publication_base_schema() -> None:
    assert issubclass(OpenAlexPublicationSchema, PublicationBaseSchema)


def test_openalex_publication_schema_declares_provider_specific_columns() -> None:
    schema = OpenAlexPublicationSchema.to_schema()
    assert "openalex_id" in schema.columns
    assert "_lookup_method" in schema.columns
    assert "primary_topic" in schema.columns
    assert "OpenAlexPublicationSchema" in __all__
