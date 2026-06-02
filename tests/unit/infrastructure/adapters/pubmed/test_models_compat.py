"""Compatibility checks for PubMed model facade exports."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters import pubmed as pubmed_pkg
from bioetl.infrastructure.adapters.pubmed import models
from bioetl.infrastructure.adapters.pubmed._search_models import (
    PubMedSearchResponse as SearchResponseImpl,
    PubMedSearchResult as SearchResultImpl,
)


pytestmark = pytest.mark.unit


def test_models_module_reexports_search_models() -> None:
    """Legacy models module should keep exposing search DTOs."""
    assert models.PubMedSearchResponse is SearchResponseImpl
    assert models.PubMedSearchResult is SearchResultImpl


def test_package_root_reexports_pubmed_search_response() -> None:
    """Package root should preserve the existing search response export."""
    assert pubmed_pkg.PubMedSearchResponse is SearchResponseImpl
