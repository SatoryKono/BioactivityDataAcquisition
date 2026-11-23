"""RF-002: primary UniProt vs auxiliary xref roles and matching policy."""

from __future__ import annotations

from dataclasses import replace

import pytest

from iuphar_target_class.bioetl_input import project_target_fields
from iuphar_target_class.identifier_roles import (
    LEGACY_MATCHING_POLICY_VERSION,
    MATCHING_POLICY_VERSION,
    RF002_CONTRACT_VERSION,
    identifier_roles_document,
)
from iuphar_target_class.matching import (
    AUXILIARY_DIVERGENCE,
    UNKNOWN_AUXILIARY,
    CatalogTarget,
    MatchQuery,
    resolve_match,
)
from iuphar_target_class.policy import policy_document
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_bytes

pytestmark = pytest.mark.unit


def _target(
    target_id: str,
    *,
    uniprot: str | None = None,
    species: str | None = "human",
) -> CatalogTarget:
    return CatalogTarget(
        target_id=target_id,
        uniprot_ids=(uniprot,) if uniprot else (),
        gene_symbol=None,
        gene_id=None,
        species=species,
        names=(),
        synonyms=(),
    )


def test_projection_splits_primary_equivalent_and_auxiliary() -> None:
    fields = project_target_fields(
        {
            "target_id": "CHEMBL1",
            "component_accessions": '["P11111", "P22222"]',
            "target_xref_uniprot_ids": "P11111|Q99999",
            "pref_name": "Example",
        },
        "9606",
    )
    assert fields["uniprot"] == "P11111|P22222"
    assert fields["uniprot_equivalent"] == "P11111"
    assert fields["uniprot_xref"] == "Q99999"
    assert "component_accessions" in (fields["source_business_data"] or "")


def test_primary_plus_unknown_auxiliary_matches_with_diagnostic() -> None:
    catalog = (_target("1", uniprot="P11111"),)
    result = resolve_match(
        MatchQuery(
            target_id=None,
            uniprot_ids=("P11111",),
            gene_symbol=None,
            gene_id=None,
            organism="human",
            name=None,
            synonyms=(),
            auxiliary_uniprot_ids=("Q99999",),
        ),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
    assert UNKNOWN_AUXILIARY in {item.code for item in result.diagnostics}


def test_two_trusted_primary_ids_still_conflict() -> None:
    catalog = (
        _target("1", uniprot="P11111"),
        _target("2", uniprot="P22222"),
    )
    result = resolve_match(
        MatchQuery(
            target_id="1",
            uniprot_ids=("P22222",),
            gene_symbol=None,
            gene_id=None,
            organism="human",
            name=None,
            synonyms=(),
            auxiliary_uniprot_ids=("Q99999",),
        ),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None
    codes = {item.code for item in result.diagnostics}
    assert "identity_conflict" in codes
    assert UNKNOWN_AUXILIARY in codes


def test_auxiliary_divergence_is_not_identity_conflict() -> None:
    catalog = (
        _target("1", uniprot="P11111"),
        _target("2", uniprot="Q88888"),
    )
    result = resolve_match(
        MatchQuery(
            target_id=None,
            uniprot_ids=("P11111",),
            gene_symbol=None,
            gene_id=None,
            organism="human",
            name=None,
            synonyms=(),
            auxiliary_uniprot_ids=("Q88888",),
        ),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
    assert AUXILIARY_DIVERGENCE in {item.code for item in result.diagnostics}


def test_name_only_still_ambiguous() -> None:
    catalog = (_target("1", uniprot="P11111"),)
    catalog = (replace(catalog[0], names=("Mu opioid receptor",), uniprot_ids=()),)
    result = resolve_match(
        MatchQuery(
            None,
            (),
            None,
            None,
            "human",
            "Mu opioid receptor",
            (),
            auxiliary_uniprot_ids=("Q99999",),
        ),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_anchor_permutation_is_stable() -> None:
    catalog = (_target("1", uniprot="P11111"),)
    first = resolve_match(
        MatchQuery(None, ("P11111",), None, None, "human", None, (), ("Q1", "Q2")),
        catalog,
        snapshot_complete=True,
    )
    second = resolve_match(
        MatchQuery(None, ("P11111",), None, None, "human", None, (), ("Q2", "Q1")),
        catalog,
        snapshot_complete=True,
    )
    assert first.match_status == second.match_status == "matched"
    assert {item.code for item in first.diagnostics} == {
        item.code for item in second.diagnostics
    }


def test_legacy_policy_version_does_not_qualify_rf002() -> None:
    document = identifier_roles_document()
    assert document["contract_version"] == RF002_CONTRACT_VERSION
    assert document["matching_policy_version"] == MATCHING_POLICY_VERSION
    assert document["legacy_matching_policy_version"] == LEGACY_MATCHING_POLICY_VERSION
    assert document["matching_policy_version"] != LEGACY_MATCHING_POLICY_VERSION
    assert document["biological_accuracy_accepted"] is False
    assert policy_document()["rf002_identifier_roles"] == document


def test_committed_rf002_matching_policy_matches_document() -> None:
    from pathlib import Path

    path = Path("data/iuphar_target_class/rf002/matching_policy.json")
    receipt = Path("data/iuphar_target_class/rf002/matching_policy.sha256.json")
    payload = path.read_bytes()
    assert payload == canonical_json_bytes(identifier_roles_document())
    meta = __import__("json").loads(receipt.read_text(encoding="utf-8"))
    assert meta["sha256"] == sha256_bytes(payload)
    assert meta["matching_policy_version"] == MATCHING_POLICY_VERSION
