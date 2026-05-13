"""Root pytest plugin registration for repository-wide shared support modules."""

from __future__ import annotations

pytest_plugins = (
    "tests.helpers.metadata_fixtures",
    "tests.integration.chembl.extraction_params_support",
)
