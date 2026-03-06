"""Compatibility tests for CrossRef adapter module decomposition."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters import crossref as crossref_pkg
from bioetl.infrastructure.adapters.crossref.client import (
    CROSSREF_API_BASE as CLIENT_CROSSREF_API_BASE,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CROSSREF_HEALTH_ERRORS as CLIENT_CROSSREF_HEALTH_ERRORS,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter as ClientCrossRefAdapter,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefFetchFlow as ClientCrossRefFetchFlow,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefQueryBuilder as ClientCrossRefQueryBuilder,
)
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefResponseMapper as ClientCrossRefResponseMapper,
)


@pytest.mark.unit
def test_package_reexports_client_symbols_for_backward_compatibility() -> None:
    """Existing imports from crossref package and client must resolve identically."""
    assert crossref_pkg.CrossRefAdapter is ClientCrossRefAdapter
    assert crossref_pkg.CROSSREF_API_BASE == CLIENT_CROSSREF_API_BASE
    assert crossref_pkg.CROSSREF_HEALTH_ERRORS == CLIENT_CROSSREF_HEALTH_ERRORS


@pytest.mark.unit
def test_client_reexports_new_decomposed_components() -> None:
    """Client facade should re-export decomposed flow/query/mapper components."""
    assert ClientCrossRefFetchFlow.__name__ == "CrossRefFetchFlow"
    assert ClientCrossRefQueryBuilder.__name__ == "CrossRefQueryBuilder"
    assert ClientCrossRefResponseMapper.__name__ == "CrossRefResponseMapper"
