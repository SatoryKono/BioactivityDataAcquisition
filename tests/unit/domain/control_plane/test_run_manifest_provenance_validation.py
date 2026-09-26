"""Production provenance validation contracts for run manifests."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane.run_manifest import (
    PRODUCTION_PROVENANCE_REQUIRED_FIELDS,
    RunCodeProvenance,
    validate_production_provenance,
)

pytestmark = pytest.mark.unit


def test_missing_production_fields_are_complete_and_deterministic() -> None:
    """An empty provenance reports every required field in stable order."""
    provenance = RunCodeProvenance()

    assert provenance.missing_production_fields() == tuple(
        sorted(PRODUCTION_PROVENANCE_REQUIRED_FIELDS)
    )


def test_production_validation_fails_closed_with_explicit_missing_fields() -> None:
    """Production validation exposes actionable missing provenance identities."""
    provenance = RunCodeProvenance(pipeline_version="2026.08")

    with pytest.raises(ValueError, match="git_commit"):
        validate_production_provenance(provenance)


def test_nonproduction_validation_allows_incomplete_provenance() -> None:
    """The explicit non-production escape hatch remains non-enforcing."""
    validate_production_provenance(RunCodeProvenance(), production=False)
