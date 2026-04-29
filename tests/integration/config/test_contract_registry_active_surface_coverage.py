"""Registry and DQ coverage for active standard pipeline contract surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.dq_contract_config_loader import (
    DQContractConfigLoader,
)
from bioetl.infrastructure.control_plane import FileContractRegistryStore

_CONFIGS_ROOT = Path("configs")
_ENTITY_CONFIGS_ROOT = _CONFIGS_ROOT / "entities"
_REGISTRY_PATH = _CONFIGS_ROOT / "base" / "contract_registry.yaml"
_FIXTURE_GAPS_PATH = _CONFIGS_ROOT / "base" / "bronze_fixture_gaps.yaml"
_GOLD_CONTRACTS_ROOT = Path("docs/04-reference/contracts/gold")
_STANDARD_CONTRACT_PROVIDERS = {
    "chembl",
    "crossref",
    "openalex",
    "pubchem",
    "pubmed",
    "semanticscholar",
    "uniprot",
}
_REQUIRED_DE_SCOPED_FIXTURE_GAP_DECISION_FIELDS = {
    "contract_ref",
    "decision_status",
    "decision_deadline",
    "decision_owner",
    "chosen_path",
    "contract_or_projection_target",
    "evidence_issue",
    "de_scope_decision",
    "resolution_plan",
}


def _active_standard_contract_refs() -> dict[str, str]:
    """Return pipeline_name -> contract_ref for active non-composite surfaces."""
    refs: dict[str, str] = {}
    for config_path in sorted(_ENTITY_CONFIGS_ROOT.glob("*/*.yaml")):
        provider = config_path.parent.name
        if provider not in _STANDARD_CONTRACT_PROVIDERS:
            continue
        if not _gold_runtime_enabled(config_path):
            continue
        entity = config_path.stem
        pipeline_name = f"{provider}_{entity}"
        refs[pipeline_name] = f"{provider}.{entity}"
    return refs


def _gold_runtime_enabled(config_path: Path) -> bool:
    """Return True when an entity config publishes a live Gold runtime surface."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    pipeline = config.get("pipeline")
    if not isinstance(pipeline, dict):
        return True
    sink = pipeline.get("sink")
    if not isinstance(sink, dict):
        return True
    gold = sink.get("gold")
    if not isinstance(gold, dict):
        return True
    enabled = gold.get("enabled")
    return True if enabled is None else bool(enabled)


def _de_scoped_fixture_contract_refs() -> set[str]:
    payload = yaml.safe_load(_FIXTURE_GAPS_PATH.read_text(encoding="utf-8")) or {}
    gaps = payload.get("gaps", {})
    if not isinstance(gaps, dict):
        return set()
    refs = set()
    for fixture_name, metadata in gaps.items():
        if not isinstance(metadata, dict) or metadata.get("status") != "de_scoped":
            continue
        provider, entity = str(fixture_name).split("/", maxsplit=1)
        if provider == "chembl":
            refs.add(f"{provider}.{entity}")
    return refs


def _fixture_gap_payload() -> dict[str, object]:
    payload = yaml.safe_load(_FIXTURE_GAPS_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


@pytest.mark.integration
def test_contract_registry_covers_active_standard_provider_surfaces() -> None:
    """Every active standard provider/entity config must be registry-governed."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()
    expected_refs = set(_active_standard_contract_refs().values())

    assert expected_refs <= set(registry.entries), (
        "Contract registry missing active provider surfaces: "
        f"{sorted(expected_refs - set(registry.entries))}"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("pipeline_name", "contract_ref"),
    sorted(_active_standard_contract_refs().items()),
)
def test_active_standard_provider_surface_has_dq_config_and_published_artifact(
    pipeline_name: str,
    contract_ref: str,
) -> None:
    """Active provider surfaces must resolve DQ config and published Gold artifact."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()
    entry = registry.entries[contract_ref]
    expected_artifact = (
        f"../../docs/04-reference/contracts/gold/{pipeline_name}_v1.0.json"
    )

    dq_config = DQContractConfigLoader(_CONFIGS_ROOT).load_dq_config_for_pipeline(
        pipeline_name
    )

    assert dq_config.contract_ref == contract_ref
    assert dq_config.contract_version == entry.identity.contract_version
    assert dq_config.rule_bundle_version == entry.identity.rule_bundle_version
    assert expected_artifact in entry.published_artifacts
    assert (_GOLD_CONTRACTS_ROOT / f"{pipeline_name}_v1.0.json").exists()


@pytest.mark.integration
def test_gold_disabled_standard_surface_can_stay_registry_published_but_not_active() -> (
    None
):
    """Gold-disabled standard surfaces may keep published artifacts without active status."""
    activity_config = _ENTITY_CONFIGS_ROOT / "chembl" / "activity.yaml"
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()

    assert _gold_runtime_enabled(activity_config) is False
    assert registry.entries["chembl.activity"].status.value == "deprecated"


@pytest.mark.integration
def test_de_scoped_chembl_fixture_gap_surfaces_are_not_active_contracts() -> None:
    """De-scoped ChEMBL fixture gaps must not advertise active contract surfaces."""
    registry = FileContractRegistryStore(_REGISTRY_PATH).load()

    statuses = {
        contract_ref: registry.entries[contract_ref].status.value
        for contract_ref in sorted(_de_scoped_fixture_contract_refs())
    }

    assert statuses == {
        "chembl.assay_parameters": "deprecated",
        "chembl.publication_similarity": "deprecated",
        "chembl.publication_term": "deprecated",
        "chembl.subcellular_fraction": "deprecated",
    }


@pytest.mark.integration
def test_de_scoped_bronze_fixture_gaps_have_explicit_resolution_decisions() -> None:
    """De-scoped Bronze fixture gaps must not remain open-ended exceptions."""
    payload = _fixture_gap_payload()
    gaps = payload.get("gaps", {})
    assert isinstance(gaps, dict)

    for fixture_name, metadata in gaps.items():
        if not isinstance(metadata, dict) or metadata.get("status") != "de_scoped":
            continue

        missing = _REQUIRED_DE_SCOPED_FIXTURE_GAP_DECISION_FIELDS - metadata.keys()
        assert not missing, f"{fixture_name}: missing decision fields {sorted(missing)}"
        assert metadata["decision_status"] in {
            "projection_required",
            "source_required",
            "keyed_recording_required",
        }
        assert str(metadata["decision_deadline"]) >= "2026-05-31"
        assert str(metadata["evidence_issue"]).endswith("/issues/3406")
