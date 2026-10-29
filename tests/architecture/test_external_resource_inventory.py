"""Source-bound inventory check in the architecture lane with Git history."""

import pytest

from scripts.engineering.qa.external_resource_inventory import main

pytestmark = pytest.mark.architecture


def test_repository_catalog_and_projection_are_current() -> None:
    """Validate the actual catalog/projection without product runtime I/O."""
    assert main(["--check"]) == 0
