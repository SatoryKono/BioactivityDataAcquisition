"""Integration tests for shipped ChEMBL Gold contract registry coverage."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.dq_contract_config_loader import (
    DQContractConfigLoader,
)
from bioetl.infrastructure.control_plane import FileContractRegistryStore

_REGISTRY_PATH = Path("configs/base/contract_registry.yaml")
_CONFIGS_ROOT = Path("configs")

_EXPECTED_CHEMBL_CONTRACT_SURFACE: dict[str, dict[str, str]] = {
    "chembl.activity": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_activity_v1.0.json",
    },
    "chembl.assay": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_assay_v1.0.json",
    },
    "chembl.assay_parameters": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_assay_parameters_v1.0.json",
    },
    "chembl.cell_line": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_reference_publication_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_cell_line_v1.0.json",
    },
    "chembl.compound_record": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_reference_publication_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_compound_record_v1.0.json",
    },
    "chembl.molecule": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_molecule_protein_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_molecule_v1.0.json",
    },
    "chembl.protein_class": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_molecule_protein_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_protein_class_v1.0.json",
    },
    "chembl.publication": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_reference_publication_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_publication_v1.0.json",
    },
    "chembl.publication_similarity": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_reference_publication_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_publication_similarity_v1.0.json",
    },
    "chembl.publication_term": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_reference_publication_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_publication_term_v1.0.json",
    },
    "chembl.subcellular_fraction": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_target_lookup_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_subcellular_fraction_v1.0.json",
    },
    "chembl.target": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_target_lookup_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_target_v1.0.json",
    },
    "chembl.target_component": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_target_lookup_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_target_component_v1.0.json",
    },
    "chembl.tissue": {
        "source_path": "../../src/bioetl/domain/contracts/gold/_chembl_target_lookup_schemas.py",
        "artifact": "../../docs/04-reference/contracts/gold/chembl_tissue_v1.0.json",
    },
}


@pytest.mark.integration
def test_chembl_contract_registry_covers_all_shipped_gold_surfaces() -> None:
    """Registry must cover the full shipped ChEMBL Gold contract surface."""
    store = FileContractRegistryStore(_REGISTRY_PATH)
    registry = store.load()

    chembl_entries = {
        contract_ref: entry
        for contract_ref, entry in registry.entries.items()
        if contract_ref.startswith("chembl.")
    }

    assert set(chembl_entries) == set(_EXPECTED_CHEMBL_CONTRACT_SURFACE)
    for contract_ref, expected in _EXPECTED_CHEMBL_CONTRACT_SURFACE.items():
        entry = chembl_entries[contract_ref]
        assert entry.source_path == expected["source_path"]
        assert entry.published_artifacts == [expected["artifact"]]
        assert entry.identity.contract_version == "1.0.0"
        assert entry.identity.dq_policy_ref == "chembl.dq.v1"
        assert entry.identity.rule_bundle_version == "dq-rules.v1.0"
        assert entry.dq_policy_ref == "chembl.dq.v1"
        assert entry.rule_bundle_version == "dq-rules.v1.0"


@pytest.mark.integration
def test_chembl_contract_registry_paths_are_filesystem_consistent() -> None:
    """All registered ChEMBL contract sources and artifacts must exist."""
    store = FileContractRegistryStore(_REGISTRY_PATH)
    registry = store.load()

    result = store.validate_filesystem_consistency(registry)

    chembl_issues = [
        issue for issue in result.issues if issue.contract_ref.startswith("chembl.")
    ]
    assert chembl_issues == []


@pytest.mark.integration
def test_chembl_activity_contract_is_registry_published_but_not_active_when_gold_disabled() -> (
    None
):
    """chembl.activity stays published in the registry but must not advertise an active Gold runtime."""
    activity_config = _CONFIGS_ROOT / "entities" / "chembl" / "activity.yaml"
    config = yaml.safe_load(activity_config.read_text(encoding="utf-8"))
    store = FileContractRegistryStore(_REGISTRY_PATH)
    registry = store.load()

    assert config["pipeline"]["sink"]["gold"]["enabled"] is False
    assert registry.entries["chembl.activity"].status.value == "deprecated"


@pytest.mark.integration
@pytest.mark.parametrize("contract_ref", sorted(_EXPECTED_CHEMBL_CONTRACT_SURFACE))
def test_chembl_contract_loader_resolves_each_registered_surface(
    contract_ref: str,
) -> None:
    """Each registered ChEMBL Gold surface must have a matching DQ contract file."""
    loader = DQContractConfigLoader(_CONFIGS_ROOT)
    pipeline_name = contract_ref.replace(".", "_")

    dq_config = loader.load_dq_config_for_pipeline(pipeline_name)

    assert dq_config.contract_ref == contract_ref
    assert dq_config.contract_version == "1.0.0"
    assert dq_config.rule_bundle_version == "dq-rules.v1.0"
