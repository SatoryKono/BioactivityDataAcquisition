"""Source-bound inventory check in the architecture lane with Git history."""

from __future__ import annotations

import pytest

from scripts.engineering.qa.external_resource_inventory import main
from scripts.engineering.qa.requalify_external_resource_inventory import (
    main as requalification_main,
)

pytestmark = pytest.mark.architecture


def test_repository_catalog_and_projection_are_current() -> None:
    """Validate the actual catalog/projection without product runtime I/O."""
    assert main(["--check"]) == 0


def test_runtime_candidate_source_review_matches_materialized_catalog() -> None:
    """The current projection must also match the pinned semantic delta review."""
    assert (
        requalification_main(
            [
                "--review",
                "configs/quality/external_resource_inventory_qm09_review.json",
                "--check",
            ]
        )
        == 0
    )
