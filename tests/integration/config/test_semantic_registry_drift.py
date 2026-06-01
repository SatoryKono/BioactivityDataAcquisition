"""Contract checks for generated semantic registry drift candidates."""

from __future__ import annotations

import pytest

from pathlib import Path

from scripts.engineering.qa.check_semantic_registry_drift import (
    discover_exact_registry_candidates,
    validate_semantic_registry_drift,
)


pytestmark = pytest.mark.integration

def test_semantic_registry_drift_gate_passes_current_repo() -> None:
    result = validate_semantic_registry_drift(Path("."))

    assert not result.findings, "\n".join(
        finding.message for finding in result.findings
    )


def test_generated_exact_candidates_cover_mapping_and_composite_alias_surfaces() -> (
    None
):
    candidates = discover_exact_registry_candidates(Path("."))
    candidate_keys = {
        (candidate.source, candidate.raw_name, candidate.canonical_name)
        for candidate in candidates
    }

    assert (
        "PUBLICATION_FIELD_MAPPING[chembl]",
        "doc_type",
        "publication_type",
    ) in candidate_keys
    assert (
        "MOLECULE_FIELD_MAPPING[pubchem]",
        "hba",
        "hba_count",
    ) in candidate_keys
    assert (
        "MOLECULE_FIELD_ALIASES[pubchem]",
        "h_bond_acceptor_count",
        "hba_count",
    ) in candidate_keys
    assert (
        "configs/composites/molecule.yaml:field_aliases[pubchem]",
        "h_bond_acceptor_count",
        "hba_count",
    ) in candidate_keys


def test_reviewed_audit_clusters_are_suppressed_from_runtime_warnings() -> None:
    result = validate_semantic_registry_drift(Path("."))

    assert not result.findings
    assert result.warnings == ()
