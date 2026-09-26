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
"""Contract checks for semantic anchor DQ/Gold/composite parity."""

from __future__ import annotations

import pytest

from pathlib import Path

from scripts.engineering.qa.check_semantic_anchor_parity import (
    ANCHOR_SPECS,
    validate_anchor_parity,
)


pytestmark = pytest.mark.integration


def test_semantic_anchor_parity_gate_passes_current_repo() -> None:
    findings = validate_anchor_parity(Path("."))

    assert not findings, "\n".join(finding.message for finding in findings)


def test_anchor_specs_cover_required_semantic_join_anchors() -> None:
    spec_ids = {spec.anchor_id for spec in ANCHOR_SPECS}

    assert {
        "crossref_doi_publication_anchor",
        "pubmed_pmid_publication_anchor",
        "pubmed_title_publication_fallback_anchor",
        "pubmed_pmc_publication_reference_anchor",
        "chembl_publication_identifier_anchor",
        "chembl_activity_publication_lineage_anchor",
        "chembl_assay_identifier_anchor",
        "chembl_molecule_identifier_anchor",
        "chembl_inchi_key_structure_join_anchor",
        "pubchem_inchi_key_structure_join_anchor",
        "chembl_canonical_smiles_structure_join_anchor",
        "pubchem_canonical_smiles_structure_join_anchor",
        "chembl_target_identifier_anchor",
        "chembl_activity_target_lineage_anchor",
        "uniprot_idmapping_target_anchor",
        "uniprot_accession_chained_join_anchor",
        "uniprot_protein_accession_identifier_anchor",
    } <= spec_ids


def test_lineage_and_structure_join_anchors_remain_gold_nullable() -> None:
    nullable_anchor_ids = {
        "pubmed_pmc_publication_reference_anchor",
        "chembl_activity_publication_lineage_anchor",
        "chembl_inchi_key_structure_join_anchor",
        "pubchem_inchi_key_structure_join_anchor",
        "chembl_canonical_smiles_structure_join_anchor",
        "pubchem_canonical_smiles_structure_join_anchor",
        "chembl_activity_target_lineage_anchor",
        "uniprot_accession_chained_join_anchor",
    }

    for spec in ANCHOR_SPECS:
        if spec.anchor_id in nullable_anchor_ids:
            assert spec.expected_gold_required is False
