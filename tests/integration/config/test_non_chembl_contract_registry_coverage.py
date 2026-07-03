"""Integration tests for shipped non-ChEMBL Gold contract registry coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.normalization.profiles.registry import (
    resolve_normalization_profile_identity,
)
from bioetl.infrastructure.control_plane import FileContractRegistryStore

_REGISTRY_PATH = Path("configs/base/contract_registry.yaml")

_EXPECTED_NON_CHEMBL_CONTRACT_SURFACE: dict[str, dict[str, str]] = {
    "crossref.publication": {
        "source_path": "../../src/bioetl/domain/contracts/gold/publications_crossref.py",
        "artifact": "../../docs/04-reference/contracts/gold/crossref_publication_v1.0.json",
        "dq_policy_ref": "crossref.dq.v1",
    },
    "openalex.publication": {
        "source_path": "../../src/bioetl/domain/contracts/gold/publications_openalex.py",
        "artifact": "../../docs/04-reference/contracts/gold/openalex_publication_v1.0.json",
        "dq_policy_ref": "openalex.dq.v1",
    },
    "pubchem.compound": {
        "source_path": "../../src/bioetl/domain/contracts/gold/pubchem.py",
        "artifact": "../../docs/04-reference/contracts/gold/pubchem_compound_v1.0.json",
        "dq_policy_ref": "pubchem.dq.v1",
    },
    "pubmed.publication": {
        "source_path": "../../src/bioetl/domain/contracts/gold/publications_pubmed.py",
        "artifact": "../../docs/04-reference/contracts/gold/pubmed_publication_v1.0.json",
        "dq_policy_ref": "pubmed.dq.v1",
    },
    "semanticscholar.publication": {
        "source_path": "../../src/bioetl/domain/contracts/gold/publications_semanticscholar.py",
        "artifact": "../../docs/04-reference/contracts/gold/semanticscholar_publication_v1.0.json",
        "dq_policy_ref": "semanticscholar.dq.v1",
    },
    "uniprot.idmapping": {
        "source_path": "../../src/bioetl/domain/contracts/gold/uniprot.py",
        "artifact": "../../docs/04-reference/contracts/gold/uniprot_idmapping_v1.0.json",
        "dq_policy_ref": "uniprot.dq.v1",
    },
    "uniprot.protein": {
        "source_path": "../../src/bioetl/domain/contracts/gold/uniprot.py",
        "artifact": "../../docs/04-reference/contracts/gold/uniprot_protein_v1.0.json",
        "dq_policy_ref": "uniprot.dq.v1",
    },
}


@pytest.mark.integration
def test_non_chembl_contract_registry_normalization_profiles_stay_in_sync() -> None:
    """Non-ChEMBL registry entries must carry canonical normalization profile identity."""
    store = FileContractRegistryStore(_REGISTRY_PATH)
    registry = store.load()

    for contract_ref, expected in _EXPECTED_NON_CHEMBL_CONTRACT_SURFACE.items():
        provider, entity = contract_ref.split(".", maxsplit=1)
        entry = registry.entries[contract_ref]
        profile_identity = resolve_normalization_profile_identity(provider, entity)

        assert profile_identity is not None
        assert entry.status.value == "active"
        assert entry.source_path == expected["source_path"]
        assert entry.published_artifacts == [expected["artifact"]]
        assert entry.identity.contract_version == "1.0.0"
        assert entry.identity.dq_policy_ref == expected["dq_policy_ref"]
        assert entry.identity.rule_bundle_version == "dq-rules.v1.0"
        assert entry.identity.normalization_profile_ref == profile_identity.profile_name
        assert (
            entry.identity.normalization_profile_version
            == profile_identity.profile_version
        )
        assert (
            entry.identity.normalization_profile_hash == profile_identity.profile_hash
        )
        assert entry.dq_policy_ref == expected["dq_policy_ref"]
        assert entry.rule_bundle_version == "dq-rules.v1.0"
        assert entry.normalization_profile_ref == profile_identity.profile_name
        assert entry.normalization_profile_version == profile_identity.profile_version
        assert entry.normalization_profile_hash == profile_identity.profile_hash
