"""Shared fixtures for integration pipeline tests.

Configures VCR cassette directories for provider-specific tests.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Base VCR fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr"

# Provider-specific cassette directories
CHEMBL_CASSETTE_DIR = FIXTURES_DIR / "chembl"
UNIPROT_CASSETTE_DIR = FIXTURES_DIR / "uniprot"
PUBMED_CASSETTE_DIR = FIXTURES_DIR / "pubmed"
PUBCHEM_CASSETTE_DIR = FIXTURES_DIR / "pubchem"


def _get_vcr_config(cassette_dir: Path) -> dict:
    """Generate VCR config for a given cassette directory."""
    return {
        "cassette_library_dir": str(cassette_dir),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.fixture(scope="module")
def vcr_config(request):
    """Configure VCR based on test module name.

    Automatically selects the correct cassette directory based on the
    test module name (e.g., test_chembl_* uses chembl/ directory).
    """
    module_name = request.module.__name__

    if "chembl" in module_name:
        return _get_vcr_config(CHEMBL_CASSETTE_DIR)
    elif "uniprot" in module_name:
        return _get_vcr_config(UNIPROT_CASSETTE_DIR)
    elif "pubmed" in module_name:
        return _get_vcr_config(PUBMED_CASSETTE_DIR)
    elif "pubchem" in module_name:
        return _get_vcr_config(PUBCHEM_CASSETTE_DIR)
    else:
        # Default to root fixtures directory
        return _get_vcr_config(FIXTURES_DIR)
