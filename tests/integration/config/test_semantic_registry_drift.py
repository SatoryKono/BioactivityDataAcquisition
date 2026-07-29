# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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


def test_generated_exact_candidates_cover_mapping_and_domain_alias_surfaces() -> None:
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
        "MOLECULE_FIELD_ALIASES[pubchem]",
        "h_bond_donor_count",
        "hbd_count",
    ) in candidate_keys
    assert (
        "MOLECULE_FIELD_ALIASES[pubchem]",
        "tpsa",
        "polar_surface_area",
    ) in candidate_keys
    assert (
        "MOLECULE_FIELD_ALIASES[pubchem]",
        "xlogp",
        "logp",
    ) in candidate_keys
    assert not any(
        source.startswith("configs/composites/") and "field_aliases" in source
        for source, _, _ in candidate_keys
    )


def test_reviewed_audit_clusters_are_suppressed_from_runtime_warnings() -> None:
    result = validate_semantic_registry_drift(Path("."))

    assert not result.findings
    assert result.warnings == ()
