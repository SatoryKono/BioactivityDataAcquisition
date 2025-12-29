"""Contract tests configuration and fixtures.

Provides common fixtures for live API contract testing.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for contract tests."""
    config.addinivalue_line("markers", "chembl: ChEMBL API contract tests")
    config.addinivalue_line("markers", "pubchem: PubChem API contract tests")
    config.addinivalue_line("markers", "uniprot: UniProt API contract tests")
    config.addinivalue_line("markers", "pubmed: PubMed API contract tests")
    config.addinivalue_line("markers", "slow: Tests that may be slow due to rate limits")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip contract tests if BIOETL_LIVE_API_TESTS is not set."""
    live_tests_enabled = os.environ.get("BIOETL_LIVE_API_TESTS", "").lower() == "true"

    if not live_tests_enabled:
        skip_marker = pytest.mark.skip(
            reason="Live API tests disabled. Set BIOETL_LIVE_API_TESTS=true to enable."
        )
        for item in items:
            # All tests in contract/ directory require live API access
            if "contract" in str(item.fspath):
                item.add_marker(skip_marker)


@pytest.fixture
def chembl_api_key() -> str | None:
    """Get ChEMBL API key from environment."""
    return os.environ.get("BIOETL_CHEMBL_API_KEY")


@pytest.fixture
def pubmed_api_key() -> str | None:
    """Get PubMed API key from environment."""
    return os.environ.get("BIOETL_PUBMED_API_KEY")


@pytest.fixture
def uniprot_api_key() -> str | None:
    """Get UniProt API key from environment."""
    return os.environ.get("BIOETL_UNIPROT_API_KEY")


# Common expected schema fields for contract verification
CHEMBL_ACTIVITY_REQUIRED_FIELDS = frozenset({
    "activity_id",
    "assay_chembl_id",
    "molecule_chembl_id",
})

CHEMBL_MOLECULE_REQUIRED_FIELDS = frozenset({
    "molecule_chembl_id",
    "molecule_type",
})

CHEMBL_TARGET_REQUIRED_FIELDS = frozenset({
    "target_chembl_id",
    "target_type",
})

UNIPROT_PROTEIN_REQUIRED_FIELDS = frozenset({
    "primaryAccession",
    "uniProtkbId",
    "entryType",
})

PUBCHEM_COMPOUND_REQUIRED_FIELDS = frozenset({
    "cid",
})
